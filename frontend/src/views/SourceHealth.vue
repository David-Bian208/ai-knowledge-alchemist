<template>
  <Layout>
    <div class="source-health-page">
      <div class="page-header">
        <h1 class="page-title">📈 信源健康监控</h1>
        <p class="page-subtitle">实时监控信源健康状态，同步信源管理配置</p>
      </div>

      <!-- 统计概览 -->
      <div class="stats-overview">
        <div class="stat-card">
          <div class="stat-icon">📊</div>
          <div class="stat-info">
            <div class="stat-label">成功率</div>
            <div class="stat-value" :style="{ color: stats.success_rate >= 80 ? '#10B981' : '#EF4444' }">
              {{ stats.success_rate }}%
            </div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">✅</div>
          <div class="stat-info">
            <div class="stat-label">健康信源</div>
            <div class="stat-value" style="color:#10B981">{{ stats.healthy }}</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">⚠️</div>
          <div class="stat-info">
            <div class="stat-label">警告信源</div>
            <div class="stat-value" style="color:#F59E0B">{{ stats.warning }}</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">❌</div>
          <div class="stat-info">
            <div class="stat-label">失效信源</div>
            <div class="stat-value" style="color:#EF4444">{{ stats.unhealthy }}</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">📡</div>
          <div class="stat-info">
            <div class="stat-label">总信源数</div>
            <div class="stat-value">{{ stats.total }}</div>
          </div>
        </div>
      </div>

      <!-- 信源健康列表（与信源管理一致的信源信息） -->
      <div class="section">
        <div class="section-title-row">
          <h2 class="section-title">📋 信源健康列表</h2>
          <div class="filter-controls">
            <a-radio-group v-model="healthFilter" type="button" size="small">
              <a-radio value="all">全部 ({{ healthSources.length }})</a-radio>
              <a-radio value="healthy">健康 ({{ healthyCount }})</a-radio>
              <a-radio value="warning">警告 ({{ warningCount }})</a-radio>
              <a-radio value="unhealthy">失效 ({{ unhealthyCount }})</a-radio>
            </a-radio-group>
          </div>
        </div>
        <a-table :data="filteredHealthList" :columns="healthColumns" :pagination="{ pageSize: 20, showTotal: true }" :loading="loading" row-key="source_id" size="small">
          <template #name="{ record }">
            <div class="source-name-cell">
              <span class="source-name">{{ record.source_name }}</span>
              <span class="source-id">{{ record.source_id }}</span>
            </div>
          </template>
          <template #status="{ record }">
            <a-tag v-if="record.is_healthy === 1" color="green">健康</a-tag>
            <a-tag v-else-if="record.consecutive_failures >= 3" color="red">失效</a-tag>
            <a-tag v-else color="orange">警告</a-tag>
          </template>
          <template #failures="{ record }">
            <span :style="{ color: record.consecutive_failures >= 3 ? '#EF4444' : record.consecutive_failures > 0 ? '#F59E0B' : '#10B981' }">
              {{ record.consecutive_failures }}
            </span>
          </template>
          <template #last_error="{ record }">
            <span :title="record.last_error" class="error-text">{{ record.last_error ? record.last_error.substring(0, 40) : '-' }}</span>
          </template>
          <template #last_check="{ record }">
            <div v-if="record.last_check_time">{{ formatTime(record.last_check_time) }}</div>
            <span v-else class="no-data">未检测</span>
          </template>
          <template #tags="{ record }">
            <div class="tags-cell">
              <a-tag v-for="tag in (record.tags || []).slice(0, 3)" :key="tag" size="small" :color="getTagColor(tag)">{{ tag }}</a-tag>
              <span v-if="(record.tags || []).length > 3" class="more-tags">+{{ record.tags.length - 3 }}</span>
            </div>
          </template>
          <template #action="{ record }">
            <div class="action-btns">
              <a-button type="text" size="mini" @click="handleCheckSingle(record.source_id)" :loading="checkingSingle === record.source_id">
                检测
              </a-button>
            </div>
          </template>
        </a-table>
      </div>

      <!-- 手动检测 -->
      <div class="section">
        <h2 class="section-title">🔍 手动检测</h2>
        <div class="manual-check">
          <a-select v-model="checkSourceId" placeholder="选择信源" style="width: 360px" :options="sourceOptions" allow-search />
          <a-button type="primary" @click="handleCheckSource" :loading="checking">
            {{ checking ? '检测中...' : '立即检测' }}
          </a-button>
        </div>
        <a-alert v-if="checkResult" :type="checkResult.reachable ? 'success' : 'error'" style="margin-top: 12px">
          <div class="check-result-content">
            <span class="check-result-text">{{ checkResultText }}</span>
            <div v-if="checkResult.response_time_ms" class="check-detail">
              <span>状态码: {{ checkResult.status }}</span>
              <span>耗时: {{ checkResult.response_time_ms }}ms</span>
              <span v-if="checkResult.error_message">错误: {{ checkResult.error_message }}</span>
            </div>
          </div>
        </a-alert>
      </div>

      <!-- 健康记录查询 -->
      <div class="section">
        <h2 class="section-title">📜 健康记录查询</h2>
        <div class="log-filters">
          <a-select v-model="logSourceId" placeholder="选择信源（全部）" style="width: 300px" :options="sourceOptions" allow-search allow-clear />
          <a-select v-model="logLimit" style="width: 120px">
            <a-option :value="20">20条</a-option>
            <a-option :value="50">50条</a-option>
            <a-option :value="100">100条</a-option>
          </a-select>
        </div>
        <a-table :data="healthLogsData" :columns="logColumns" :pagination="{ pageSize: 20, showTotal: true }" :loading="loading" row-key="id" size="small">
          <template #reachable="{ record }">
            <a-tag :color="record.reachable ? 'green' : 'red'">
              {{ record.reachable ? '成功' : '失败' }}
            </a-tag>
          </template>
          <template #response_time_ms="{ record }">
            <span :style="{ color: record.response_time_ms > 1000 ? '#EF4444' : record.response_time_ms > 500 ? '#F59E0B' : '#10B981' }">
              {{ record.response_time_ms }}ms
            </span>
          </template>
        </a-table>
      </div>

      <div class="action-bar">
        <a-button type="primary" @click="refreshAll" :loading="loading">
          🔄 刷新监控数据
        </a-button>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { Message } from '@arco-design/web-vue'
