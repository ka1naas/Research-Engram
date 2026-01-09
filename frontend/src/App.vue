<template>
  <div class="common-layout">
    <el-container style="height: 100vh;">
      
      <el-aside width="220px" style="background-color: #2c3e50; display: flex; flex-direction: column; padding: 10px;">
        <div style="color: white; font-weight: bold; margin: 20px 0; text-align: center; font-size: 18px;">
            研究灵感库
        </div>
        
        <el-button type="primary" icon="Plus" style="width: 100%; margin-bottom: 20px;" @click="showCreateDialog = true">
          新建 Idea
        </el-button>

        <div style="flex: 1; overflow-y: auto;">

          <div 
            @click="switchToGeneralChat()"
            :style="{
              padding: '10px',
              marginBottom: '5px',
              borderRadius: '4px',
              cursor: 'pointer',
              color: 'white',
              backgroundColor: currentIdeaId === null ? '#67C23A' : 'transparent', /* 选中时变绿 */
              transition: 'all 0.3s',
              border: '1px dashed rgba(255,255,255,0.3)'
            }"
            class="idea-item"
          >
            <div style="font-weight: bold;"> 随便聊聊</div>
            <div style="font-size: 12px; opacity: 0.7;">不关联具体 Idea</div>
          </div>

          <div 
            v-for="idea in ideaList" 
            :key="idea.id"
            @click="switchIdea(idea)"
            :style="{
              padding: '10px',
              marginBottom: '5px',
              borderRadius: '4px',
              cursor: 'pointer',
              color: 'white',
              backgroundColor: currentIdeaId === idea.id ? '#409EFF' : 'transparent',
              transition: 'all 0.3s'
            }"
            class="idea-item"
          >
            <div style="font-weight: bold;">{{ idea.title }}</div>
            <div style="font-size: 12px; opacity: 0.7; overflow: hidden; white-space: nowrap; text-overflow: ellipsis;">
              {{ idea.description || '无描述' }}
            </div>
          </div>
        </div>

        <div style="margin-top: auto; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.1);">
           <el-button type="warning" plain style="width: 100%;" @click="triggerSleep" :loading="isSleeping">
              整理记忆 (Sleep)
           </el-button>
        </div>
      </el-aside>

      <el-container>
        <el-header style="border-bottom: 1px solid #eee; display: flex; align-items: center; justify-content: space-between; height: 60px;">
          <div style="display: flex; align-items: center;">
            <h3 style="margin:0; margin-right: 15px;">🧪 科研助手</h3>
            
            <el-tag v-if="currentIdeaId" type="success" style="margin-right: 10px;">
              Idea: {{ currentIdeaTitle }}
            </el-tag>
            
            <el-tag v-if="currentPaperId" type="danger" effect="dark" closable @close="clearPaperSelection">
              <span v-if="useFullText">📖 全文研读模式</span>
              <span v-else>💬 摘要+联想模式</span>
              : {{ currentPaperTitle }}
            </el-tag>
          </div>

          <div>
            <el-tag type="info">User: {{ userId }}</el-tag>
          </div>
        </el-header>

        <el-main style="display: flex; padding: 0;">
          
          <div style="flex: 6; display: flex; flex-direction: column; border-right: 1px solid #eee; height: 100%;">
            
            <div id="chat-box" style="flex: 1; overflow-y: auto; padding: 20px; background-color: #f9f9f9;">
              <div v-if="messages.length === 0" style="text-align: center; color: #ccc; margin-top: 50px;">
                <p>暂无对话。</p>
                <p v-if="!currentIdeaId">请先在左侧选择或新建一个 Idea</p>
              </div>

              <div v-for="(msg, index) in messages" :key="index" :style="{ textAlign: msg.role === 'user' ? 'right' : 'left', marginBottom: '15px' }">
                <div style="display: inline-block; max-width: 80%;">
                  <span style="font-size: 12px; color: #888; display: block; margin-bottom: 4px;">{{ msg.role === 'user' ? '我' : 'AI 助手' }}</span>
                  <div :style="{
                    background: msg.role === 'user' ? '#409EFF' : '#fff',
                    color: msg.role === 'user' ? '#fff' : '#333',
                    padding: '10px 15px',
                    borderRadius: '8px',
                    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                    textAlign: 'left',
                    whiteSpace: 'pre-wrap'
                  }">{{ msg.content }}</div>

                  <el-card v-if="msg.suggested_idea" style="margin-top: 10px; border-color: #67C23A; background-color: #f0f9eb;">
                    <template #header><div style="color: #67C23A; font-weight: bold;">💡 发现新灵感</div></template>
                    <p>{{ msg.suggested_idea }}</p>
                    <el-button type="success" size="small" style="margin-top:5px" @click="openUpdateDialog(msg.suggested_idea)">
                      采纳并修订
                    </el-button>
                  </el-card>
                </div>
              </div>

              <div v-if="isLoading" style="text-align: left; margin-bottom: 15px;">
                <span style="font-size: 12px; color: #888; display: block; margin-bottom: 4px;">AI 助手</span>
                <div style="background: #f4f4f5; color: #909399; padding: 10px 15px; border-radius: 8px; display: inline-flex; align-items: center;">
                  <el-icon class="is-loading" style="margin-right: 5px;"><Loading /></el-icon>
                  <span v-if="currentPaperId && useFullText">正在深度阅读全文...</span>
                  <span v-else-if="currentPaperId">正在分析摘要并联想...</span>
                  <span v-else>Agent 正在思考与检索...</span>
                </div>
              </div>
            </div>

            <div style="padding: 20px; background: white; border-top: 1px solid #eee;">
              <div style="margin-bottom: 10px; display: flex; align-items: center; flex-wrap: wrap; gap: 15px;">
                <el-radio-group v-model="chatMode" size="small">
                  <el-radio-button label="chat">对话</el-radio-button>
                  <el-radio-button label="update">改进</el-radio-button>
                  <el-radio-button label="critique">找茬</el-radio-button>
                </el-radio-group>
                
                <el-checkbox v-model="saveAsKnowledge">存为知识</el-checkbox>
                
                <el-switch
                  v-model="enableGlobalSearch"
                  inline-prompt
                  active-text="全局联想"
                  inactive-text="专注当前"
                />

                <div style="display: flex; align-items: center; width: 140px;">
                  <span style="font-size: 12px; color: #666; margin-right: 5px;">回溯:{{ historyLen }}</span>
                  <el-slider v-model="historyLen" :min="0" :max="10" size="small" />
                </div>
              </div>

              <div style="display: flex;">
                <el-input 
                  v-model="inputQuery" 
                  placeholder="输入你的想法... (未选 Idea 时为自由模式)" 
                  @keyup.enter="sendMessage" 
                />
                <el-button type="primary" style="margin-left: 10px;" @click="sendMessage" :loading="isLoading" :disabled="!currentIdeaId">发送</el-button>
              </div>
            </div>
          </div>

          <div style="flex: 4; padding: 20px; background-color: #fff; display: flex; flex-direction: column;">
            
            <div style="margin-bottom: 20px;">
                <h4 style="margin-top:0">📄 论文库 (Idea ID: {{ currentIdeaId || '-' }})</h4>
                <el-upload
                  class="upload-demo"
                  drag
                  action="http://127.0.0.1:8000/upload_paper/"
                  :data="{ user_id: userId, idea_id: currentIdeaId }"
                  multiple
                  :on-success="handleUploadSuccess"
                  :on-error="handleUploadError"
                  :disabled="!currentIdeaId"
                  :show-file-list="false" 
                >
                  <el-icon style="font-size: 30px; color: #ccc;"><upload-filled /></el-icon>
                  <div class="el-upload__text" style="font-size: 12px;">拖拽上传 PDF</div>
                </el-upload>
            </div>

            <div style="flex: 1; overflow-y: auto; border-top: 1px solid #eee; padding-top: 10px;">
                <div v-if="paperList.length === 0" style="color: #999; text-align: center; font-size: 13px; margin-top: 20px;">
                    暂无论文，请上传
                </div>

                <div v-for="paper in paperList" :key="paper.id" style="margin-bottom: 15px; border: 1px solid #eee; padding: 10px; borderRadius: 4px;">
                    <div style="font-weight: bold; font-size: 14px; margin-bottom: 5px; word-break: break-all;">
                        {{ paper.title }}
                    </div>
                    
                    <div style="display: flex; gap: 10px;">
                        <el-button 
                            type="danger" 
                            size="small" 
                            plain 
                            @click="selectPaper(paper, true)"
                            :disabled="currentPaperId === paper.id && useFullText"
                        >
                           <el-icon><View /></el-icon> 读全文
                        </el-button>

                        <el-button 
                            type="primary" 
                            size="small" 
                            plain 
                            @click="selectPaper(paper, false)"
                            :disabled="currentPaperId === paper.id && !useFullText"
                        >
                           <el-icon><ChatLineSquare /></el-icon> 聊摘要
                        </el-button>
                    </div>
                </div>
            </div>

          </div>
        </el-main>
      </el-container>
    </el-container>

    <el-dialog v-model="showCreateDialog" title="新建研究灵感" width="30%">
      <el-form :model="newIdeaForm">
        <el-form-item label="标题">
          <el-input v-model="newIdeaForm.title" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="newIdeaForm.description" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="createIdea">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showUpdateDialog" title="确认更新 Idea" width="40%">
      <el-form>
        <div style="margin-bottom: 10px; color: #666;">AI 建议的内容：</div>
        <el-form-item>
          <el-input v-model="pendingIdeaContent" type="textarea" :rows="6" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUpdateDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmUpdateIdea">确认更新</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import axios from 'axios'
