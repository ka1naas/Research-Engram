<template>
  <div class="common-layout">
    <el-container style="height: 100vh;">
      
      <el-aside width="60px" style="background-color: #2c3e50; display: flex; flex-direction: column; align-items: center; padding-top: 20px;">
        <div style="color: white; font-weight: bold; margin-bottom: 20px;">R-E</div>
        <el-button circle size="small">➕</el-button>
      </el-aside>

      <el-container>
        <el-header style="border-bottom: 1px solid #eee; display: flex; align-items: center; justify-content: space-between;">
          <h3 style="margin:0;">🧪 科研助手工作台 (Linux版)</h3>
          <div>
            <el-tag type="success">Idea ID: {{ currentIdeaId }}</el-tag>
            <el-tag style="margin-left: 10px">User: {{ userId }}</el-tag>
          </div>
        </el-header>

        <el-main style="display: flex; padding: 0;">
          
          <div style="flex: 6; display: flex; flex-direction: column; border-right: 1px solid #eee; height: 100%;">
            
            <div style="flex: 1; overflow-y: auto; padding: 20px; background-color: #f9f9f9;">
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
                  }">
                    {{ msg.content }}
                  </div>

                  <el-card v-if="msg.suggested_idea" style="margin-top: 10px; border-color: #67C23A; background-color: #f0f9eb;">
                    <template #header>
                      <div style="color: #67C23A; font-weight: bold;">💡 发现新灵感</div>
                    </template>
                    <p>{{ msg.suggested_idea }}</p>
                    <el-button type="success" size="small" plain @click="adoptIdea(msg.suggested_idea)">采纳更新 (TODO)</el-button>
                  </el-card>
                </div>
              </div>
            </div>

            <div style="padding: 20px; background: white; border-top: 1px solid #eee;">
              <div style="margin-bottom: 10px;">
                <el-radio-group v-model="chatMode" size="small">
                  <el-radio-button label="chat">闲聊模式</el-radio-button>
                  <el-radio-button label="update">改进 Idea</el-radio-button>
                  <el-radio-button label="critique">找茬/批评</el-radio-button>
                </el-radio-group>
                <el-checkbox v-model="saveAsKnowledge" style="margin-left: 15px;">存为知识</el-checkbox>
              </div>
              <div style="display: flex;">
                <el-input v-model="inputQuery" placeholder="输入你的想法... (例如: 帮我把Idea改成基于GAN的)" @keyup.enter="sendMessage" />
                <el-button type="primary" style="margin-left: 10px;" @click="sendMessage" :loading="isLoading">发送</el-button>
              </div>
            </div>
          </div>

          <div style="flex: 4; padding: 20px; background-color: #fff;">
            <h4>📄 关联论文库</h4>
            <el-upload
              class="upload-demo"
              drag
              action="http://127.0.0.1:8000/upload_paper/"
              :data="{ user_id: userId, idea_id: currentIdeaId }"
              multiple
              :on-success="handleUploadSuccess"
              :on-error="handleUploadError"
            >
              <el-icon style="font-size: 50px; color: #ccc;"><upload-filled /></el-icon>
              <div class="el-upload__text">
                拖拽 PDF 到此处或 <em>点击上传</em>
              </div>
            </el-upload>

            <div style="margin-top: 20px;">
              <el-timeline>
                <el-timeline-item v-for="(paper, index) in papers" :key="index" :timestamp="paper.time" placement="top">
                  <el-card>
                    <h4>{{ paper.title }}</h4>
                    <p>{{ paper.status }}</p>
                  </el-card>
                </el-timeline-item>
              </el-timeline>
            </div>
          </div>

        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'
import { UploadFilled } from '@element-plus/icons-vue' // 引入图标

// --- 数据状态 ---
const userId = ref(1) // 假设当前用户ID是1
const currentIdeaId = ref(1) // 假设当前讨论 Idea ID=1
const inputQuery = ref('')
const isLoading = ref(false)
const messages = ref([
  { role: 'ai', content: '你好！我是你的科研助手。已连接到 Linux 后端。' }
])
const chatMode = ref('chat') // 默认模式
const saveAsKnowledge = ref(false)

// 假装的论文列表
const papers = ref([])

// --- 核心功能：发送消息 ---
const sendMessage = async () => {
  if (!inputQuery.value.trim()) return

  // 1.先把用户的话显示出来
  const userText = inputQuery.value
  messages.value.push({ role: 'user', content: userText })
  inputQuery.value = ''
  isLoading.value = true

  try {
    // 2. 调用后端 API
    // 注意：如果在Linux里运行，127.0.0.1通常能正常映射，如果连不上尝试换成 localhost
    const response = await axios.post('http://127.0.0.1:8000/chat/', {
      user_id: userId.value,
      query: userText,
      idea_id: currentIdeaId.value,
      mode: chatMode.value,        // 传模式：chat / update / critique
      history_len: 5,              // 带5条历史
      save_as_knowledge: saveAsKnowledge.value // 是否存知识
    })

    const data = response.data
    
    // 3. 把 AI 的回复显示出来
    messages.value.push({
      role: 'ai',
      content: data.response_text,
      suggested_idea: data.suggested_idea // 如果后端返回了新 Idea，这里会接收到
    })

  } catch (error) {
    console.error(error)
    messages.value.push({ role: 'ai', content: '❌ 连接后端失败：' + error.message })
  } finally {
    isLoading.value = false
  }
}

// 仅仅是打个 Log，还没写真正的更新逻辑
const adoptIdea = (newIdea) => {
  alert("前端收到了新 Idea，下一步可以调用 API 更新数据库！\n\n" + newIdea)
}

// 上传成功回调
const handleUploadSuccess = (response, file) => {
  console.log("上传结果:", response)
  papers.value.push({
    title: file.name,
    time: '刚刚',
    status: '✅ 已存入向量库'
  })
}

const handleUploadError = (err) => {
  console.error(err)
  alert("上传失败，请检查后端报错")
}
</script>

<style>
/* 消除默认边距 */
body { margin: 0; font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', Arial, sans-serif; }
</style>
