'''
此程序是用来定义数据库蓝图长什么样的
'''
from sqlalchemy import Column, Integer, String, ForeignKey, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime

#定义数据库模型的基类 python class => SQL
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    #primary_key=True:主键
    #index=True：自动编号
    #unique=True:确保唯一性
    id = Column(Integer,primary_key=True,index=True)
    username = Column(String,unique=True,index=True)
    password_hash = Column(String) # 存储加密后的密码
    persona = Column(Text,default='')
    last_sleep_time = Column(DateTime,default=datetime.datetime(1970, 1, 1))

    ideas = relationship("Idea", back_populates="owner")
    papers = relationship("Paper", back_populates="uploader")

class Idea(Base):
    __tablename__ = 'ideas'
    
    #ForeignKey():外键
    #default=datetime.datetime.utcnow:默认为utc时间
    id = Column(Integer,primary_key=True,index=True)
    title = Column(String)
    description = Column(Text)
    user_id = Column(Integer,ForeignKey('users.id'))
    created_at = Column(DateTime,default=datetime.datetime.utcnow)

    owner = relationship("User", back_populates="ideas")
    papers = relationship("Paper", back_populates="idea")
    messages = relationship("Message", back_populates="idea", cascade="all, delete-orphan")

class Paper(Base):
    __tablename__ = "papers"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    abstract = Column(Text) # 论文摘要
    idea_id = Column(Integer, ForeignKey("ideas.id")) # 这篇论文关联到了哪个 Idea
    user_id = Column(Integer, ForeignKey("users.id"))

    #保存Paper全文
    full_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    #关联到Idea和User，back_populates表示建立双向关系
    idea = relationship("Idea",back_populates="papers")
    uploader = relationship('User',back_populates='papers')

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text) # 聊天具体内容
    role = Column(String)  # 是 "user" 说的还是 "ai" 说的
    created_at = Column(DateTime, default=datetime.datetime.utcnow) # 什么时候说的
    user_id = Column(Integer, ForeignKey("users.id"))
    idea_id = Column(Integer, ForeignKey("ideas.id"), nullable=True) # 可以为空（闲聊模式）

    idea = relationship("Idea", back_populates="messages")