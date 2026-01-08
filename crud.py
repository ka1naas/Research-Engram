'''
此代码用于存储数据
'''
from sqlalchemy.orm import Session
import models, schemas

# --- User 相关 ---
def get_user_by_username(db: Session, username: str): # 根据用户名找对象
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, user: schemas.UserCreate):
    # 这里只是简单的存数据，不涉及复杂逻辑
    fake_hashed_password = user.password + "notreallyhashed"
    db_user = models.User(username=user.username, password_hash=fake_hashed_password)
    db.add(db_user) # 将对象加入对话，等待提交
    db.commit() # 写入数据库
    db.refresh(db_user) # 重新加载对象属性
    return db_user

# --- Idea 相关 ---
def create_idea(db: Session, idea: schemas.IdeaCreate, user_id: int):
    db_idea = models.Idea(**idea.dict(), user_id=user_id)
    db.add(db_idea)
    db.commit()
    db.refresh(db_idea)
    return db_idea

# --- Paper 相关 (为 PDF 上传做准备) ---
def create_paper_record(db: Session, paper: schemas.PaperCreate, user_id: int):
    # 这里只存 SQL 里的元数据（标题、摘要等）
    db_paper = models.Paper(**paper.dict(), user_id=user_id)
    db.add(db_paper)
    db.commit()
    db.refresh(db_paper)
    return db_paper