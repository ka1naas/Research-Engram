# Research Engram - 科研灵感伴侣
Research Engram 是一个垂直于科研场景的 AI 助手，旨在解决文献阅读中的**灵感碎片化**与**记忆丢失**问题。它具备独特的“睡眠”机制，能够将短期对话转化为长期记忆，并支持跨项目的灵感联想。

**设计哲学：Why "Engram"?**

在神经科学中，Engram (记忆痕迹) 是指记忆在大脑神经元网络中留下的物理印记。人类的记忆并非数据的简单堆砌，而是一个动态的编码、巩固与再激活的过程。
现有的 LLM 对话系统往往受限于 Context Window，面临“灾难性遗忘”的问题——它们只有短暂的“工作记忆”。Research Engram 旨在赋予 AI 一个可生长的“海马体”，通过模拟人类的睡眠记忆固化 (Sleep-Dependent Memory Consolidation) 机制，将碎片化的灵感转化为长期的认知资产。

**核心仿生架构**

本项目通过代码实现了生物记忆的三大核心过程：
1. 记忆编码 (Encoding) - 工作记忆
用户与 AI 的实时对话流被视为瞬时信号。系统支持 "专注 (Focus)" 与 "联想 (Associative)" 双模态检索，模拟大脑在处理不同任务时对神经突触的不同激活策略，确保对话既能聚焦当下课题，又能跨项目触发灵感。

2. 记忆固化 (Consolidation) - The Sleep Mechanism
这是本项目的核心创新。如同人类在睡眠中将海马体的短期记忆转移至新皮层，Sleep 模块 作为一个离线异步进程，负责：
三大核心亮点：
噪声清洗：过滤掉无效的闲聊噪音。
隐式知识提取：自动提炼对话中产生的 Insight（如“用户倾向于使用 Transformer 架构”）。
画像重塑 (Plasticity)：根据提取的知识更新 User Persona，实现 AI 认知的神经可塑性。

3. 记忆检索 (Retrieval) - 基于线索的再激活
系统实现了 Agentic Retrieval（自主决策检索）。Agent 不再是被动的问答机器，而是像人类回忆往事一样，通过捕捉当前语境中的“检索线索 (Retrieval Cues)”，自主判断是否需要激活沉睡的历史记忆（Function Calling）。

**功能特性 (Features)**

昼夜节律 (Circadian Rhythm): 支持手动或定时触发 Sleep 进程，完成记忆的整理与固化。
深度阅读 (Deep Reading): 支持全量 PDF 文献的 Token 级研读，构建高保真的记忆底座。
跨时空联想 (Cross-Project Association): 打破不同 Idea 之间的孤岛，实现知识迁移。
对抗性思考 (Adversarial Thinking): 系统会自动检索反例与局限性，模拟“批判性思维”过程。