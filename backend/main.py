'''
此代码为主函数（废话）
'''
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
import models, schemas, crud, services
from database import engine, get_db
from fastapi.middleware.cors import CORSMiddleware
import sleep as memory_sleep
from typing import List

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Research Engram V1 API")

# --- 暂时允许跨域请求 (CORS) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 允许所有来源 (开发阶段方便)
    allow_credentials=True,
    allow_methods=["*"], # 允许 GET, POST 等所有方法
    allow_headers=["*"],
)

# --- 接口: 注册用户 (使用 CRUD) ---
@app.post("/users/", response_model=schemas.UserResponse) # r_m 输出前过滤
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="用户名已存在")
    return crud.create_user(db=db, user=user)

# --- 接口: 上传论文 (PDF) ---
# 注意：这里用到了 "依赖注入" (Depends) 和 "异步" (async)
@app.post("/upload_paper/")
async def upload_paper( # 异步函数
    user_id: int = Form(...),    # 从表单获取 user_id
    idea_id: int = Form(...),    # 从表单获取 idea_id
    file: UploadFile = File(...), # 获取文件
    db: Session = Depends(get_db) # 获取数据库连接
):
    try:
        # 服务员(Main) 直接把活儿交给 厨师长(Service)
        # 这里的 await 意思是：厨师长你去处理吧，处理完了告诉我，我去招呼别的客人
        db_paper = await services.process_paper_upload(user_id, idea_id, file, db)
        return {"status": "success", "paper_id": db_paper.id, "title": db_paper.title}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 接口：论文列表 ---

@app.get("/ideas/{idea_id}/papers/", response_model=List[schemas.PaperResponse])
def get_idea_papers(idea_id: int, db: Session = Depends(get_db)):
    return db.query(models.Paper).filter(models.Paper.idea_id == idea_id).all()
    
# --- 接口： 智能对话 ---
# 前端对话框接这个
@app.post("/chat/", response_model=schemas.ChatResponse)
async def chat_endpoint(
    request: schemas.ChatRequest, 
    db: Session = Depends(get_db)
):
    try:

        return await services.chat_with_deepseek(db, request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 前端的“一键深度评审”
@app.post("/agent/critique/")
async def critique_endpoint(
    user_id: int = Form(...),
    query: str = Form(...), 
    idea_id: int = Form(...),
    db: Session = Depends(get_db)
):
    try:
        # 这里依然调用你原来的那个复杂的 Agent 逻辑
        critique_content = await services.critical_agent_chat(db, user_id, query, idea_id)
        # 注意：Agent 返回的是纯文本，不是 ChatResponse 对象，前端要注意区分
        return {"response": critique_content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 接口: 获取用户的所有 Idea ---
@app.get("/users/{user_id}/ideas/")
def get_user_ideas(user_id: int, db: Session = Depends(get_db)):
    return db.query(models.Idea).filter(models.Idea.user_id == user_id).all()

# --- 接口: 获取某个 Idea 的历史聊天记录 ---
@app.get("/ideas/{idea_id}/messages/")
def get_idea_messages(idea_id: int, db: Session = Depends(get_db)):
    # 按时间正序排列，方便前端直接显示
    return db.query(models.Message).filter(models.Message.idea_id == idea_id).order_by(models.Message.created_at.asc()).all()

# --- 接口: 创建新 Idea ---
@app.post("/ideas/")
def create_new_idea(idea: schemas.IdeaCreate, user_id: int, db: Session = Depends(get_db)):
    return crud.create_idea(db=db, idea=idea, user_id=user_id)

# --- 接口: 修改 Idea ---
@app.put("/ideas/{idea_id}")
def update_idea_endpoint(
    idea_id: int, 
    payload: dict, # 接收前端传来的 { "description": "..." }
    db: Session = Depends(get_db)
):
    new_desc = payload.get("description")
    if not new_desc:
        raise HTTPException(status_code=400, detail="描述不能为空")
        
    updated_idea = crud.update_idea_content(db, idea_id, new_desc)
    if not updated_idea:
        raise HTTPException(status_code=404, detail="Idea 不存在")
        
    return {"status": "success", "id": updated_idea.id, "new_description": updated_idea.description}

# --- 接口: 手动触发 sleep ---
@app.post("/system/sleep/")
def trigger_sleep_endpoint(
    user_id: int = Form(...),
    db: Session = Depends(get_db)
):
    # 1. 找用户
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    try:
        # 2. 调用 sleep.py 里的逻辑
        # 注意：process_one_user 函数没有返回值，它是直接打印和改数据库
        # 我们可以稍微修改 sleep.py 让它返回统计信息，或者直接运行
        memory_sleep.process_one_user(db, user)
        
        return {
            "status": "success", 
            "message": "大脑整理完成！画像已更新，新知识已固化。",
            "new_persona": user.persona # 把更新后的画像返给前端看看
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
