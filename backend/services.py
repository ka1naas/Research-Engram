'''
功能a：对上传的论文生成摘要，以及对抗性搜索需要的内容
功能b：帮用户生成或改进idea，或者，进行普通对话，四种模式
功能c：在用户已经有idea的情况下，需要一点批评时才采用的
后续更新计划：加入真正的function calling实现简单的agent任务
'''
import os
from sqlalchemy.orm import Session
from pypdf import PdfReader
from fastapi import UploadFile
import schemas, crud
from vector_memory import VectorMemory
import datetime
import openai
from dotenv import load_dotenv
import models
import utils
import json
import re

# 读取 .env
load_dotenv()

# 初始化 DeepSeek
client = openai.OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"), # 从系统环境变量里拿钥匙，而不是写死在代码里
    base_url="https://api.deepseek.com"
)

# 初始化向量记忆库（单例模式：整个系统只用这一个实例，避免重复加载模型）
# 注意：这里我们假设 vector_memory.py 在同一目录下
memory_core = VectorMemory()

# ================= 功能A：接收pdf，保存全文，llm提取摘要，存入向量库 =================
async def process_paper_upload(
    user_id: int, 
    idea_id: int, 
    file: UploadFile, 
    db: Session
):
    """
    业务逻辑：上传 PDF -> 解析文本 -> 存 SQL -> 存向量库
    """
    
    # 1. 读取 PDF 内容 (I/O 操作)
    # UploadFile 是 FastAPI 的特有类型，类似于一个打开的文件句柄
    content = await file.read() 
    
    # 为了用 pypdf 读取，我们需要把二进制存成临时文件，或者用 BytesIO
    # 这里为了演示简单，我们假设是一个标准的文本提取流程
    import io
    pdf_file = io.BytesIO(content) # 把二进制流变成像文件一样可读的对象
    reader = PdfReader(pdf_file)
    
    full_text = ""
    for i,page in enumerate(reader.pages):
        if i >10:break
        text = page.extract_text()
        if text:
            full_text += page.extract_text() + "\n"
    
    # 2. 使用deepseek生成摘要
    print("使用deepseek生成摘要中...")
    structure_prompt = """
    你是一个科研论文分析师。请分析这篇论文，输出纯 JSON 对象：
    {
        "summary": "300字中文摘要",
        "claims": ["核心贡献1", "核心贡献2"],
        "critiques": ["指出的现有方法缺陷", "本论文方法的局限性", "反直觉的实验结果"]
    }
    """
    try:
        response = client.chat.completions.create(
            model = 'deepseek-chat',
            messages=[
                {'role':'system','content': structure_prompt},
                {'role':'user','content':full_text[:2000]}# 发送前2000字符，防止超长
            ],
            stream=False
        )
        # 解析 JSON (增加容错)
        import json
        content_str = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
        analysis = json.loads(content_str)
        
        abstract = analysis.get("summary", "摘要生成失败")
        critiques = analysis.get("critiques", [])
        if abstract == "摘要生成失败":
            print("deepseek生成摘要失败...")
        else:
            print("deepseek成功生成摘要！")

    except Exception as e:
        print("deepseek总结失败，采用其他方案：{e}")
        #提取前500字作为摘要
        abstract = full_text[:500] + "..."

    title = file.filename # 暂时用文件名当标题

    # 3. 调用 CRUD 层：存入 SQL 数据库
    # 这一步是为了保证无论向量库挂没挂，我们的基础数据都在
    paper_schema = schemas.PaperCreate(
        title=title, 
        abstract=abstract, 
        idea_id=idea_id,
        full_text=full_text # 传给 schema
    )
    db_paper = crud.create_paper_record(db=db, paper=paper_schema, user_id=user_id)

    # 4. 调用 VectorMemory：存入向量数据库
    # 我们把 paper_id 存进去，这样以后检索到向量，能反向查到 SQL 里的完整信息
    # 为了 **对抗性检索** 我们存入摘要的同时，存入批驳
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    metadata_true = {
        "role": "paper_summary",
        "user_id": user_id,
        "idea_id": idea_id,
        "paper_db_id": db_paper.id, # 关键：建立 SQL 和 Vector 的联系
        "timestamp": current_time 
    }

    metadata_false={
                "role": "paper_critique", # 👈 关键标签
                "user_id": user_id,
                "idea_id": idea_id,
                "paper_db_id": db_paper.id,
                "timestamp": current_time 
    }
    
    # 构造存入向量库的文本
    # ---- 正向存储 把摘要和题目存在一起 ----
    save_text = f'论文标题：{title}\nAI摘要:{abstract}\n'
    memory_core.add_memory(
        text=save_text, 
        metadata=metadata_true,
        mem_id=f"paper_{db_paper.id}"
    )

    # ---- 反向存储 存入批驳 ----
    if critiques:
        critique_text = f"论文标题：{title}\n局限与反思：{'; '.join(critiques)}"
        memory_core.add_memory(
            text=critique_text,
            metadata=metadata_false
        )


    print("论文成功存入！")

    return db_paper

