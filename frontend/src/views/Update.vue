<template>
  <Layout>
    <div class="update-page">
      <div class="page-header">
        <h1 class="page-title">内容更新</h1>
        <p class="page-subtitle">管理数据同步和自动抓取</p>
      </div>

      <!-- 操作区域 -->
      <div class="action-section">
        <div class="action-card">
          <div class="action-icon">⚡</div>
          <div class="action-content">
            <div class="action-title">立即更新</div>
            <div class="action-desc">全量抓取所有信息源</div>
          </div>
          <div class="action-buttons">
            <a-button 
              type="primary" 
              size="large"
              :loading="fetchRunning"
              :disabled="fetchRunning"
              @click="startFetch"
            >
              {{ fetchRunning ? '更新中...' : '立即更新' }}
            </a-button>
            <a-button 
              v-if="fetchRunning"
              type="outline" 
              status="danger"
              size="large"
              :loading="fetchAborting"
              @click="abortFetch"
              class="abort-btn"
            >
              {{ fetchAborting ? '中止中...' : '中止' }}
            </a-button>
          </div>
        </div>
      </div>

      <!-- 更新配置 -->
      <div class="config-section">
        <div class="config-card">
          <div class="config-title">⚙️ 自动更新设置</div>

          <!-- 更新设置：间隔和定时并排 -->
          <div class="update-grid">
            <!-- 间隔更新配置 -->
            <div class="config-block">
              <div class="config-row" style="margin-bottom: 12px;">
                <span class="config-label" style="font-weight: 600; font-size: 15px;">⏱️ 间隔更新</span>
                <div class="switch-container" @click="intervalEnabled = !intervalEnabled" :class="{ 'switch-on': intervalEnabled }">
                  <span class="custom-switch">
                    <span class="switch-dot"></span>
                  </span>
                </div>
              </div>
              <div class="config-row">
                <span class="config-label">更新间隔</span>
                <a-input-number 
                  v-model="syncIntervalValue" 
                  :min="1" 
                  :max="maxIntervalValue"
                  size="large"
                  :style="{ width: '100px' }"
                  placeholder="1"
                  :disabled="!intervalEnabled"
                />
                <a-radio-group v-model="syncUnit" type="button" size="large" @change="onUnitChange" :disabled="!intervalEnabled">
                  <a-radio value="minutes">分钟</a-radio>
                  <a-radio value="hours">小时</a-radio>
                </a-radio-group>
              </div>
              <div class="config-hint">设置范围：1 ~ 24 小时（当前：{{ displayCurrentInterval }}）</div>
            </div>

            <!-- 定时更新配置 -->
            <div class="config-block">
              <div class="config-row" style="margin-bottom: 12px;">
                <span class="config-label" style="font-weight: 600; font-size: 15px;"> 定时更新</span>
                <div class="switch-container" @click="scheduledEnabled = !scheduledEnabled" :class="{ 'switch-on': scheduledEnabled }">
                  <span class="custom-switch">
                    <span class="switch-dot"></span>
                  </span>
                </div>
              </div>
              <div class="config-row">
                <span class="config-label">更新时间</span>
                <a-time-picker
                  v-model="scheduledTimeValue"
                  format="HH:mm"
                  size="large"
                  :style="{ width: '120px' }"
                  :disabled="!scheduledEnabled"
                />
                <span class="config-unit">（北京时间）</span>
              </div>
              <div class="config-hint">每天在指定时间自动执行更新</div>
            </div>
          </div>

          <!-- 分隔线 -->
          <div class="divider"></div>

          <!-- 更新后自动生成日报 -->
          <div class="config-row" style="margin-top: 16px; padding-top: 16px; border-top: 1px solid rgba(255,255,255,0.06);">
            <span class="config-label">生成日报</span>
            <div class="switch-container" @click="autoGenerateReport = !autoGenerateReport" :class="{ 'switch-on': autoGenerateReport }">
              <span class="custom-switch">
                <span class="switch-dot"></span>
              </span>
            </div>
            <span class="config-label ml-12" style="color: rgba(255,255,255,0.5); font-size: 13px;">每次更新后自动生成当日日报，如已有则覆盖</span>
          </div>

          <div style="margin-top: 16px;">
            <a-button type="primary" size="large" @click="saveAutoConfig" :loading="savingConfig">
              保存设置
            </a-button>
          </div>
        </div>
      </div>

      <!-- 上次更新结果 -->
      <div class="result-section" v-if="lastResult">
        <div class="result-card">
          <div class="result-title">📊 上次更新结果</div>
          
          <!-- 被中止提示 -->
          <div class="aborted-banner" v-if="lastResult.abort_message">
            <span class="aborted-icon">⚠️</span>
            <span class="aborted-text">{{ lastResult.abort_message }}</span>
          </div>

          <div class="result-grid">
            <div class="result-item">
              <div class="result-label">总耗时</div>
              <div class="result-value">{{ formatDuration(lastResult.started_at, lastResult.completed_at) }}</div>
            </div>
            <div class="result-item">
              <div class="result-label">信源总数</div>
              <div class="result-value">{{ lastResult.total_sources || 0 }} 个</div>
            </div>
            <div class="result-item">
              <div class="result-label">AI HOT 新增</div>
              <div class="result-value" :class="{ success: lastResult.aihot_result?.saved > 0 }">{{ lastResult.aihot_result?.saved || 0 }} 条</div>
            </div>
            <div class="result-item">
              <div class="result-label">信源抓取</div>
              <div class="result-value">{{ lastResult.crawler_result?.fetched || 0 }} 条</div>
            </div>
            <div class="result-item">
              <div class="result-label">信源新增</div>
              <div class="result-value" :class="{ success: lastResult.crawler_result?.saved > 0 }">{{ lastResult.crawler_result?.saved || 0 }} 条</div>
            </div>
          </div>
          <div class="result-summary">
            共新增 <span class="highlight">{{ lastResult.total_saved || 0 }}</span> 条内容
            （{{ formatTime(lastResult.completed_at) }}）
          </div>

          <!-- 失败信源详情 -->
          <div class="failed-sources" v-if="lastResult.failed_sources && lastResult.failed_sources.length > 0">
            <div class="failed-title">⚠️ 失败/被限制的信源（{{ lastResult.failed_sources.length }} 个）</div>
            <div class="failed-list">
              <div 
                v-for="(fs, idx) in lastResult.failed_sources" 
                :key="idx" 
                class="failed-item"
                :class="{ 'blocked': fs.is_blocked }"
              >
                <span class="failed-icon">{{ fs.is_blocked ? '🚫' : '❌' }}</span>
                <span class="failed-name">{{ fs.name }}</span>
                <span class="failed-type">{{ fs.type }}</span>
                <span class="failed-error">{{ fs.error }}</span>
              </div>
            </div>
          </div>

          <!-- 信源详细列表 -->
          <div class="source-details-toggle" v-if="lastResult.source_details && lastResult.source_details.length > 0">
            <a-button type="text" size="small" @click="showSourceDetails = !showSourceDetails">
              {{ showSourceDetails ? '隐藏' : '查看' }}所有信源详情（{{ lastResult.source_details.length }} 个）
              <icon-up v-if="showSourceDetails" />
              <icon-down v-else />
            </a-button>
          </div>
          <div class="source-details-list" v-if="showSourceDetails && lastResult.source_details">
            <div 
              v-for="(sd, idx) in lastResult.source_details" 
              :key="idx" 
              class="source-detail-item"
              :class="{ 'detail-failed': sd.status === 'failed' }"
            >
              <span class="detail-status">{{ sd.status === 'success' ? '✅' : '❌' }}</span>
              <span class="detail-name">{{ sd.name }}</span>
              <span class="detail-tier">{{ sd.tier }}</span>
              <span class="detail-count">抓取 {{ sd.fetched }} 条</span>
              <span class="detail-saved" v-if="sd.saved > 0">新增 {{ sd.saved }} 条</span>
              <span class="detail-error" v-if="sd.error">{{ sd.error.slice(0, 80) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 实时进度流 -->
      <div class="stream-section">
        <div class="stream-header">
          <div class="stream-title">📡 实时进度</div>
          <a-button v-if="streamLogs.length > 0" size="small" @click="clearLogs">清空</a-button>
        </div>
        <div class="stream-container">
          <div v-if="streamLogs.length === 0" class="stream-empty">
            点击"立即更新"开始抓取，这里会实时显示进度...
          </div>
          <div v-else class="stream-logs" ref="logsRef">
            <div 
              v-for="(log, idx) in streamLogs" 
              :key="idx" 
              class="stream-log"
              :class="{ 'log-info': log.type === 'info', 'log-error': log.type === 'error', 'log-success': log.type === 'success', 'log-abort': log.type === 'abort' }"
            >
              <span class="log-time">{{ log.time }}</span>
              <span class="log-text">{{ log.text }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import Layout from '../components/Layout.vue'
import { Message } from '@arco-design/web-vue'
import { IconLoading, IconUp, IconDown } from '@arco-design/web-vue/es/icon'

const fetchRunning = ref(false)
const fetchAborting = ref(false)
const intervalEnabled = ref(false)
const scheduledEnabled = ref(true)
const syncIntervalValue = ref(1)
const syncUnit = ref('hours')
const currentIntervalMinutes = ref(60)
const scheduledTimeValue = ref('08:00')
const autoGenerateReport = ref(true)
const savingConfig = ref(false)
const lastResult = ref(null)
const streamLogs = ref([])
const logsRef = ref(null)
const showSourceDetails = ref(false)

const maxIntervalValue = computed(() => syncUnit.value === 'hours' ? 24 : 1440)

const displayCurrentInterval = computed(() => {
  if (!currentIntervalMinutes.value) return '-'
  if (currentIntervalMinutes.value >= 60) {
    const hours = Math.floor(currentIntervalMinutes.value / 60)
    const mins = currentIntervalMinutes.value % 60
    return mins > 0 ? `${hours}小时${mins}分钟` : `${hours}小时`
  }
  return `${currentIntervalMinutes.value}分钟`
})

function formatTime(isoStr) {
  if (!isoStr) return ''
  try {
    const d = new Date(isoStr)
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch { return isoStr }
}

function formatDuration(start, end) {
  if (!start || !end) return '-'
  try {
    const ms = new Date(end) - new Date(start)
    const s = Math.floor(ms / 1000)
    if (s < 60) return `${s}秒`
    const m = Math.floor(s / 60)
    const sec = s % 60
    return `${m}分${sec}秒`
  } catch { return '-' }
}

function addLog(text, type = 'info') {
  const now = new Date()
  streamLogs.value.push({
    time: now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
    text,
    type
  })
  nextTick(() => {
    if (logsRef.value) {
      logsRef.value.scrollTop = logsRef.value.scrollHeight
    }
  })
}

function clearLogs() {
  streamLogs.value = []
}

async function startFetch() {
  fetchRunning.value = true
  fetchAborting.value = false
  streamLogs.value = []
  showSourceDetails.value = false
  
  addLog('正在启动全量刷新任务...', 'info')
  
  try {
    const res = await fetch('/api/v1/fetch', { method: 'POST' })
    const data = await res.json()
    
    if (data.status === 'started') {
      addLog('刷新任务已启动，开始执行...', 'success')
      startPolling()
    } else if (data.status === 'running') {
      addLog('刷新任务已在运行中', 'error')
      fetchRunning.value = false
    }
  } catch (e) {
    addLog(`启动失败：${e.message}`, 'error')
    fetchRunning.value = false
  }
}

async function abortFetch() {
  fetchAborting.value = true
  addLog('正在请求中止刷新任务...', 'abort')
  
  try {
    const res = await fetch('/api/v1/fetch/abort', { method: 'POST' })
    const data = await res.json()
    addLog(data.message, data.status === 'aborting' ? 'success' : 'error')
  } catch (e) {
    addLog(`中止请求失败：${e.message}`, 'error')
  } finally {
    fetchAborting.value = false
  }
}

let pollTimer = null
async function startPolling() {
  if (pollTimer) clearInterval(pollTimer)
  
  pollTimer = setInterval(async () => {
    try {
      const res = await fetch('/api/v1/fetch/status')
      const data = await res.json()
      
      if (!data.running) {
        clearInterval(pollTimer)
        pollTimer = null
        fetchRunning.value = false
        fetchAborting.value = false
        
        if (data.total_saved !== undefined) {
          if (data.total_saved > 0) {
            addLog(`刷新完成！共新增 ${data.total_saved} 条内容`, 'success')
          } else {
            addLog('刷新完成，没有新增内容', 'info')
          }
        }
        
        // 构建完整结果
        lastResult.value = {
          started_at: data.started_at,
          completed_at: data.completed_at,
          total_saved: data.total_saved || 0,
          total_sources: data.total_sources || 0,
          aihot_result: data.aihot_result,
          crawler_result: data.crawler_result,
          failed_sources: data.failed_sources || [],
          source_details: data.source_details || [],
          abort_message: data.abort_message || null
        }
        
        return
      }
      
      // 任务还在运行，获取最新日志
      fetchLogs()
    } catch (e) {
      console.error('Polling error:', e)
    }
  }, 2000)
}

async function fetchLogs() {
  try {
    const res = await fetch('/api/v1/fetch/logs')
    const data = await res.json()
    
    if (data.logs && data.logs.length > 0) {
      const newLogs = data.logs.slice(-50)
      newLogs.forEach(line => {
        const exists = streamLogs.value.some(l => l.text === line)
        if (!exists) {
          const isError = line.includes('失败') || line.includes('ERROR') || line.includes('反爬') || line.includes('403')
          const isSuccess = line.includes('完成') && !line.includes('失败') && !line.includes('中止')
          const isAbort = line.includes('中止')
          const type = isAbort ? 'abort' : (isError ? 'error' : (isSuccess ? 'success' : 'info'))
          addLog(line, type)
        }
      })
    }
  } catch (e) {
    console.error('Fetch logs error:', e)
  }
}

function onUnitChange() {
  if (syncUnit.value === 'hours') {
    syncIntervalValue.value = Math.max(1, Math.round(currentIntervalMinutes.value / 60))
  } else {
    syncIntervalValue.value = Math.max(1, currentIntervalMinutes.value)
  }
}

async function saveAutoConfig() {
  savingConfig.value = true
  try {
    let minutes = currentIntervalMinutes.value
    if (syncUnit.value === 'hours') {
      minutes = syncIntervalValue.value * 60
    }

    if (intervalEnabled.value && (minutes < 1 || minutes > 1440)) {
      Message.warning('间隔时间必须在 1~1440 分钟之间')
      savingConfig.value = false
      return
    }

    const timeParts = scheduledTimeValue.value.split(':')
    const scheduledTime = parseInt(timeParts[0]) || 8

    await fetch('/api/v1/update/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        interval_enabled: intervalEnabled.value,
        sync_interval: minutes,
        scheduled_enabled: scheduledEnabled.value,
        scheduled_time: scheduledTime,
        auto_generate_report: autoGenerateReport.value
      })
    })

    currentIntervalMinutes.value = minutes
    Message.success('自动更新设置已保存')
  } catch (e) {
    Message.error('保存失败')
  } finally {
    savingConfig.value = false
  }
}

async function loadAutoConfig() {
  try {
    const res = await fetch('/api/v1/update/config')
    const data = await res.json()
    if (data.code === 0) {
      intervalEnabled.value = data.data.interval_enabled !== false
      scheduledEnabled.value = data.data.scheduled_enabled === true

      currentIntervalMinutes.value = data.data.sync_interval || 60
      if (currentIntervalMinutes.value >= 60 && currentIntervalMinutes.value % 60 === 0) {
        syncUnit.value = 'hours'
        syncIntervalValue.value = currentIntervalMinutes.value / 60
      } else {
        syncUnit.value = 'minutes'
        syncIntervalValue.value = currentIntervalMinutes.value
      }

      const hour = data.data.scheduled_time || 8
      scheduledTimeValue.value = `${String(hour).padStart(2, '0')}:00`

      autoGenerateReport.value = data.data.auto_generate_report !== false
    }
  } catch (e) {
    console.error('Load update config error:', e)
  }
}

async function loadLastResult() {
  try {
    const res = await fetch('/api/v1/fetch/status')
    const data = await res.json()
    if (data.completed_at && !data.running) {
      lastResult.value = {
        started_at: data.started_at,
        completed_at: data.completed_at,
        total_saved: data.total_saved || 0,
        total_sources: data.total_sources || 0,
        aihot_result: data.aihot_result,
        crawler_result: data.crawler_result,
        failed_sources: data.failed_sources || [],
        source_details: data.source_details || [],
        abort_message: data.abort_message || null
      }
    }
  } catch (e) {
    console.error('Load status error:', e)
  }
}

onMounted(() => {
  loadAutoConfig()
  loadLastResult()
})
</script>

<style scoped>
.update-page {
  max-width: 1000px;
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

.action-section {
  margin-bottom: 20px;
}

.action-card {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 20px 24px;
  display: flex;
  align-items: center;
  gap: 16px;
}

.action-icon {
  font-size: 36px;
}

.action-content {
  flex: 1;
}

.action-title {
  font-size: 16px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
}

.action-desc {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.4);
  margin-top: 2px;
}

.action-buttons {
  display: flex;
  gap: 10px;
}

.config-section {
  margin-bottom: 20px;
}

.config-card {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 20px 24px;
}

.config-title {
  font-size: 16px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
  margin-bottom: 16px;
}

.config-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.config-label {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.6);
}

