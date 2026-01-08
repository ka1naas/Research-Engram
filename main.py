from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
import models, schemas, crud, services
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Research Engram V1 API")

# --- 接口: 注册用户 (使用 CRUD) ---
@app.post("/users/", response_model=schemas.UserResponse) # r_m 输出前过滤
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="用户名已存在")
    return crud.create_user(db=db, user=user)

# --- 接口: 核心功能 - 上传论文 (PDF) ---
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