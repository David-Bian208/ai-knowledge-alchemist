<template>
  <Layout>
    <div class="url-page">
      <div class="page-header">
        <h1 class="page-title">URL处理</h1>
        <p class="page-subtitle">输入网页URL自动分析评分入库</p>
      </div>
      
      <div class="process-card">
        <a-form :model="form" layout="vertical">
          <a-form-item label="网页URL">
            <a-textarea 
              v-model="form.url" 
              placeholder="https://mp.weixin.qq.com/s/xxxxx 或 https://example.com/article" 
              :auto-size="{ minRows: 3, maxRows: 6 }"
            />
          </a-form-item>
          
          <a-form-item label="信源等级">
            <a-radio-group v-model="form.tier" type="button">
              <a-radio value="T1">T1 核心</a-radio>
              <a-radio value="T1.5">T1.5 优质</a-radio>
              <a-radio value="T2">T2 一般</a-radio>
            </a-radio-group>
          </a-form-item>
          
          <a-button 
            type="primary" 
            size="large" 
            class="process-btn"
            :loading="processing"
            @click="processUrl"
          >
            🚀 处理并入库
          </a-button>
        </a-form>
      </div>
      
      <div v-if="result" class="result-card" :class="result.type">
        <div class="result-header">
          <span class="result-icon">{{ result.type === 'success' ? '✅' : result.type === 'warning' ? '⚠️' : '❌' }}</span>
          <h3>{{ result.title }}</h3>
        </div>
        <div v-if="result.score !== null" class="result-score">
          <span class="score-value" :style="{ color: getScoreColor(result.score) }">{{ result.score }}</span>
          <span class="score-label">综合评分</span>
        </div>
        <p v-if="result.message" class="result-message">{{ result.message }}</p>
      </div>
      
      <div class="info-card">
        <h3>💡 使用说明</h3>
        <ul>
          <li>支持微信公众号、知乎、36氪、IT之家等常见网页</li>
          <li>系统会自动提取标题、摘要、发布时间等信息</li>
          <li>AI会对内容进行评分，高分内容将进入精选时间线</li>
        </ul>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref } from 'vue'
import Layout from '../components/Layout.vue'
import { Message } from '@arco-design/web-vue'

const form = ref({ url: '', tier: 'T2' })
const processing = ref(false)
const result = ref(null)

function getScoreColor(score) {
  if (score >= 110) return '#EF4444'
  if (score >= 100) return '#F59E0B'
  if (score >= 90) return '#3B82F6'
  if (score >= 80) return '#10B981'
  return '#9CA3AF'
}

async function processUrl() {
  if (!form.value.url || !form.value.url.startsWith('http')) {
    Message.error('请输入有效的URL')
    return
  }
  
  processing.value = true
  result.value = null
  
  try {
    // 调用后端API - 这里假设后端有一个处理URL的端点
    // 实际需要根据后端实现调整
    const response = await fetch('/api/v1/process-url', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: form.value.url, tier: form.value.tier })
    })
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }
    
    const data = await response.json()
    
    if (data.selected) {
      result.value = {
        type: 'success',
        title: '已入选精选！',
        score: data.final_score || 0,
        message: `标题：${data.title || '无'}\n来源：${data.source || '未知'}`
      }
    } else {
      result.value = {
        type: 'warning',
        title: '未入选精选',
        score: data.final_score || 0,
        message: '得分未达到精选阈值，已入库但不展示在精选时间线'
      }
    }
  } catch (err) {
    result.value = {
      type: 'error',
      title: '处理失败',
      score: null,
      message: err.message
    }
  } finally {
    processing.value = false
  }
}
</script>

<style scoped>
.url-page { max-width: 700px; }

.page-header { margin-bottom: 24px; }

.page-title {
  font-size: 32px;
  font-weight: 700;
  margin: 0 0 4px;
  background: linear-gradient(135deg, #60a5fa, #8b5cf6);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.page-subtitle {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.4);
  margin: 0;
}

.light .page-subtitle { color: rgba(0, 0, 0, 0.4); }

.process-card {
  background: rgba(30, 41, 59, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
}

.light .process-card {
  background: rgba(248, 250, 252, 0.6);
  border: 1px solid rgba(0, 0, 0, 0.08);
}

.process-btn { width: 100%; margin-top: 12px; }

.result-card {
  border-radius: 16px;
  padding: 20px 24px;
  margin-bottom: 24px;
}

.result-card.success {
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.3);
}

.result-card.warning {
  background: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.result-card.error {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.result-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.result-icon { font-size: 20px; }

.result-header h3 {
  font-size: 18px;
  font-weight: 600;
  margin: 0;
}

.result-score {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.score-value { font-size: 24px; font-weight: 700; }
.score-label { font-size: 13px; color: rgba(255, 255, 255, 0.5); }
.light .score-label { color: rgba(0, 0, 0, 0.5); }

.result-message {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.7);
  margin: 0;
  white-space: pre-wrap;
  line-height: 1.6;
}

.light .result-message { color: rgba(0, 0, 0, 0.7); }

.info-card {
  background: rgba(30, 41, 59, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 20px;
}

.light .info-card {
  background: rgba(248, 250, 252, 0.4);
  border: 1px solid rgba(0, 0, 0, 0.06);
}

.info-card h3 {
  font-size: 15px;
  font-weight: 600;
  margin: 0 0 12px;
}

.info-card ul {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
  line-height: 1.8;
}

.light .info-card ul { color: rgba(0, 0, 0, 0.6); }
</style>