# ================= 功能B (重构版)：通用智能对话流水线，含function calling =================
# services.py

async def chat_with_deepseek(db: Session, request: schemas.ChatRequest):
    # 1. 存用户消息
    user_msg = models.Message(content=request.query, role="user", user_id=request.user_id, idea_id=request.idea_id)
    db.add(user_msg)
    db.commit()

    final_answer = ""
    used_refs = []

    # 🟢 预先定义过滤条件 (复用逻辑)
    # 逻辑：只有当 (选了Idea) 且 (没开全局搜索) 时，才限制范围
    # 否则 (没选Idea 或 开了全局) -> filter 为 None (搜全部)
    current_filter = {"idea_id": request.idea_id} if (request.idea_id and not request.enable_global_search) else None
    
    # 用于打印日志看看
    mode_name = "🌍 全局联想" if not current_filter else f"🔒 专注当前(ID:{request.idea_id})"

    # ================= 分支一：指定了论文 (Context Locked) =================
    if request.paper_id:
        paper = db.query(models.Paper).filter(models.Paper.id == request.paper_id).first()
        if not paper:
            return schemas.ChatResponse(response_text="❌ 找不到指定的论文数据", message_id=0)

        # --- A. 深度阅读模式 (Full Text) ---
        # 这种模式下，我们要深度读这一篇，通常不需要 RAG 干扰，所以不使用 filter
        if request.use_full_text:
            print(f"📖 [深度模式] 阅读全文：{paper.title}")
            if not paper.full_text:
                return schemas.ChatResponse(response_text="⚠️ 该论文未录入全文数据", message_id=0)

            system_prompt = f"""
            你是一个专业的论文审稿人。用户指定了一篇论文进行【深度研读】。
            【标题】: {paper.title}
            【全文】:
            {paper.full_text[:35000]} 
            请基于全文细节回答。
            """
            messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": request.query}]

        # --- B. 摘要聚焦 + RAG 联想模式 ---
        # 🟢 关键点：这里要用到 current_filter
        else:
            print(f"🔍 [摘要模式] {mode_name} - 论文：{paper.title}")
            
            # 1. 基础是摘要
            base_context = f"【当前讨论论文】\n标题：{paper.title}\n摘要：{paper.abstract}"
            
            # 2. RAG 检索 (这里用到了 filter！)
            # 如果开启全局，这里就能搜到其他 Idea 的相关论文
            search_results = memory_core.search_memory(
                request.query, 
                n_results=3, 
                filter_metadata=current_filter # 👈 注入过滤逻辑
            )
            rag_context = "\n".join([f"- {r['content']}" for r in search_results])
            used_refs = [r['content'][:20] for r in search_results]

            system_prompt = f"""
            你是一个科研助手。
            {base_context}
            
            【关联知识 ({mode_name})】:
            {rag_context}
            
            请结合摘要和关联知识回答。
            """
            messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": request.query}]

        # 执行 LLM (分支一)
        response = client.chat.completions.create(model="deepseek-chat", messages=messages, stream=False)
        final_answer = response.choices[0].message.content

    # ================= 分支二：Agent 自由模式 (无指定 Paper) =================
    else:
        print(f"🤖 [Agent模式] {mode_name}")
        
        # 1. 历史记录
        history_context = ""
        if request.idea_id and request.history_len > 0:
            # 历史记录依然建议只看当前的，否则对话太乱。
            # 当然，如果你想让“对话历史”也跨 Idea，可以把 filter 去掉。这里暂且保持只看当前 Idea 的历史。
            last_msgs = db.query(models.Message).filter(models.Message.idea_id == request.idea_id).order_by(models.Message.created_at.desc()).limit(request.history_len).all()
            last_msgs.reverse()
            history_context = "\n".join([f"{m.role}: {m.content}" for m in last_msgs])

        # 2. Agent 思考
        agent_system_prompt = f"""
        你是一个科研助手。
        规则：
        1. 需要查资料 -> 输出 <TOOL_CALL>search: 关键词</TOOL_CALL>
        2. 否则 -> 直接回答。
        """

        resp1 = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": agent_system_prompt},
                {"role": "user", "content": f"历史:\n{history_context}\n问题:\n{request.query}"}
            ]
        )
        first_content = resp1.choices[0].message.content
        
        # 3. 工具检测与执行
        tool_query = detect_tool_call(first_content)
        
        if tool_query:
            keyword = tool_query.replace("search:", "").strip()
            print(f"🔧 Agent 正在搜索: {keyword} | 模式: {mode_name}")
            
            # 🟢 关键点：Agent 搜索时也要遵守 filter 规则
            res = memory_core.search_memory(
                keyword, 
                n_results=3, 
                filter_metadata=current_filter # 👈 注入过滤逻辑
            )
            
            knowledge = "\n".join([f"- {r['content']}" for r in res])
            used_refs = [r['content'][:20] for r in res]
            
            resp2 = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": "结合检索结果回答："},
                    {"role": "user", "content": f"问题:{request.query}\n资料:{knowledge}"}
                ]
            )
            final_answer = resp2.choices[0].message.content
        else:
            final_answer = first_content

    # ================= 收尾 =================
    ai_msg = models.Message(content=final_answer, role="ai", user_id=request.user_id, idea_id=request.idea_id)
    db.add(ai_msg)
    db.commit()

    return schemas.ChatResponse(
        response_text=final_answer,
        suggested_idea=None,
        used_references=used_refs,
        message_id=ai_msg.id
    )

