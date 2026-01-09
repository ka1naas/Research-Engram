from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
import models, schemas, crud, services
from database import engine, get_db
from fastapi.middleware.cors import CORSMiddleware

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
    
# ---接口： 智能对话 ---
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