import { UploadFilled, Plus, Loading, View, ChatLineSquare } from '@element-plus/icons-vue'

// --- 状态变量 ---
const userId = ref(1)
const currentIdeaId = ref(null)
const currentIdeaTitle = ref('')
const ideaList = ref([])

// 🟢 论文控制状态
const paperList = ref([])         // 当前 Idea 下的论文列表
const currentPaperId = ref(null)  // 当前锁定的论文 ID (null 代表 Agent 模式)
const currentPaperTitle = ref('') 
const useFullText = ref(false)    // true=全文, false=摘要

// 聊天控制
const inputQuery = ref('')
const isLoading = ref(false)
const isSleeping = ref(false)
const messages = ref([])
const chatMode = ref('chat')
const saveAsKnowledge = ref(false)
const enableGlobalSearch = ref(false)
const historyLen = ref(5)

// 弹窗状态
const showCreateDialog = ref(false)
const showUpdateDialog = ref(false)
const pendingIdeaContent = ref('')
const newIdeaForm = reactive({ title: '', description: '' })

// --- 初始化 ---
const loadIdeas = async () => {
  try {
    const res = await axios.get(`http://127.0.0.1:8000/users/${userId.value}/ideas/`)
    ideaList.value = res.data
    
    // 如果没有 Idea，或者用户刚进来，默认进入自由模式
    if (!currentIdeaId.value) {
      switchToGeneralChat()
    }
  } catch (err) { console.error(err) }
}