import Layout from '../components/Layout.vue'
import { getHealthStats, getAllSourceHealth, getHealthLogs, checkSourceHealth } from '../api/index.js'

const loading = ref(false)
const stats = ref({ total: 0, healthy: 0, warning: 0, unhealthy: 0, success_rate: 0, error_distribution: {} })
const healthSources = ref([])
const healthLogsData = ref([])
const healthFilter = ref('all')

const checkSourceId = ref(undefined)
const checkResult = ref(null)
const checking = ref(false)
const checkingSingle = ref(null)
const sourceOptions = ref([])

const logSourceId = ref(undefined)
const logLimit = ref(50)

const checkResultText = computed(() => {
  if (!checkResult.value) return ''
  const r = checkResult.value
  return r.reachable
    ? `✅ ${r.source_name}: ${r.status} (${r.response_time_ms}ms)`
    : `❌ ${r.source_name}: ${r.status} - ${r.error_message || ''}`
})

const healthyCount = computed(() => healthSources.value.filter(s => s.is_healthy === 1).length)
const warningCount = computed(() => healthSources.value.filter(s => s.is_healthy === 0 && s.consecutive_failures < 3).length)
const unhealthyCount = computed(() => healthSources.value.filter(s => s.is_healthy === 0 && s.consecutive_failures >= 3).length)

const filteredHealthList = computed(() => {
  if (healthFilter.value === 'all') return healthSources.value
  if (healthFilter.value === 'healthy') return healthSources.value.filter(s => s.is_healthy === 1)
  if (healthFilter.value === 'unhealthy') return healthSources.value.filter(s => s.is_healthy === 0 && s.consecutive_failures >= 3)
  if (healthFilter.value === 'warning') return healthSources.value.filter(s => s.is_healthy === 0 && s.consecutive_failures < 3)
  return healthSources.value
})

