<template>
  <Layout>
    <div class="agent-page">
      <h1 class="page-title">Agent接入</h1>
      <p class="page-subtitle">把AI-Pulse接进你的工作流</p>
      
      <div class="filter-section">
        <h2 class="section-title">📡 REST API</h2>
        <a-card class="api-doc">
          <pre class="code-block">GET /api/v1/items?mode=selected&amp;limit=50</pre>
        </a-card>
        
        <a-divider />
        
        <h3 class="subsection-title">🧪 API 测试</h3>
        <a-form :model="testForm" layout="vertical">
          <a-row :gutter="16">
            <a-col :span="8">
              <a-form-item label="模式">
                <a-radio-group v-model="testForm.mode">
                  <a-radio value="selected">精选</a-radio>
                  <a-radio value="all">全部</a-radio>
                </a-radio-group>
              </a-form-item>
            </a-col>
            <a-col :span="8">
              <a-form-item label="返回数量">
                <a-input-number v-model="testForm.limit" :min="1" :max="100" />
              </a-form-item>
            </a-col>
            <a-col :span="8">
              <a-form-item label="关键词搜索（可选）">
                <a-input v-model="testForm.q" placeholder="如：OpenAI" />
              </a-form-item>
            </a-col>
          </a-row>
          <a-button type="primary" :loading="loading" @click="testApi">🚀 测试API</a-button>
        </a-form>
        
        <a-card v-if="testResult" class="result-card" style="margin-top: 16px;">
          <pre class="code-block">{{ testResult }}</pre>
        </a-card>
      </div>
      
      <div class="filter-section">
        <h2 class="section-title">📋 RSS 订阅</h2>
        <p class="desc">通过RSS订阅获取精选内容更新</p>
        <a-input :model-value="rssUrl" readonly>
          <template #append>
            <a-button @click="copyToClipboard(rssUrl)">复制</a-button>
          </template>
        </a-input>
      </div>
      
      <div class="filter-section">
        <h2 class="section-title">📖 SKILL.md 标准</h2>
        <p class="desc">通过SKILL.md标准接入其他Agent</p>
        <a-input :model-value="skillUrl" readonly>
          <template #append>
            <a-button @click="copyToClipboard(skillUrl)">复制</a-button>
          </template>
        </a-input>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Layout from '../components/Layout.vue'
import { Message } from '@arco-design/web-vue'

const testForm = ref({
  mode: 'selected',
  limit: 5,
  q: ''
})
const loading = ref(false)
const testResult = ref('')

const baseUrl = window.location.origin
const rssUrl = `${baseUrl}/api/v1/rss`
const skillUrl = `${baseUrl}/api/v1/skill.md`

async function testApi() {
  loading.value = true
  try {
    const params = new URLSearchParams({
      mode: testForm.value.mode,
      limit: testForm.value.limit
    })
    if (testForm.value.q) {
      params.append('q', testForm.value.q)
    }
    
    const response = await fetch(`/api/v1/list?${params}`)
    const data = await response.json()
    testResult.value = JSON.stringify(data, null, 2)
  } catch (err) {
    testResult.value = `Error: ${err.message}`
  } finally {
    loading.value = false
  }
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).then(() => {
    Message.success('已复制到剪贴板')
  }).catch(() => {
    Message.error('复制失败')
  })
}

onMounted(() => {
  // Initialize if needed
})
</script>

<style scoped>
.agent-page {
  max-width: 800px;
}

.page-title {
  font-size: 32px;
  font-weight: 700;
  margin: 0 0 8px;
}

.page-subtitle {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.5);
  margin: 0 0 24px;
}

.light .page-subtitle {
  color: rgba(0, 0, 0, 0.5);
}

.filter-section {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
}

.light .filter-section {
  background: rgba(248, 250, 252, 0.6);
  border: 1px solid rgba(0, 0, 0, 0.08);
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  margin: 0 0 12px;
}

.subsection-title {
  font-size: 16px;
  font-weight: 500;
  margin: 0 0 12px;
}

.desc {
  color: rgba(255, 255, 255, 0.6);
  margin: 0 0 12px;
  font-size: 14px;
}

.light .desc {
  color: rgba(0, 0, 0, 0.6);
}

.code-block {
  background: rgba(15, 23, 42, 0.8);
  padding: 12px;
  border-radius: 8px;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  overflow-x: auto;
  color: #e2e8f0;
}

.light .code-block {
  background: rgba(248, 250, 252, 0.8);
  color: #1e293b;
}

.result-card {
  margin-top: 16px;
}
</style>
