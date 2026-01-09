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

# ================= 功能A：接收pdf，llm提取摘要，存入向量库 =================
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
    paper_schema = schemas.PaperCreate(title=title, abstract=abstract, idea_id=idea_id)
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

# ================= 功能B (重构版)：通用智能对话流水线 =================
async def chat_with_deepseek(
    db: Session, 
    request: schemas.ChatRequest
):
    # --- 1. 先把用户的这一句，存入 SQL (不管是啥模式) ---
    user_msg = models.Message(
        content=request.query,
        role="user",
        user_id=request.user_id,
        idea_id=request.idea_id # 如果没选 idea，这里就是 None
    )
    db.add(user_msg)
    db.commit() # 拿到 user_msg.id
    
    # --- 2. 准备上下文 (历史记录 + 知识检索) ---
    # A. 获取最近 N 轮对话历史 (Context)
    history_context = ""
    if request.idea_id and request.history_len > 0:
        # 查这个 Idea 下最近的 N 条消息
        last_msgs = db.query(models.Message)\
            .filter(models.Message.idea_id == request.idea_id)\
            .order_by(models.Message.created_at.desc())\
            .limit(request.history_len).all()
        
        # 倒序回来，变成时间正序
        last_msgs.reverse()
        history_context = "\n".join([f"{m.role}: {m.content}" for m in last_msgs])

    # B. Function Calling 这里的“Function”就是去向量库查知识 (RAG)
    # 不管什么模式，先去大脑(VectorDB)里搜一下，以防用户在问相关知识
    search_results = memory_core.search_memory(request.query, n_results=3)
    knowledge_context = "\n".join([f"- {r['content']}" for r in search_results])
    
    # --- 3. 组装 Prompt (根据 Mode 切换系统人设) ---
    
    # 默认人设
    system_instruction = "你是一个科研助手。请根据提供的上下文和知识回答用户。"
    
    # 获取当前 Idea 的内容（如果有）
    current_idea_text = "用户暂无 Idea"
    if request.idea_id:
        idea = db.query(models.Idea).filter(models.Idea.id == request.idea_id).first()
        if idea:
            current_idea_text = f"标题：{idea.title}\n详情：{idea.description}"

    # === 关键：模式路由 ===
    if request.mode == 'update':
        # 【功能 Calling】: 更新模式
        system_instruction = f"""
        你是一个科研Idea迭代专家。
        用户的意图是：**修改或完善当前的 Idea**。
        
        【当前 Idea】:
        {current_idea_text}
        
        【检索到的相关知识/论文】:
        {knowledge_context}
        
        请执行以下步骤：
        1. 结合用户的新指令和检索到的知识，思考如何改进 Idea。
        2. 用自然语言向用户解释你修改了哪里，为什么要改。
        3. **重要**：最后必须生成一个全新的 Idea 版本，并用 XML 标签包裹，格式如下：
           <SUGGEST_IDEA>
           (这里是修改后的完整 Idea 描述，不要包含原来的标题，只写描述内容)
           </SUGGEST_IDEA>
        """
        
    elif request.mode == 'critique':
        # 【功能 Calling】: 批判模式
        system_instruction = f"""
        你是一个严厉的审稿人 (Reviewer 2)。
        请基于【检索到的知识】：
        {knowledge_context}
        
        对用户的 Idea ({current_idea_text}) 进行批判。
        你需要指出逻辑漏洞、创新点不足或与现有文献冲突的地方。
        """

    else: # mode == 'chat'
        system_instruction = f"""
        你是一个科研助手。
        【相关对话历史】:
        {history_context}
        
        【相关知识库】:
        {knowledge_context}
        
        如果用户的问题和科研无关，请正常聊天。
        如果用户似乎在暗示要修改 Idea，请提示用户切换到“修改模式”。
        """

    # --- 4. 调用 LLM ---
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": request.query}
            ],
            stream=False
        )
        ai_content = response.choices[0].message.content

        # --- 5. 解析结果 (Function Result Parsing) ---
        suggested_idea = None
        
        # 只有在 update 模式下，才去尝试提取新 Idea
        if request.mode == 'update':
            import re
            match = re.search(r"<SUGGEST_IDEA>(.*?)</SUGGEST_IDEA>", ai_content, re.DOTALL)
            if match:
                suggested_idea = match.group(1).strip()
                # 把标签去掉，剩下的作为对话内容返回，或者你可以保留标签让前端处理
                # 这里我们选择在对话文本里隐藏掉那段冗长的定义，只留解释
                ai_content = ai_content.replace(match.group(0), "\n\n(已为您生成修改建议，请查看下方卡片👇)")

        # --- 6. 把 AI 的回复也存入 SQL ---
        ai_msg = models.Message(
            content=ai_content, # 这里存的是去掉了 XML 的纯文本
            role="ai",
            user_id=request.user_id,
            idea_id=request.idea_id
        )
        db.add(ai_msg)
        db.commit()

        # --- 7.  根据用户选择存储对话作为知识 ---
        # 如果用户在前台勾选了 "作为知识保存" (save_as_knowledge=True)
        # 我们就把这轮对话作为“高权重知识”立即存入向量库
        if request.save_as_knowledge:
            # 存入向量库
            memory_core.add_memory(
                text=f"【用户精选知识】\n问: {request.query}\n答: {ai_content}",
                metadata={
                    "user_id": request.user_id,
                    "idea_id": request.idea_id if request.idea_id else 0,
                    "role": "explicit_knowledge", # 显式知识标记
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            )
            print(f" >> 已手动固化知识: {request.query[:10]}...")

        # --- 8. 返回结果 ---
        return schemas.ChatResponse(
            response_text=ai_content,
            suggested_idea=suggested_idea,
            used_references=[r['content'][:20] for r in search_results],
            message_id=ai_msg.id
        )

    except Exception as e:
        print(f"Chat Error: {e}")
        return schemas.ChatResponse(
            response_text="系统出错了，请检查日志。",
            message_id=0
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