# ================= 功能C：进行对抗性检索（深度评判） =================  
async def critical_agent_chat(
    db: Session,
    user_id: int,
    query: str,
    idea_id: int = None
):
    """
    正向检索 + 反向攻击 + 逻辑打分。
    """
    
    # 1. 基础上下文检索 (正向)
    support_results = memory_core.search_memory(query, n_results=3)
    support_text = "\n".join([f"- {r['content']}" for r in support_results])

    # 2. 对抗性检索 (反向)
    print("正在进行批判性思考...")
    # 生成反向关键词
    bad_keywords = utils.generate_adversarial_keywords(query)
    
    critique_evidences = []
    # 去向量库里专门搜 role='paper_critique' 的数据
    # 注意：这里假设 vector_memory.search_memory 以后可以支持 filter 参数
    # 目前先简单搜全文
    for kw in bad_keywords:
        res = memory_core.search_memory(kw, n_results=2)
        critique_evidences.extend(res)

    # 3. 逻辑冲突量化 (The Metric)
    high_conflict_points = []
    for evi in critique_evidences:
        # 调用 utils 里的量化器
        assessment = utils.calculate_conflict_score(query, evi['content'])
        
        if assessment['score'] >= 6: # 只有冲突分大于6的才值得报告
            high_conflict_points.append({
                "content": evi['content'],
                "score": assessment['score'],
                "reason": assessment['reason']
            })

    # 4. 组装最终 Agent Prompt
    system_prompt = f"""
    你是一个不仅提供帮助，更提供“深度洞察”的科研伙伴。
    用户正在思考："{query}"
    
    【已有支持证据】:
    {support_text}
    
    【⚠️ 潜在的逻辑风险 (基于现有论文的反驳)】:
    {json.dumps(high_conflict_points, ensure_ascii=False)}
    
    请回复用户：
    1. 首先肯定 Idea 的价值（如果有支持证据）。
    2. **核心任务**：如果存在高分冲突（Score > 6），必须严肃指出这个 Idea 的潜在缺陷。不要一味赞同。
    3. 综合建议下一步该怎么做。
    """

    # 5. 生成最终回复
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "system", "content": system_prompt}],
        stream=False
    )
    
    return response.choices[0].message.content




