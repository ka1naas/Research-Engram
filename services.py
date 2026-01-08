'''
功能b先帮用户生成或改进idea（此时用户
没有idea或者用户其实本身已经知道idea有问题，才会选择让ai帮忙迭代）
而功能c，是在用户已经有idea的情况下，需要一点批评时才采用的
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


    print("论文成存入！")

    return db_paper

# ================= 功能B：接收idea/None，llm提取摘要总结new idea/idea存入向量库 =================
async def chat_with_deepseek(
    db: Session, 
    request: schemas.ChatRequest
):
    # 1. 获取上下文信息
    user = db.query(models.User).filter(models.User.id == request.user_id).first()
    if not user:
        raise Exception('User not found')
    
    # 获取用户画像
    user_persona = user.persona if user.persona else "该用户暂无画像"

    # 2. 判定场景（有无用户idea）并组装对应的prompt
    #初始化
    context_info = "" # 用户prompt
    system_instruction = "" # 系统prompt

    # 记忆检索
    #如果有idea，搜idea相关，如果没有，全搜索
    query_for_search = request.query
    search_results = memory_core.search_memory(query_for_search)
    memory_context = '\n'.join([f"- {r['content']}" for r in search_results])

    # -- 分割场景 --
    # 如果目前对话用户已经绑定了idea
    if request.idea_id:
        idea = db.query(models.Idea).filter(models.Idea.id == request.idea_id).first()
        context_info += f"\n【当前讨论的 Idea】: {idea.title}\n{idea.description}\n"

        if request.paper_id:
            # 场景 1: 有Idea也有Paper
            paper = db.query(models.Paper).filter(models.Paper.id == request.paper_id)
            context_info += f"\n【当前参考的 Paper】: {paper.title}\n摘要: {paper.abstract}\n"
            system_instruction = """
                你是一个严谨的科研合作者。
                你的任务是：基于用户提供的 Paper，批判性地审视用户的 Idea。
                请指出 Idea 与 Paper 的联系、潜在的矛盾点，或 Paper 如何能支撑这个 Idea。
                """
        
        else:
            # 场景 2：只有idea没有Paper
            system_instruction = """
            你是一个科研导师。用户正在构思一个 Idea，但他可能还没想清楚。
            你的任务是：帮助用户完善这个 Idea，通过提问或建议，让 Idea 变得更具体、更有逻辑。
            如果用户要求，请帮助修改 Idea 的描述。
            """
    
    #如果用户没有绑定Idea
    elif request.paper_id:
        # 场景 3： 只有Paper没有Idea
        paper = db.query(models.Paper).filter(models.Paper.id == request.paper_id)
        context_info += f"\n【当前参考的 Paper】: {paper.title}\n摘要: {paper.abstract}\n"
        system_instruction = """
            你是一个严谨的科研合作者。
            你的任务是：基于用户提供的 Paper，总结出与用户研究相关的 Idea。
            并请指出 Idea 与 Paper 的联系，或 Paper 如何能支撑这个 Idea。
            """
        
    else:
        # 场景 4： 没有idea也没有paper
        system_instruction = """
        你是一个科研灵感助手。用户目前没有指定具体的 Idea。
        你的任务是：通过对话引导用户挖掘他们的想法。
        【重要】：如果你敏锐地发现用户正在表达一个成型的科研想法，请在回答的最后，
        用特殊标记（如 <SUGGEST_IDEA>内容</SUGGEST_IDEA>）总结出这个 Idea，以便系统提取。
        """
    
    # 3. 最终拼接prompt
    final_prompt = f"""
    {system_instruction}
    
    【用户画像】:
    {user_persona}
    
    【相关历史记忆】:
    {memory_context}
    
    【当前上下文】:
    {context_info}
    """

    # 4. 调用 DeepSeek (这是之前缺失的部分)
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": final_prompt},
                {"role": "user", "content": request.query}
            ],
            stream=False
        )
        ai_content = response.choices[0].message.content

        # 5. 解析是否有新 Idea 建议
        suggested_idea = None
        # 使用正则提取 <SUGGEST_IDEA> 标签里的内容
        match = re.search(r"<SUGGEST_IDEA>(.*?)</SUGGEST_IDEA>", ai_content, re.DOTALL)
        if match:
            suggested_idea = match.group(1).strip()
            # 移除标签，保持回复整洁
            ai_content = ai_content.replace(match.group(0), "\n\n(系统提示：已为您捕捉到一个新灵感，请查看建议卡片)")

        # 6. 处理显式知识存储 (如果用户勾选了 "保存为知识")
        if request.save_as_knowledge:
            memory_core.add_memory(
                text=f"【用户精选知识】问:{request.query}\n答:{ai_content}",
                metadata={
                    "user_id": request.user_id,
                    "role": "explicit_knowledge",
                    "heat": 999, # 标记为高热度
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            )

        # 7. 返回标准响应对象 (Schemas 需要定义 ChatResponse)
        return schemas.ChatResponse(
            response_text=ai_content,
            suggested_idea=suggested_idea,
            used_references=[r['content'][:20] for r in search_results]
        )

    except Exception as e:
        print(f"Chat Error: {e}")
        # 返回一个包含错误信息的响应
        return schemas.ChatResponse(response_text="抱歉，系统暂时繁忙，请稍后再试。")

# ================= 功能C：进行对抗性检索 =================  
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




