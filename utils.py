'''
此代码为llm可调用的工具（agent function calling）
'''
import json
import os
import openai
from dotenv import load_dotenv

load_dotenv()
client = openai.OpenAI(
    api_key=os.getenv('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com"
)

def generate_adversarial_keywords(user_idea: str):
    """
    【找茬器】: 根据用户的 Idea，生成专门用来搜索反驳证据的关键词。
    """
    prompt = f"""
    用户 Idea: "{user_idea}"
    请生成 3 个用于搜索**反对意见**、**局限性**或**替代方案**的关键词。
    例如用户说"CNN好"，你生成 ["CNN 缺点", "Transformer 优势", "CNN 局限"]。
    只输出 JSON 列表。
    """
    try:
        res = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            stream=False
        )
        return json.loads(res.choices[0].message.content.replace("```json", "").replace("```", "").strip())
    except:
        return [f"{user_idea} 局限性", f"反驳 {user_idea}"]

def calculate_conflict_score(user_idea: str, evidence: str):
    """
    【逻辑量化器】: 计算 Evidence 对 Idea 的逻辑冲击力 (0-10分)。
    """
    prompt = f"""
    【用户观点】: {user_idea}
    【检索到的论文片段】: {evidence}
    
    请分析：这个片段是否在逻辑上**反驳**、**削弱**或**限制**了用户的观点？
    请打分 (0-10)：
    - 0-3: 无关或支持。
    - 4-6: 指出了一些小缺陷。
    - 7-10: 核心逻辑冲突，或指出了致命局限。
    
    输出 JSON: {{"score": int, "reason": "简短理由"}}
    """
    try:
        res = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            stream=False
        )
        return json.loads(res.choices[0].message.content.replace("```json", "").replace("```", "").strip())
    except:
        return {"score": 0, "reason": "无法评估"}