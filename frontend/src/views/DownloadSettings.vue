<template>
  <Layout>
    <div class="download-page">
      <div class="page-header">
        <h1 class="page-title">下载设置</h1>
        <p class="page-subtitle">管理下载路径和缓存清理</p>
      </div>

      <!-- 本地保存路径 -->
      <div class="section">
        <div class="section-card">
          <div class="section-title"> 本地保存路径</div>
          <div class="path-row">
            <a-input
              v-model="savePath"
              placeholder="例如：/home/user/My_Knowledge_Base/Inbox"
              size="large"
              :style="{ flex: 1 }"
            />
            <a-button type="primary" size="large" @click="saveConfig" :loading="saving">保存</a-button>
          </div>
          <div class="section-hint">输入本地文件夹的完整路径，打包下载时将保存到此目录。例如：~/My_Knowledge_Base/Inbox 或 C:\Downloads\AI-Pulse</div>
        </div>
      </div>

      <!-- L1缓存清理 -->
      <div class="section">
        <div class="section-card">
          <div class="section-title">🗑️ L1缓存清理设置</div>
          
          <div class="config-row">
            <span class="config-label">自动清理周期</span>
            <a-input-number
              v-model="l1RetentionDays"
              :min="1"
              :max="30"
              size="large"
              :style="{ width: '100px' }"
            />
            <span class="config-unit">天</span>
            <a-button size="large" class="ml-12" @click="saveConfig" :loading="saving">保存</a-button>
          </div>
          <div class="section-hint">系统每日凌晨2点自动清理超过设定天数的原始抓取数据</div>

          <div class="manual-actions">
            <a-button type="primary" size="large" @click="cleanExpired" :loading="cleaning">
              立即清理过期L1缓存
            </a-button>
            <a-button status="danger" size="large" @click="confirmCleanAll" :loading="cleaning">
              清空全部L1缓存
            </a-button>
          </div>
        </div>
      </div>

      <!-- 下载状态说明 -->
      <div class="section">
        <div class="section-card">
          <div class="section-title">ℹ️ 下载状态说明</div>
          <div class="info-box">
            系统自动标记已下载内容，避免重复下载。已下载内容在列表中显示
            <span class="dot-green"></span> 绿色圆点标识，未下载内容显示
            <span class="dot-gray"></span> 灰色圆点标识。
          </div>
        </div>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Layout from '../components/Layout.vue'
import { Message, Modal } from '@arco-design/web-vue'

const savePath = ref('~/My_Knowledge_Base/Inbox')
const l1RetentionDays = ref(7)
const saving = ref(false)
const cleaning = ref(false)

async function loadConfig() {
  try {
    const res = await fetch('/api/v1/download/config')
    const data = await res.json()
    if (data.code === 0) {
      savePath.value = data.data.save_path || '~/My_Knowledge_Base/Inbox'
      l1RetentionDays.value = data.data.l1_retention_days || 7
    }
  } catch (e) {
    console.error('Load config error:', e)
  }
}

async function saveConfig() {
  saving.value = true
  try {
    const res = await fetch('/api/v1/download/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        save_path: savePath.value,
        l1_retention_days: l1RetentionDays.value
      })
    })
    const data = await res.json()
    if (data.code === 0) {
      Message.success('保存成功')
    } else {
      Message.error(data.message || '保存失败')
    }
  } catch (e) {
    Message.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function cleanExpired() {
  cleaning.value = true
  try {
    const res = await fetch('/api/v1/cache/l1/clean', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ clean_all: false })
    })
    const data = await res.json()
    if (data.code === 0) {
      Message.success(`清理完成，共删除 ${data.data.clean_count} 条过期数据`)
    } else {
      Message.error(data.message || '清理失败')
    }
  } catch (e) {
    Message.error('清理失败')
  } finally {
    cleaning.value = false
  }
}

function confirmCleanAll() {
  Modal.confirm({
    title: '确认清空所有原始抓取数据？',
    content: '此操作不可恢复，所有L1缓存数据将被永久删除。',
    okText: '确认清空',
    cancelText: '取消',
    okButtonProps: { status: 'danger' },
    onOk: async () => {
      cleaning.value = true
      try {
        const res = await fetch('/api/v1/cache/l1/clean', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ clean_all: true })
        })
        const data = await res.json()
        if (data.code === 0) {
          Message.success(`已清空 ${data.data.clean_count} 条缓存数据`)
        } else {
          Message.error(data.message || '清空失败')
        }
      } catch (e) {
        Message.error('清空失败')
      } finally {
        cleaning.value = false
      }
    }
  })
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.download-page {
  max-width: 800px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}

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

.section {
  margin-bottom: 20px;
}

.section-card {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 20px 24px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
  margin-bottom: 16px;
}

.path-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ml-12 {
  margin-left: 12px;
}

.section-hint {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.3);
  margin-top: 10px;
}

.config-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.config-label {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.6);
}

.config-unit {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.4);
}

.manual-actions {
  margin-top: 16px;
  display: flex;
  gap: 12px;
}

.info-box {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.5);
  line-height: 1.8;
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}

.dot-green {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #10B981;
}

.dot-gray {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
}
</style>
