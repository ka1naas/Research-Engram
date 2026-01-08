'''
此代码用于创建数据库
'''
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

# 数据库放在当前目录，叫 research.db
SQLALCHEMY_DATABASE_URL = "sqlite:///./research.db"

# 创建引擎
# check_same_thread=False 是 SQLite 在 Web 框架下必须的设置
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 创建会话工厂，一个引擎可以对应许多不同的会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 初始化数据库，根据model中的base进行创建
def init_db():
    print("正在初始化数据库...")
    Base.metadata.create_all(bind=engine)
    print("数据库文件 research.db 已生成！")

# 给 FastAPI 用的依赖项 (借用数据库连接，用完自动关)
def get_db():
    db = SessionLocal()
    try:
        yield db # 吐出db并暂停
    finally:
        db.close()

# 如果直接运行这个文件，就执行初始化
if __name__ == "__main__":
    init_db()