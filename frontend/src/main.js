import { createApp } from 'vue'
import App from './App.vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css' // 引入样式文件

const app = createApp(App)

app.use(ElementPlus) // 安装组件库
app.mount('#app')