const healthColumns = [
  { title: '信源名称', key: 'name', slotName: 'name', width: 180 },
  { title: 'URL', dataIndex: 'source_url', key: 'source_url', ellipsis: true, tooltip: true, width: 200 },
  { title: '等级', dataIndex: 'tier', key: 'tier', width: 50 },
  { title: '类型', dataIndex: 'type', key: 'type', width: 50 },
  { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
  { title: '标签', key: 'tags', slotName: 'tags', width: 100 },
  { title: '状态', key: 'status', slotName: 'status', width: 60 },
  { title: '连续失败', key: 'failures', slotName: 'failures', width: 80 },
  { title: '最后错误', key: 'last_error', slotName: 'last_error', ellipsis: true },
  { title: '最后检测', key: 'last_check', slotName: 'last_check', width: 130 },
  { title: '操作', key: 'action', slotName: 'action', width: 70 }
]

const logColumns = [
  { title: '信源', dataIndex: 'source_name', key: 'source_name', width: 150 },
  { title: '检测时间', dataIndex: 'check_time', key: 'check_time', width: 180 },
  { title: '结果', key: 'reachable', slotName: 'reachable', width: 80 },
  { title: '状态码', dataIndex: 'status', key: 'status', width: 100 },
  { title: '耗时', key: 'response_time_ms', slotName: 'response_time_ms', width: 80 },
  { title: '错误信息', dataIndex: 'error_message', key: 'error_message', ellipsis: true }
]

function formatTime(isoStr) {
  if (!isoStr) return ''
  try {
    const d = new Date(isoStr)
    return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return isoStr
  }
}

const tagColors = {
  'AI': 'blue', '科技': 'cyan', '开源': 'purple', '工具': 'green',
  '效率': 'arcoblue', '商业': 'orange', '投资': 'gold', '决策': 'magenta',
  '管理': 'red', '思维': 'purple', '习惯': 'green', '成长': 'arcoblue'
}

function getTagColor(tag) {
  return tagColors[tag] || 'gray'
}

const fetchStats = async () => {
  try {
    const res = await getHealthStats()
    stats.value = res.data.data || {}
  } catch (e) {
    console.error('获取统计失败', e)
  }
}

const fetchHealthSources = async () => {
  try {
    const res = await getAllSourceHealth()
    healthSources.value = res.data.data || []
    sourceOptions.value = healthSources.value.map(s => ({
      label: `${s.source_name} (${s.source_id})`,
      value: s.source_id
    }))
  } catch (e) {
    console.error('获取信源列表失败', e)
  }
}

const fetchHealthLogs = async () => {
  try {
    const params = { limit: logLimit.value }
    if (logSourceId.value) params.source_id = logSourceId.value
    const res = await getHealthLogs(params)
    healthLogsData.value = res.data.data || []
  } catch (e) {
    console.error('获取日志失败', e)
  }
}

const handleCheckSource = async () => {
  if (!checkSourceId.value) {
    Message.warning('请选择信源')
    return
  }
  checking.value = true
  try {
    const res = await checkSourceHealth(checkSourceId.value)
    checkResult.value = res.data.data
    Message.success(checkResult.value.reachable ? '信源可访问' : '信源不可访问')
    await fetchStats()
    await fetchHealthSources()
  } catch (e) {
    Message.error('检测失败: ' + (e.response?.data?.msg || e.message))
  } finally {
    checking.value = false
  }
}

const handleCheckSingle = async (sourceId) => {
  checkingSingle.value = sourceId
  try {
    const res = await checkSourceHealth(sourceId)
    Message.success(res.data.data.reachable ? '✅ 可访问' : '❌ 不可访问')
    await fetchHealthSources()
    await fetchStats()
  } catch (e) {
    Message.error('检测失败')
  } finally {
    checkingSingle.value = null
  }
}

const refreshAll = async () => {
  loading.value = true
  await Promise.all([fetchStats(), fetchHealthSources(), fetchHealthLogs()])
  loading.value = false
  Message.success('数据已刷新')
}

watch([logSourceId, logLimit], () => {
  fetchHealthLogs()
})

onMounted(() => {
  refreshAll()
})
</script>

<style scoped>
.source-health-page {
  max-width: 1200px;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 4px;
  background: linear-gradient(135deg, #60a5fa, #8b5cf6);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.page-subtitle {
  font-size: 13px;
  color: rgba(255,255,255,0.4);
  margin: 0;
}

.light .page-subtitle {
  color: rgba(0,0,0,0.4);
}

.stats-overview {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}

.stat-card {
  background: rgba(30,41,59,0.6);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 12px;
}

.light .stat-card {
  background: rgba(248,250,252,0.6);
  border: 1px solid rgba(0,0,0,0.06);
}

.stat-icon {
  font-size: 24px;
}

.stat-label {
  font-size: 11px;
  color: rgba(255,255,255,0.4);
}

.light .stat-label {
  color: rgba(0,0,0,0.4);
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: #60a5fa;
}

.section {
  background: rgba(30,41,59,0.6);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  padding: 20px 24px;
  margin-bottom: 20px;
}

.light .section {
  background: rgba(248,250,252,0.6);
  border: 1px solid rgba(0,0,0,0.08);
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 16px 0;
}

.section-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

.manual-check {
  display: flex;
  align-items: center;
  gap: 12px;
}

.check-result-content {
  width: 100%;
}

.check-result-text {
  font-size: 14px;
  font-weight: 500;
}

.check-detail {
  margin-top: 6px;
  display: flex;
  gap: 24px;
  font-size: 12px;
  opacity: 0.8;
}

.log-filters {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.action-bar {
  display: flex;
  justify-content: center;
  margin-top: 16px;
}

.source-name-cell {
  display: flex;
  flex-direction: column;
}

.source-name {
  font-weight: 500;
}

.source-id {
  font-size: 11px;
  color: rgba(255,255,255,0.3);
}

.light .source-id {
  color: rgba(0,0,0,0.3);
}

.error-text {
  font-size: 12px;
}

.action-btns {
  display: flex;
  gap: 4px;
}

.tags-cell {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  align-items: center;
}

.more-tags {
  font-size: 11px;
  color: rgba(255,255,255,0.4);
}

.light .more-tags {
  color: rgba(0,0,0,0.4);
}

.no-data {
  color: rgba(255,255,255,0.3);
  font-size: 12px;
}

.light .no-data {
  color: rgba(0,0,0,0.3);
}

@media (max-width: 768px) {
  .stats-overview {
    grid-template-columns: repeat(2, 1fr);
  }
  .section-title-row {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
