import os
from sqlalchemy.orm import Session
from pypdf import PdfReader
from fastapi import UploadFile
import schemas, crud
from vector_memory import VectorMemory
import time

# 初始化向量记忆库（单例模式：整个系统只用这一个实例，避免重复加载模型）
# 注意：这里我们假设 vector_memory.py 在同一目录下
memory_core = VectorMemory()

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
    pdf_file = io.BytesIO(content)
    reader = PdfReader(pdf_file)
    
    full_text = ""
    for page in reader.pages:
        full_text += page.extract_text() + "\n"
    
    # 简单的摘要生成 (实际可以用 LLM 生成，这里先截取前500字作为摘要)
    abstract = full_text[:500] + "..."
    title = file.filename # 暂时用文件名当标题

    # 2. 调用 CRUD 层：存入 SQL 数据库
    # 这一步是为了保证无论向量库挂没挂，我们的基础数据都在
    paper_schema = schemas.PaperCreate(title=title, abstract=abstract, idea_id=idea_id)
    db_paper = crud.create_paper_record(db=db, paper=paper_schema, user_id=user_id)

    # 3. 调用 VectorMemory：存入向量数据库
    # 我们把 paper_id 存进去，这样以后检索到向量，能反向查到 SQL 里的完整信息
    metadata = {
        "role": "paper",
        "user_id": user_id,
        "idea_id": idea_id,
        "paper_db_id": db_paper.id, # 关键：建立 SQL 和 Vector 的联系
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S") 
    }
    
    # 将全文切片存储（这里简单存全文，后续需优化为切片存储）
    memory_core.add_memory(
        text=full_text[:2000], # 向量库通常有长度限制，先存前2000字
        metadata=metadata,
        mem_id=f"paper_{db_paper.id}"
    )

    return db_paper