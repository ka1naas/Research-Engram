'''
此代码用于生成用户画像,提取对话内容
'''
import time
import json
import os
from sqlalchemy.orm import Session
from database import SessionLocal # 👈 从这里拿数据库连接器
import models
from vector_memory import VectorMemory
import openai
from dotenv import load_dotenv
import datetime

#加载api用于“做梦”
load_dotenv('.env')
client = openai.OpenAI(
    api_key=os.getenv('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com"
)

memory_core = VectorMemory()

def process_one_user(db: Session, user: models.User):#Hippocampus
    """
    负责处理单个用户的睡眠逻辑,提取用户画像，实现知识固化以及非知识剔除
    """

    print(f" 用户 {user.username} 进入睡眠...")

    # 1. 获取上次睡觉时间
    # 数据库里取出来的是 datetime 对象，转成字符串给向量库用
    last_sleep_str = str(user.last_sleep_time)

    # 2. 去海马体（向量库）找新记忆
    new_memories = memory_core.get_new_memory_for_sleep(last_timestamp=last_sleep_str)
    my_new_memories = [
        m for m in new_memories 
        if m['metadata'].get('user_id') == user.id
    ]
    if not my_new_memories:
        print(f"用户 {user.username} 没有新记忆，无需整理。")
        return
# ================= 任务 A: 更新用户画像 (User Traits) =================
    # 3. 整理记忆，准备prompt
    memory_text_buffer = ''
    high_heat_memories = []
    for mem in my_new_memories:
        meta = mem.get('metadata',{})
        timestamp = meta.get('timestamp','unknow timestamp')
        role = meta.get('role','unknown')
        content = mem.get('content','')
        memory_text_buffer += f'-[{timestamp}{role}:{content}]\n'
    
    #利用llm思考
    system_prompt = '''
    你是一个专业的用户画像侧写师。
    你的任务是：维护和更新用户的【长期科研画像】。
    
    输入包含：
    1. 【旧画像】：用户已有的画像标签。
    2. 【新记忆】：最近发生的交互内容。

    请遵循以下更新策略（Update Strategy）：
    1. **验证 (Verify)**：如果新记忆证实了旧画像（例如旧画像说“做CV”，新记忆也是CV），则保留并强化权重。
    2. **修正 (Correct)**：如果新记忆与旧画像直接冲突（例如旧画像说“只用PyTorch”，新记忆显示“开始转用JAX”），请以新记忆为准进行修正，并标记为“最近转变”。
    3. **新增 (Append)**：如果发现了全新的特征，加入画像。
    4. **遗忘 (Decay)**：不要无故删除旧画像，除非它们明显过时或错误。
    
    输出格式：
    请输出一个更新后的 JSON 列表。
    '''
    #将 current_persona 对象转换为 JSON 格式的字符串，
    # ensure_ascii=False 确保非 ASCII 字符（如中文）正常显示而不被转义。
    user_prompt = f'''
    【已有的用户画像】：
    {json.dumps(user.persona, ensure_ascii=False)}

    【今日新记忆 (自 {last_sleep_str} 起)】：
    {memory_text_buffer}

    请输出更新后的用户画像列表：
    '''

    try:
        #4. 调用 LLM
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            stream=False
        )

        #获取结果
        new_persona_json = response.choices[0].message.content
        #去除markdown
        new_persona_json = new_persona_json.replace("```json", "").replace("```", "").strip()

        # 5.更新数据库
        print(f'更新画像：{new_persona_json}')

        user.persona = new_persona_json
        user.last_sleep_time = datetime.datetime.utcnow()
        db.commit()

        
    except Exception as e:
        print(f"[噩梦] 睡眠处理失败: {e}")
        # 打印原始返回以便调试
        db.rollback() # 如果出错，回滚数据库，防止坏数据
        if 'response' in locals():
            print(f"LLM 原始返回: {response.choices[0].message.content}")   


        
def run_sleep_cycle():
    """
    主循环：打开数据库，遍历所有用户
    """
    print("=== 开始全员睡眠周期 ===")
    
    # 1. 手动创建数据库会话
    db = SessionLocal()
    
    try:
        # 2. 查出所有用户
        users = db.query(models.User).all()
        
        # 3. 挨个处理
        for user in users:
            process_one_user(db, user)
            
    finally:
        # 4. 无论如何，最后一定要关闭连接！
        db.close()
        print("=== 睡眠周期结束，连接已关闭 ===")

if __name__ == "__main__":
    run_sleep_cycle()