.config-hint {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.3);
  margin-top: 12px;
}

.divider {
  height: 1px;
  background: rgba(255, 255, 255, 0.06);
  margin: 16px 0;
}

.update-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin: 16px 0;
}

.config-block {
  padding: 8px 0;
}

.ml-12 {
  margin-left: 12px;
}

.ml-20 {
  margin-left: 20px;
}

.switch-container {
  width: 44px;
  height: 24px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.15);
  cursor: pointer;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  padding: 0 2px;
}
.custom-switch {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.4);
  transition: all 0.3s;
  display: flex;
  align-items: center;
  justify-content: center;
}
.light .custom-switch {
  background: rgba(0, 0, 0, 0.3);
}
.switch-on .custom-switch {
  background: #10B981;
  transform: translateX(20px);
}
.switch-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: white;
}
.switch-on .switch-dot {
  background: white;
}

.result-section {
  margin-bottom: 20px;
}

.result-card {
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 20px 24px;
}

.result-title {
  font-size: 16px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
  margin-bottom: 16px;
}

.aborted-banner {
  background: rgba(234, 179, 8, 0.1);
  border: 1px solid rgba(234, 179, 8, 0.3);
  border-radius: 8px;
  padding: 10px 16px;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.aborted-text {
  font-size: 14px;
  color: #EAB308;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.result-item {
  text-align: center;
}

.result-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
  margin-bottom: 4px;
}

