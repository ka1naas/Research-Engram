# 🧠 Research Engram
> **基于仿生记忆固化机制 (Memory Consolidation) 的科研灵感伴侣**
>
> **Biomimetic Research Assistant with Sleep-Dependent Memory Consolidation**

![Python](https://img.shields.io/badge/Python-3.10-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-High%20Performance-green) ![RAG](https://img.shields.io/badge/RAG-Agentic-purple) ![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek_V3-orange)

[中文](#-中文介绍) | [English](#-english-introduction)

---

## 🇨🇳 中文介绍

### 📖 设计哲学：Why "Engram"?

在神经科学中，**Engram (记忆痕迹)** 是指记忆在大脑神经元网络中留下的物理印记。人类的记忆并非数据的简单堆砌，而是一个动态的**编码 (Encoding)**、**巩固 (Consolidation)** 与 **再激活 (Retrieval)** 的过程。

现有的 LLM 对话系统往往受限于 Context Window，面临“灾难性遗忘”的问题——它们只有短暂的“工作记忆”。**Research Engram** 旨在赋予 AI 一个可生长的“海马体”，通过模拟人类的**睡眠记忆固化 (Sleep-Dependent Memory Consolidation)** 机制，将碎片化的灵感转化为长期的认知资产，解决科研场景下的灵感碎片化与记忆丢失问题。

### 🧬 核心仿生架构与技术实现

本项目在工程上复现了生物记忆的三大核心过程：

#### 1. 记忆编码 (Encoding) - *工作记忆*
用户与 AI 的实时对话流被视为瞬时信号。系统采用 **Sentence Transformers** (`all-MiniLM-L6-v2`) 将非结构化文本转化为高维语义向量，并支持双模态检索策略：
* **专注模式 (Focus)**：利用 Metadata Filtering 仅检索当前 Project ID 下的上下文，确保严谨性。
* **联想模式 (Associative)**：跨项目检索相似向量，模拟大脑的“发散性思维”以触发灵感迁移。

#### 2. 记忆固化 (Consolidation) - *The Sleep Mechanism*
这是本项目的核心创新。如同人类在睡眠中将海马体的短期记忆转移至新皮层，`Sleep` 模块作为一个基于 **Celery/AsyncIO** 的异步离线进程，负责：
* **噪声清洗**：利用 LLM 识别并丢弃低信息熵的闲聊数据。
* **隐式知识提取**：自动提炼对话中的 Insight（如“用户偏好 Transformer 架构”），并结构化存入 **SQLAlchemy** 关系型数据库。
* **画像重塑 (Plasticity)**：根据提取的知识动态更新 User Persona，实现 AI 认知的神经可塑性。

#### 3. 记忆检索 (Retrieval) - *基于线索的再激活*
系统实现了 **Agentic Retrieval**（自主决策检索）。Agent 不再是被动的问答机器，而是像人类回忆往事一样，通过捕捉当前语境中的“检索线索 (Retrieval Cues)”，利用 **Function Calling** 自主判断是否需要激活沉睡的历史记忆（查询 **ChromaDB** 向量库）。

#### 4. 对抗式检索 - *批判精神*
针对科研场景，在记忆固化阶段就加入对抗式的批判内容。Agent 不再是单纯的知识问答，而是像一个科研合作者一样，通过回忆批判记忆，针对当前的idea和对话内容进行评估，输出探讨内容。

### 🛠️ 技术栈 (Tech Stack)

| 模块 | 技术选型 | 用途 |
| :--- | :--- | :--- |
| **Backend** | Python, FastAPI | 高性能异步后端 API 服务 |
| **LLM & Agent** | DeepSeek V3 API | 核心推理引擎与意图识别 |
| **Embedding** | **Sentence Transformers** | 本地化高性能文本向量化 |
| **Vector DB** | ChromaDB | 向量存储与语义检索 |
| **Database** | SQLAlchemy (SQLite/MySQL) | 关系型数据与元数据管理 |
| **Frontend** | Vue 3, Element Plus | 响应式交互界面 |
| **Tools** | pypdf, LangChain (Concepts) | 文档解析与思维链构建 |

### ✨ 功能特性

* **🛌 昼夜节律 (Circadian Rhythm)**: 支持手动或定时触发 `Sleep` 进程，完成记忆的整理与固化。
* **📄 深度阅读 (Deep Reading)**: 支持全量 PDF 文献的 Token 级研读，构建高保真的记忆底座。
* **🔗 跨时空联想 (Cross-Project Association)**: 打破不同 Idea 之间的孤岛，实现知识迁移。
* **🛡️ 对抗性思考 (Adversarial Thinking)**: 系统会自动检索反例与局限性，模拟“批判性思维”过程。

---

## 🇺🇸 English Introduction

### 📖 Design Philosophy: Why "Engram"?

In neuroscience, an **Engram** refers to the physical trace of memory within the brain's neural network. Human memory is not merely a collection of static data but a dynamic process involving **Encoding**, **Consolidation**, and **Retrieval**.

Current LLM-based conversational systems are often constrained by the Context Window, facing the problem of "catastrophic forgetting"—they possess only fleeting "working memory." **Research Engram** aims to endow AI with a growing "hippocampus." By simulating the **Sleep-Dependent Memory Consolidation** mechanism, it transforms fragmented inspirations into long-term cognitive assets, addressing the issues of fragmented inspiration and memory loss in scientific research.

### 🧬 Biomimetic Architecture & Implementation

This project engineeringly replicates the three core processes of biological memory:

#### 1. Memory Encoding - *Working Memory*
Real-time dialogue streams are treated as transient signals. The system employs **Sentence Transformers** (`all-MiniLM-L6-v2`) to convert unstructured text into high-dimensional semantic vectors, supporting a dual-mode retrieval strategy:
* **Focus Mode**: Uses Metadata Filtering to retrieve context only within the current Project ID, ensuring rigor.
* **Associative Mode**: Retrieves similar vectors across different projects, simulating the brain's "divergent thinking" to trigger inspiration transfer.

#### 2. Memory Consolidation - *The Sleep Mechanism*
This is the core innovation. Just as humans transfer short-term memories from the hippocampus to the neocortex during sleep, the `Sleep` module acts as an asynchronous offline process (based on **Celery/AsyncIO**) responsible for:
* **Noise Cleaning**: Utilizing LLM to identify and discard low-entropy chitchat.
* **Implicit Knowledge Extraction**: Automatically extracting insights from conversations (e.g., "User prefers Transformer architecture") and storing them structurally in a **SQLAlchemy** relational database.
* **Plasticity**: Dynamically updating the User Persona based on extracted knowledge, achieving neural plasticity in AI cognition.

#### 3. Memory Retrieval - *Cue-Based Reactivation*
The system implements **Agentic Retrieval**. The Agent is no longer a passive answering machine but acts like a human recalling the past. By capturing "Retrieval Cues" in the current context, it uses **Function Calling** to autonomously decide whether to reactivate dormant historical memories (querying the **ChromaDB** vector store).

### 🛠️ Tech Stack

| Module | Technology | Purpose |
| :--- | :--- | :--- |
| **Backend** | Python, FastAPI | High-performance asynchronous API service |
| **LLM & Agent** | DeepSeek V3 API | Core inference engine & intent recognition |
| **Embedding** | **Sentence Transformers** | Local high-performance text vectorization |
| **Vector DB** | ChromaDB | Vector storage & semantic search |
| **Database** | SQLAlchemy (SQLite/MySQL) | Relational data & metadata management |
| **Frontend** | Vue 3, Element Plus | Responsive interactive interface |
| **Tools** | pypdf, LangChain (Concepts) | Document parsing & Chain-of-Thought |

### ✨ Features

* **🛌 Circadian Rhythm**: Supports manual or scheduled triggering of the `Sleep` process for memory organization and consolidation.
* **📄 Deep Reading**: Supports Token-level study of full PDF documents, building a high-fidelity memory foundation.
* **🔗 Cross-Project Association**: Breaks the silos between different ideas to achieve knowledge transfer.
* **🛡️ Adversarial Thinking**: The system automatically retrieves counterexamples and limitations, simulating a "critical thinking" process.

---

## 📄 License
MIT

---

## 🚀 快速开始 (Quick Start)

### 1. 环境准备 (Prerequisites)
- **Python**: 3.10+
- **Node.js**: 16+
- **API Key**: DeepSeek V3 API Key

### 2. 后端启动 (Backend Setup)

```bash
# 1. 进入后端目录
# Enter backend directory
cd backend

# 2. 创建并激活虚拟环境 (可选，但推荐)
# Create and activate virtual environment (Optional)
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 3. 安装依赖
# Install dependencies
pip install -r requirements.txt

# 4. 配置环境变量
# Configure environment variables
# (Copy .env.example to .env and fill in your API Key)
cp .env.example .env

# 5. 启动服务
# Start the server
uvicorn main:app --reload

# 1. 进入前端目录
# Enter frontend directory
cd ../frontend

# 2. 安装依赖
# Install dependencies
npm install

# 3. 启动开发服务器
# Start development server
npm run dev

```

---

## 📄 项目结构 (Project Structure)

```text
Research-Engram/
├── backend/                # 后端代码文件夹
│   ├── main.py             # 入口
│   ├── services.py         # 业务逻辑
│   ├── models.py           # 数据库模型
│   ├── schemas.py          # Pydantic模型
│   ├── crud.py             # 数据库操作
│   ├── sleep.py            # 睡眠机制
│   ├── vector_memory.py    # 向量库逻辑
│   └── requirements.txt    # 后端依赖列表
├── frontend/               # 前端代码文件夹 (把 Vue 项目放这里)
│   ├── src/
│   ├── package.json
│   └── vite.config.js
├── README.md               # 项目说明书
├── .gitignore              # 忽略文件
└── .env.example            # 配置示例
```
