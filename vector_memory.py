'''
此代码用于管理向量知识库，包含：记忆添加、普通记忆检索、睡眠记忆检索
'''
import chromadb
from chromadb.utils import embedding_functions
import os

class VectorMemory:
    def __init__(self,collection_name='memory_core'):
        #1.初始化客户端
        self.client = chromadb.PersistentClient(path='./chroma_db')

        #2.设置嵌入模型
        #获取本地模型path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.local_model_path = os.path.join(current_dir, 'models', 'all-MiniLM-L6-v2')
    
        self.embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name = self.local_model_path
        )

        #3.创建记忆集合
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_func
        )

    def add_memory(self,text,metadata=None,mem_id=None):
        '''
        存储记忆
        text:记忆内容
        metadata:附加信息（时间、来自用户还是ai）
        mem_id:唯一id
        '''
        if mem_id == None:
            import time
            mem_id = str(time.time())

        self.collection.add(
            documents=[text], #原始文字
            metadatas=[metadata], #附加标记
            ids=[mem_id] #timestamp
        )
        print(f"[Chroma] 已存入: {text[:20]}...")
    
    def get_new_memory_for_sleep(self,last_timestamp='1970-01-01 00:00:00',limit=100):
        '''
        为sleep准备数据
        last_timestamp:上次运行sleep的时间
        limit:读取记忆限制数目
        '''
        new_memory = self.collection.get(
            limit=limit,
            include=['documents','metadatas']
        ) 
        new_memories = []
        if new_memory["ids"]:
            for i in range(len(new_memory["ids"])):
                meta = new_memory['metadatas'][i]
                doc = new_memory["documents"][i]
                mem_time = meta.get("timestamp",'0000-00-00')

                #筛选上次sleep后的数据
                if last_timestamp < mem_time:
                    new_memories.append({
                        'content':doc,
                        'metadata':meta
                    })
        #按时间排序
        new_memories.sort(key=lambda x: x['metadata'].get('timestamp',''))
        return new_memories

    def search_memory(self,query_text,n_results=3,threshold=1):
        '''
        检索记忆
        query_text:检索的问题
        n_result:返回几条
        '''
        results = self.collection.query(
            query_texts=[query_text],
            n_results=n_results
        )

        #对返回的数据做数据清洗
        # results['documents'][0] 是内容列表，n个query，n个列表[text1,text2...]
        # results['distances'][0] 是距离列表，每个text对应的距离
        # results['metadatas'][0] 是元数据列表,metadata={
        #"role": "user",# 是谁说的？
        #"timestamp": "2023-10-27..."  # 什么时候说的？}
        clean_result = []
        seen_content = set() #初始化一个集合，用来记录见过的内容
        if results['documents']:
            for i,doc in enumerate(results['documents'][0]): #i是索引，doc是文本内容
                #阈值限制
                if results["distances"][0][i] > threshold:
                    continue
                #去重
                if doc in seen_content:
                    continue
                seen_content.add(doc)
                meta = results['metadatas'][0][i]
                distance = results["distances"][0][i]
                clean_result.append({
                    'content':doc,
                    'metadata':meta,
                    'distance':distance
                })
        return clean_result
    
if __name__ == "__main__":
    # 测试代码
    vm = VectorMemory()
    
    # 1. 存点假数据
    print("正在写入数据...")
    vm.add_memory("也就是岩土工程中土体的本构关系", metadata={"role": "user", "time": "2023-01-01"})
    vm.add_memory("今天中午吃了黄焖鸡米饭", metadata={"role": "user", "time": "2023-01-02"})
    vm.add_memory("DeepSeek 是一个强大的大语言模型", metadata={"role": "ai", "time": "2023-01-03"})
    
    # 2. 查一下
    query = "土体工程性质"
    print(f"\n🔍 正在搜索: {query}")
    results = vm.search_memory(query)
    
    for r in results:
        print(f"找到: {r['content']} (时间: {r['metadata']['time']})")





