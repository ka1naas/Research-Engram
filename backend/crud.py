'''
此代码用于修改、存储数据
'''
from sqlalchemy.orm import Session
import models, schemas

# --- User 相关 ---
def get_user_by_username(db: Session, username: str): # 根据用户名找对象
    return db.query(models.User).filter(models.User.username == username).first()

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

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
    '''
    创建新idea
    '''
    db_idea = models.Idea(**idea.dict(), user_id=user_id)
    db.add(db_idea)
    db.commit()
    db.refresh(db_idea)
    return db_idea

def update_idea_content(db: Session, idea_id: int, new_content: str):
    """
    更新 Idea 的描述内容
    """
    # 1. 查找到这个 Idea
    db_idea = db.query(models.Idea).filter(models.Idea.id == idea_id).first()
    
    # 2. 如果找到了，就修改
    if db_idea:
        db_idea.description = new_content
        db.commit() # 提交保存
        db.refresh(db_idea) # 刷新数据
    
    return db_idea

# --- Paper 相关 (为 PDF 上传做准备) ---
def create_paper_record(db: Session, paper: schemas.PaperCreate, user_id: int):
    # 自动把 schema 里的所有字段（包括 full_text）都传进去
    db_paper = models.Paper(**paper.dict(), user_id=user_id)
    db.add(db_paper)
    db.commit()
    db.refresh(db_paper)
    return db_paper