.result-value {
  font-size: 24px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.7);
}

.result-value.success {
  color: #10B981;
}

.result-summary {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.5);
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.result-summary .highlight {
  color: #60a5fa;
  font-weight: 700;
  font-size: 18px;
}

.failed-sources {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.failed-title {
  font-size: 14px;
  font-weight: 600;
  color: #EF4444;
  margin-bottom: 10px;
}

.failed-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.failed-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.02);
  border-radius: 6px;
  font-size: 13px;
}

.failed-item.blocked {
  background: rgba(239, 68, 68, 0.08);
  border: 1px solid rgba(239, 68, 68, 0.15);
}

.failed-name {
  font-weight: 600;
  color: rgba(255, 255, 255, 0.8);
  min-width: 100px;
}

.failed-type {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.06);
  padding: 2px 8px;
  border-radius: 4px;
}

.failed-error {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-details-toggle {
  margin-top: 12px;
}

.source-details-list {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-height: 300px;
  overflow-y: auto;
}

.source-detail-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px;
  font-size: 12px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.02);
}

.source-detail-item.detail-failed {
  background: rgba(239, 68, 68, 0.05);
}

.detail-name {
  font-weight: 600;
  color: rgba(255, 255, 255, 0.7);
  min-width: 100px;
}

.detail-tier {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.3);
  background: rgba(255, 255, 255, 0.06);
  padding: 1px 6px;
  border-radius: 3px;
}

.detail-count {
  color: rgba(255, 255, 255, 0.4);
}

.detail-saved {
  color: #10B981;
  font-weight: 600;
}

.detail-error {
  color: #EF4444;
  font-size: 11px;
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.stream-section {
  margin-bottom: 20px;
}

.stream-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.stream-title {
  font-size: 16px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
}

.stream-container {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  overflow: hidden;
}

.stream-empty {
  padding: 40px;
  text-align: center;
  color: rgba(255, 255, 255, 0.3);
  font-size: 14px;
}

.stream-logs {
  max-height: 450px;
  overflow-y: auto;
  padding: 16px;
}

.stream-log {
  font-family: 'SF Mono', 'Monaco', 'Consolas', monospace;
  font-size: 12px;
  line-height: 1.8;
  padding: 2px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
}

.stream-log:last-child {
  border-bottom: none;
}

.log-time {
  color: rgba(255, 255, 255, 0.25);
  margin-right: 12px;
  user-select: none;
}

.log-info .log-text {
  color: rgba(255, 255, 255, 0.7);
}

.log-error .log-text {
  color: #EF4444;
}

.log-success .log-text {
  color: #10B981;
}

.log-abort .log-text {
  color: #EAB308;
}
</style>
