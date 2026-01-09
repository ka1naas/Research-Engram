'''
此代码用于生成用户画像,提取对话内容，作为知识
'''
import time
import json
import os
import datetime
from sqlalchemy.orm import Session
from database import SessionLocal
import models
from vector_memory import VectorMemory
import openai
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 初始化 DeepSeek 客户端
client = openai.OpenAI(
    api_key=os.getenv('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com"
)

# 初始化向量库 (作为写入目标)
memory_core = VectorMemory()

def get_messages_since_last_sleep(db: Session, user: models.User):
    """
    从 SQL 中提取自上次睡眠以来的所有对话
    """
    # 查找所有 created_at > last_sleep_time 的消息
    new_msgs = db.query(models.Message).filter(
        models.Message.user_id == user.id,
        models.Message.created_at > user.last_sleep_time
    ).order_by(models.Message.created_at.asc()).all()
    
    return new_msgs

def generate_implicit_knowledge(user_id: int, chat_history_text: str):
    """
    【任务 B】: 隐式知识固化
    让 AI 像看课堂笔记一样，从对话中总结出知识点
    """
    system_prompt = """
    你是一个科研知识整理员。你的任务是阅读用户的聊天记录，提取出**长期有价值的科研知识**。
    
    请提取以下类型的内容：
    1. 用户确认过的 Idea 细节或修改方向。
    2. 明确的科研结论或实验约束条件。
    3. 有价值的参考文献或理论依据。
    
    ❌ 忽略以下内容：
    - 闲聊 ("你好", "谢谢")
    - 过程性的纠结 ("我再想想")
    - 简单的指令 ("帮我改一下")

    如果提取到了知识，请输出 JSON 列表，格式：
    [{"content": "知识点内容...", "tags": ["Idea迭代", "CV"]}]
    
    如果没有提取到任何有价值的知识，请直接输出空列表 []。
    """
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"【今日对话记录】:\n{chat_history_text}"}
            ],
            stream=False
        )
        content = response.choices[0].message.content
        # 清洗一下 markdown
        content = content.replace("```json", "").replace("```", "").strip()
        knowledge_list = json.loads(content)
        return knowledge_list
    except Exception as e:
        print(f"  [知识提取失败] {e}")
        return []

def update_user_persona(current_persona: str, chat_history_text: str):
    """
    【任务 A】: 更新用户画像
    """
    system_prompt = """
    你是一个用户画像侧写师。请根据今日的对话更新用户的【科研画像】。
    
    策略：
    1. **验证**：强化已验证的特征。
    2. **修正**：如果发现用户改变了研究方向（如从 NLP 转做 CV），请修正画像。
    3. **新增**：发现新的偏好或习惯。
    
    请直接输出更新后的 JSON 列表（不要废话），例如：["研究方向: Transformer", "偏好: PyTorch"]
    """
    
    user_prompt = f"""
    【旧画像】: {current_persona}
    【今日对话】: {chat_history_text}
    """
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            stream=False
        )
        content = response.choices[0].message.content.replace("```json", "").replace("```", "").strip()
        # 简单验证一下是不是 JSON
        json.loads(content) 
        return content
    except Exception as e:
        print(f"  [画像更新失败] {e}")
        return current_persona # 失败了就返回旧的，别改坏了

def process_one_user(db: Session, user: models.User):
    print(f"\n💤 用户 [{user.username}] 进入睡眠处理...")

    # 1. 获取新记忆 (从 SQL 读取)
    new_msgs = get_messages_since_last_sleep(db, user)
    
    if not new_msgs:
        print("  -> 无新对话，跳过。")
        # 即使没有新对话，也可以选择更新一下时间，或者不做操作
        return

    print(f"  -> 发现 {len(new_msgs)} 条新对话，开始大脑整理...")
    
    # 拼装对话文本
    chat_text = ""
    for msg in new_msgs:
        chat_text += f"[{msg.role}]: {msg.content}\n"

    # 2. 执行任务 A: 更新画像
    new_persona = update_user_persona(user.persona, chat_text)
    if new_persona != user.persona:
        print(f"  -> 画像已更新")
        user.persona = new_persona
    
    # 3. 执行任务 B: 隐式知识提取 (The Magic)
    knowledge_list = generate_implicit_knowledge(user.id, chat_text)
    
    if knowledge_list:
        print(f"  -> 提炼出 {len(knowledge_list)} 条隐式知识，正在固化...")
        for k in knowledge_list:
            text = k.get('content', '')
            if text:
                # 存入向量库
                memory_core.add_memory(
                    text=f"【睡眠整理知识】{text}",
                    metadata={
                        "user_id": user.id,
                        "role": "implicit_knowledge", # 关键标记：这是睡觉得来的
                        "source": "sleep_consolidation",
                        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                )
    else:
        print("  -> 今日对话主要是闲聊，未提取到深度知识。")

    # 4. 标记睡眠完成
    user.last_sleep_time = datetime.datetime.utcnow()
    db.commit()
    print(f"  -> [{user.username}] 睡眠结束，精力已恢复。")

def run_sleep_cycle():
    """
    主程序
    """
    print("=== 研究助手后台睡眠系统启动 ===")
    db = SessionLocal()
    try:
        users = db.query(models.User).all()
        for user in users:
            process_one_user(db, user)
    finally:
        db.close()
        print("=== 睡眠周期结束 ===")

if __name__ == "__main__":
    run_sleep_cycle()