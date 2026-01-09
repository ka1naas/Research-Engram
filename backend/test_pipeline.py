'''
这个代码是简单的测试示例，可以在代码中更改问题，进行你想要的测试，但是还不能测试长距离对话
注意，你需要自己创建.env文件，使用自己的api，目前代码的模型仅限于deepseek，你要是闲的可以自己改
'''
import requests

BASE_URL = "http://127.0.0.1:8000"

def run_test():
    print("=== 开始测试科研助手后端流程 ===")

    # 1. 注册一个测试用户
    username = "test_scholar_001"
    try:
        resp = requests.post(f"{BASE_URL}/users/", json={
            "username": username,
            "password": "password123"
        })
        if resp.status_code == 200:
            user_data = resp.json()
            user_id = user_data['id']
            print(f"✅ 用户注册成功: ID={user_id}")
        else:
            print("用户可能已存在，尝试获取ID...")
            # 这里简化处理，假设ID是1（实际开发中应该去查库，或者重置数据库）
            user_id = 1 
    except Exception as e:
        print(f"连接失败: {e}")
        return

    # 2. 模拟对话：创建一个 Idea 上下文
    # 注意：我们这里不直接调 /chat/ 创建 Idea，因为 Idea 应该是用户在界面填写的。
    # 我们假设数据库里已经有了一个 Idea (你需要手动去数据库插一条，或者我们先发一条空聊)
    
    # 我们用 Chat 模式强行假装有个 Idea ID = 1 (假设你还没清空数据库)
    idea_id = 1 
    
    # 3. 测试：普通的闲聊 (Chat Mode)
    print("\n--- 测试 1: 普通闲聊 ---")
    payload_chat = {
        "user_id": user_id,
        "query": "DeepSeek是什么模型？",
        "idea_id": None, # 闲聊不绑定Idea
        "mode": "chat",
        "history_len": 3
    }
    resp = requests.post(f"{BASE_URL}/chat/", json=payload_chat)
    print(f"AI回复: {resp.json()['response_text'][:50]}...")

    # 4. 测试：请求改进 Idea (Update Mode)
    print("\n--- 测试 2: 改进 Idea (核心功能) ---")
    # 假设用户想把 Idea 改成关于 Transformer 的
    payload_update = {
        "user_id": user_id,
        "query": "我觉得目前的Idea太老旧了，帮我结合 Transformer 架构进行改进。",
        "idea_id": idea_id, 
        "mode": "update", # <--- 关键：触发 Function Calling
        "history_len": 3,
        "save_as_knowledge": True # <--- 测试手动保存
    }
    
    resp = requests.post(f"{BASE_URL}/chat/", json=payload_update)
    data = resp.json()
    
    print(f"AI回复主体: {data['response_text'][:50]}...")
    
    if data['suggested_idea']:
        print(f"🎉 成功捕捉到新 Idea 建议!\n内容预览: {data['suggested_idea'][:100]}...")
    else:
        print("⚠️ 未捕捉到新 Idea (可能 AI 觉得不需要改，或者 Prompt 没生效)")

    # 5. 测试：深度逻辑体检 (使用 Utils 的那个 Agent)
    print("\n--- 测试 3: 深度 Agent ---")
    # 注意：这个接口用的是 Form data，不是 JSON
    data_critique = {
        "user_id": user_id,
        "query": "使用 Transformer 进行图像分类",
        "idea_id": idea_id
    }
    resp = requests.post(f"{BASE_URL}/agent/critique/", data=data_critique)
    print(f"深度体检报告: {resp.json()['response'][:100]}...")

if __name__ == "__main__":
    run_test()