// --- 切换 Idea ---
const switchIdea = async (idea) => {
  currentIdeaId.value = idea.id
  currentIdeaTitle.value = idea.title
  
  // 重置论文选择
  clearPaperSelection()
  
  // 1. 加载聊天记录
  messages.value = []
  try {
    const res = await axios.get(`http://127.0.0.1:8000/ideas/${idea.id}/messages/`)
    messages.value = res.data.map(m => ({
        role: m.role || (m.response_text ? 'ai' : 'user'),
        content: m.content || m.query || m.response_text
    }))
  } catch (err) { console.error(err) }

  // 2. 加载该 Idea 的论文列表 (需要后端支持 GET /papers?idea_id=...)
  // 这里假设你还没写这个接口，我先用假数据或者空的
  // ⚠️ 记得去 main.py 加一个获取论文列表的接口: 
  // @app.get("/ideas/{idea_id}/papers/")
  loadPapers(idea.id)
}

// --- 加载论文列表 ---
const loadPapers = async (ideaId) => {
  try {
    // 假设后端有这个接口
    const res = await axios.get(`http://127.0.0.1:8000/ideas/${ideaId}/papers/`)
    paperList.value = res.data
  } catch (err) {
    console.warn("加载论文列表失败(可能是后端接口没写):", err)
    paperList.value = [] 
  }
}

