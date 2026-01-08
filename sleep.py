import json
import time
from vector_memory import VectorMemory
import openai
from dotenv import load_dotenv
#from utils import STOP_WORDS
import os

#加载api用于“做梦”
load_dotenv('.env')
client = openai.OpenAI(
    api_key=os.getenv('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com"
)

def sleep_and_consolidate(LM_path='long_m.json'):#Hippocampus
    #初始化睡眠时间 & 用户画像
    #last_sleep_time = '1970-01-01 00:00:00'
    #current_persona = []

    if os.path.exists(LM_path):
        try:
            with open(LM_path,'r',encoding='utf-8') as f:
                data = json.load(f)
                #获取旧画像
                current_persona = data.get('user_persona',[])
                last_sleep_time = data.get('last_sleep_time','1970-01-01 00:00:00')
        except Exception as e:
            print(f'when getting lm:{e}')

    #print(f"[调试] 系统认为上次睡觉时间是: {last_sleep_time}")

    Hippocampus = VectorMemory()

    #count = Hippocampus.collection.count()
    #print(f"[调试] 向量数据库中现有记忆总数: {count} 条")
    #print(Hippocampus.collection.get(
            #include=['metadatas']
        #) )

    #获取记忆
    new_memories = Hippocampus.get_new_memory_for_sleep(last_timestamp=last_sleep_time)

    if not new_memories:
        print('nothing new,no need to sleep')
        return
    print(f'there are {len(new_memories)} new memories,start to sleep.')

    #整理记忆给llm学习
    memory_text = ''
    for mem in new_memories:
        meta = mem.get('metadata',{})
        timestamp = meta.get('timestamp','unknow timestamp')
        role = meta.get('role','unknown')
        content = mem.get('content','')
        memory_text += f'-[{timestamp}{role}:{content}]\n'
    
    #利用llm思考
    system_prompt = '''
    你是一个负责整理记忆的“大脑皮层”。
    任务：根据【新记忆】和【旧画像】，更新用户画像。
    要求：
    1. 提取用户的新属性（如职业、爱好、项目、性格偏好）。
    2. 如果新信息与旧画像冲突，以新的为准。
    3. 合并相似的信息。
    4. 输出纯 JSON 列表，不要包含 Markdown 格式或其他废话。
    '''
    #将 current_persona 对象转换为 JSON 格式的字符串，
    # ensure_ascii=False 确保非 ASCII 字符（如中文）正常显示而不被转义。
    user_prompt = f'''
    【已有的用户画像】：
    {json.dumps(current_persona, ensure_ascii=False)}

    【今日新记忆 (自 {last_sleep_time} 起)】：
    {memory_text}

    请输出更新后的用户画像列表：
    '''

    try:
        #调用 LLM
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
        #将 JSON 格式字符串 new_persona_json 解析为
        #对应的 Python 对象（如字典、列表等），并赋值给变量 new_traits。
        new_traits = json.loads(new_persona_json)
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        save_data = {
            "user_persona": new_traits,
            "last_sleep_time": current_time}
        
        with open(LM_path,'w',encoding='utf-8') as f:
            json.dump(save_data,f,ensure_ascii=False,indent=4)
        
        print('get new persona!')
        for trait in new_traits:
            print(f' -{trait}')
        
    except Exception as e:
        print(f"[噩梦] 睡眠处理失败: {e}")
        # 打印原始返回以便调试
        if 'response' in locals():
            print(f"LLM 原始返回: {response.choices[0].message.content}")


        
        
if __name__ == "__main__":
    sleep_and_consolidate()




