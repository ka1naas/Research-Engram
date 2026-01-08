'''
此代码用于检查传入传出的数据
'''
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from typing import List, Optional, Literal

# --- 基础模型 (Base) ---
# 这些是 Idea 共有的一些属性
class IdeaBase(BaseModel):
    title: str
    description: Optional[str] = None

# --- 创建时用的模型 (Create) ---
# 用户创建 Idea 时，只需要传标题和描述
class IdeaCreate(IdeaBase):
    pass

# --- 读出时用的模型 (Response) ---
# 返回给前端时，我们需要告诉它 ID、创建时间、属于谁
class IdeaResponse(IdeaBase):
    id: int
    user_id: int
    created_at: datetime

    # 这一行必须加！允许 Pydantic 读取 ORM 模型数据
    class Config:
        from_attributes = True

# --- User 相关的模型 ---
class UserCreate(BaseModel): 
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    # 不读取password，防止泄露
    
    # 嵌套显示该用户的 ideas (这就是 relationship 的好处)
    ideas: List[IdeaResponse] = []

    class Config:
        from_attributes = True

# --- Paper 相关的模型 ---
class PaperCreate(BaseModel):
    title: str
    abstract: str
    idea_id: int # 必须指定属于哪个 Idea

class PaperResponse(BaseModel):
    id: int
    title: str
    abstract: str
    idea_id: int
    
    class Config:
        from_attributes = True

# 聊天请求：前端发给后端的
class ChatRequest(BaseModel):
    user_id: int
    query: str
    idea_id: Optional[int] = None   # 如果不传idea，就是闲聊/未定义
    paper_id: Optional[int] = None  # 针对特定论文
    
    # 允许用户显式控制：是否将这句话存为长期知识？
    save_as_knowledge: bool = False

# 聊天响应：后端回给前端的
class ChatResponse(BaseModel):
    response_text: str # AI总结的新Idea
    suggested_idea: Optional[str] = None # 是否通过新idea，可为空值
    used_references: List[str] = [] # 本次对话引用的记忆，必须是列表