// --- 🟢 核心：选择/锁定论文 ---
const selectPaper = (paper, fullTextMode) => {
  currentPaperId.value = paper.id
  currentPaperTitle.value = paper.title
  useFullText.value = fullTextMode
  
  // 可以在聊天框里提示一下用户
  const modeText = fullTextMode ? "深度阅读全文" : "摘要+联想"
  messages.value.push({
    role: 'ai',
    content: `🔍 已锁定论文：《${paper.title}》。\n当前模式：**${modeText}**。\n请问你想了解什么？`
  })
}

// --- 取消锁定 ---
const clearPaperSelection = () => {
  if (currentPaperId.value) {
    // 只有当之前有选中时，才提示切换回 Agent
    messages.value.push({
        role: 'ai',
        content: `🤖 已退出论文锁定模式。切换回 **Agent 自由决策模式**。`
    })
  }
  currentPaperId.value = null
  currentPaperTitle.value = ''
  useFullText.value = false
}

// --- 发送消息 ---
const sendMessage = async () => {
  if (!inputQuery.value.trim()) return

  const userText = inputQuery.value
  messages.value.push({ role: 'user', content: userText })
  inputQuery.value = ''
  isLoading.value = true

  try {
    const response = await axios.post('http://127.0.0.1:8000/chat/', {
      user_id: userId.value,
      query: userText,
      idea_id: currentIdeaId.value,
      
      // 关键参数传给后端
      paper_id: currentPaperId.value, 
      use_full_text: useFullText.value,
      
      mode: chatMode.value,
      history_len: historyLen.value,
      save_as_knowledge: saveAsKnowledge.value,
      enable_global_search: enableGlobalSearch.value
    })
    
    messages.value.push({
      role: 'ai',
      content: response.data.response_text,
      suggested_idea: response.data.suggested_idea
    })

  } catch (error) {
    messages.value.push({ role: 'ai', content: '请求失败：' + error.message })
  } finally {
    isLoading.value = false
  }
}

// --- 杂项功能 ---
const createIdea = async () => {
  if(!newIdeaForm.title) return alert("标题不能为空")
  try {
    const res = await axios.post('http://127.0.0.1:8000/ideas/', {
      title: newIdeaForm.title, description: newIdeaForm.description
    }, { params: { user_id: userId.value } })
    showCreateDialog.value = false
    loadIdeas()
  } catch (err) { alert("创建失败") }
}

const openUpdateDialog = (content) => {
  pendingIdeaContent.value = content
  showUpdateDialog.value = true
}

const confirmUpdateIdea = async () => {
  try {
    await axios.put(`http://127.0.0.1:8000/ideas/${currentIdeaId.value}`, {
      description: pendingIdeaContent.value
    })
    alert(" Idea 更新成功！")
    showUpdateDialog.value = false
    loadIdeas()
  } catch(e) { console.error(e); alert("更新失败") }
}

const triggerSleep = async () => {
  isSleeping.value = true
  try {
    const formData = new FormData()
    formData.append('user_id', userId.value)
    const res = await axios.post('http://127.0.0.1:8000/system/sleep/', formData)
    alert(" 整理完成！\n" + res.data.message)
  } catch (err) { alert("失败：" + err.message) }
  finally { isSleeping.value = false }
}

const handleUploadSuccess = () => {
  alert("上传成功！")
  loadPapers(currentIdeaId.value) // 刷新论文列表
}
const handleUploadError = (err) => console.error(err)

// “随便聊聊”模式
const switchToGeneralChat = () => {
  currentIdeaId.value = null // 设置为 null
  currentIdeaTitle.value = '自由对话模式'
  
  // 清空论文锁定
  clearPaperSelection()
  paperList.value = [] // 自由模式下暂无关联论文
  
  // 清空聊天记录 (或者你可以选择不清空，看需求)
  messages.value = [] 
  messages.value.push({ role: 'ai', content: ' 你好！现在是自由对话模式，我们可以随便聊聊，或者讨论新的研究方向。' })
}
</script>

<style>
body { margin: 0; font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', Arial, sans-serif; }
.idea-item:hover { background-color: rgba(255,255,255,0.1) !important; }
</style>