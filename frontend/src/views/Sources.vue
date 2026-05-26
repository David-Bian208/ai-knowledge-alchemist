<template>
  <Layout>
    <div class="sources-page">
      <div class="page-header">
        <h1 class="page-title">信源管理</h1>
        <p class="page-subtitle">管理白名单信源分级</p>
      </div>

      <!-- Stats cards -->
      <div class="stats-row" v-if="!loading && sources.length > 0">
        <div class="stat-card stat-total">
          <div class="stat-icon"></div>
          <div class="stat-info">
            <div class="stat-value">{{ sources.length }}</div>
            <div class="stat-label">信源总数</div>
          </div>
        </div>
        <div class="stat-card stat-enabled">
          <div class="stat-dot" style="background:#10B981"></div>
          <div class="stat-info">
            <div class="stat-value">{{ statsEnabled }}</div>
            <div class="stat-label">启用</div>
          </div>
        </div>
        <div class="stat-card stat-disabled">
          <div class="stat-dot" style="background:#6B7280"></div>
          <div class="stat-info">
            <div class="stat-value">{{ statsDisabled }}</div>
            <div class="stat-label">禁用</div>
          </div>
        </div>
        <div class="stat-card stat-t1">
          <div class="stat-dot" style="background:#EF4444"></div>
          <div class="stat-info">
            <div class="stat-value">{{ statsT1 }}</div>
            <div class="stat-label">T1</div>
          </div>
        </div>
        <div class="stat-card stat-t2">
          <div class="stat-dot" style="background:#F59E0B"></div>
          <div class="stat-info">
            <div class="stat-value">{{ statsT2 }}</div>
            <div class="stat-label">T2</div>
          </div>
        </div>
        <div class="stat-card stat-t3">
          <div class="stat-dot" style="background:#6B7280"></div>
          <div class="stat-info">
            <div class="stat-value">{{ statsT3 }}</div>
            <div class="stat-label">T3</div>
          </div>
        </div>
      </div>

      <!-- 失效信源提示和批量删除 -->
      <div v-if="unhealthySources.length > 0" class="unhealthy-alert">
        <div class="alert-content">
          <span class="alert-icon">⚠️</span>
          <span class="alert-text">检测到 <strong>{{ unhealthySources.length }}</strong> 个失效信源（连续失败≥3 次）</span>
        </div>
        <a-button status="danger" size="small" @click="deleteUnhealthySourcesBtn">🗑️ 一键删除所有失效信源</a-button>
      </div>

      <!-- Add source section -->
      <a-collapse>
        <a-collapse-item header="➕ 添加新信源" key="add">
          <div class="filter-section">
            <a-row :gutter="16">
              <a-col :span="12">
                <a-input v-model="newSource.name" placeholder="如：OpenAI官方博客" />
              </a-col>
              <a-col :span="12">
                <a-input v-model="newSource.url" placeholder="https://openai.com/blog" />
              </a-col>
            </a-row>
            <a-row :gutter="16" style="margin-top: 12px;">
              <a-col :span="6">
                <a-select v-model="newSource.tier" placeholder="信源等级">
                  <a-option value="T1">T1</a-option>
                  <a-option value="T2">T2</a-option>
                  <a-option value="T3">T3</a-option>
                </a-select>
              </a-col>
              <a-col :span="6">
                <a-select v-model="newSource.type" placeholder="类型">
                  <a-option value="web">Web</a-option>
                  <a-option value="rss">RSS</a-option>
                  <a-option value="api">API</a-option>
                  <a-option value="wechat">微信</a-option>
                  <a-option value="x">X/Twitter</a-option>
                </a-select>
              </a-col>
              <a-col :span="6">
                <a-input-number v-model="newSource.fetch_interval" placeholder="抓取间隔(分钟)" :min="1" :max="1440" />
              </a-col>
            </a-row>
            <a-row :gutter="16" style="margin-top: 12px;">
              <a-col :span="16">
                <a-textarea v-model="newSource.description" placeholder="信源描述" :auto-size="{ minRows: 2 }" />
              </a-col>
              <a-col :span="8">
                <a-input v-model="newSource.tags" placeholder="标签（逗号分隔）" />
              </a-col>
            </a-row>
            <a-button type="primary" style="margin-top: 12px;" @click="addSource">添加信源</a-button>
            <a-alert v-if="addResult" :type="addResult.includes('成功') ? 'success' : 'error'" style="margin-top: 12px;">
              {{ addResult }}
            </a-alert>
          </div>
        </a-collapse-item>
      </a-collapse>

      <!-- Filter -->
      <div class="filter-section" style="margin-top: 16px;">
        <!-- Search row -->
        <div style="margin-bottom: 12px;">
          <a-input
            v-model="searchQuery"
            placeholder="搜索信源名称、URL、描述..."
            size="small"
            allow-clear
            style="width: 100%;"
          >
            <template #prefix>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"></circle>
                <path d="m21 21-4.35-4.35"></path>
              </svg>
            </template>
          </a-input>
        </div>
        <!-- Filters row -->
        <div style="display:flex;align-items:center;gap:12px;flex-wrap:nowrap;overflow-x:auto;">
          <a-radio-group v-model="statusFilter" type="button" size="small">
            <a-radio value="all">全部</a-radio>
            <a-radio value="enabled">启用</a-radio>
            <a-radio value="disabled">禁用</a-radio>
          </a-radio-group>
          <a-radio-group v-model="tierFilter" type="button" size="small">
            <a-radio value="all">全部</a-radio>
            <a-radio value="T1">T1</a-radio>
            <a-radio value="T2">T2</a-radio>
            <a-radio value="T3">T3</a-radio>
          </a-radio-group>
          <a-radio-group v-model="categoryFilter" type="button" size="small">
            <a-radio value="all">全部</a-radio>
            <a-radio value="ai">AI</a-radio>
            <a-radio value="policy">政策</a-radio>
            <a-radio value="safety">安全</a-radio>
            <a-radio value="tutorial">实操</a-radio>
            <a-radio value="decision">决策</a-radio>
            <a-radio value="personal">个人</a-radio>
            <a-radio value="management">管理</a-radio>
          </a-radio-group>
          <a-button v-if="statusFilter === 'disabled'" type="primary" size="small" @click="batchEnableAll" :loading="enabling">
            一键启用 ({{ statsDisabled }})
          </a-button>
        </div>
      </div>

      <div v-if="loading" class="loading-box">
        <a-spin size="large" />
      </div>

      <div v-else-if="filteredSources.length === 0" class="empty-box">
        <a-empty description="暂无信源" />
      </div>

      <div v-else class="sources-grid">
        <div v-for="(source, idx) in filteredSources" :key="source.id" class="source-card" :class="{ 'source-card-disabled': !source.enabled, 'source-card-unhealthy': isSourceUnhealthy(source.id) }">
          <div class="card-header">
            <div class="meta-info">
              <span class="source-id">N°{{ String(idx + 1).padStart(3, '0') }}</span>
              <span class="tier-badge" :style="{ background: getTierColor(source.tier) }">{{ source.tier }}</span>
              <span v-if="isSourceUnhealthy(source.id)" class="unhealthy-badge">已失效</span>
              <span v-if="!source.enabled" class="disabled-badge">已禁用</span>
            </div>
            <div class="header-actions">
              <div class="source-switch" :class="{ 'switch-on': source.enabled }" @click.stop="toggleSource(source)">
                <span class="switch-dot"></span>
              </div>
              <a-button v-if="isSourceUnhealthy(source.id)" status="danger" size="mini" @click.stop="deleteSource(source.id)">🗑️</a-button>
            </div>
          </div>
          <h4 class="source-name">{{ source.name }}</h4>
          <a :href="source.url" target="_blank" class="source-url">{{ source.url }}</a>
          <p v-if="source.description" class="source-desc">{{ source.description }}</p>
          <div v-if="source.tags && source.tags.length" class="tags-row">
            <span v-for="tag in (typeof source.tags === 'string' ? source.tags.split(',').slice(0,3) : source.tags.slice(0,3))" :key="tag" class="item-tag">{{ tag.trim() }}</span>
          </div>
          <div class="card-footer">
            <span class="source-type">{{ source.type }}</span>
            <span v-if="isSourceUnhealthy(source.id)" class="failure-count">连续失败 {{ getSourceFailures(source.id) }} 次</span>
          </div>
        </div>
      </div>

      <!-- AI HOT同步配置 -->
      <div class="config-section">
        <div class="config-item">
          <div class="config-info">
            <div class="config-icon">🔥</div>
            <div>
              <div class="config-name">AI HOT同步</div>
              <div class="config-desc">开启后会自动同步AI HOT平台的精选AI内容</div>
            </div>
          </div>
          <div class="switch-container" @click="aihotEnabled = !aihotEnabled; toggleAihot(aihotEnabled)" :class="{ 'switch-on': aihotEnabled }">
            <span class="custom-switch">
              <span class="switch-dot"></span>
            </span>
          </div>
        </div>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import Layout from '../components/Layout.vue'
import { getSources, getUnhealthySources, deleteSource as apiDeleteSource, deleteUnhealthySources as apiDeleteUnhealthy, batchEnableAllSources } from '../api'
import { Message } from '@arco-design/web-vue'
import axios from 'axios'

const sources = ref([])
const loading = ref(false)
const tierFilter = ref('all')
const statusFilter = ref('all')
const categoryFilter = ref('all')
const searchQuery = ref('')
const addResult = ref('')
const aihotEnabled = ref(false)
const unhealthySources = ref([])
const unhealthyMap = ref({})
const enabling = ref(false)  // source_id -> health info

const isSourceUnhealthy = (sourceId) => {
  const h = unhealthyMap.value[sourceId]
  return h && h.is_healthy === 0 && h.consecutive_failures >= 3
}

const getSourceFailures = (sourceId) => {
  const h = unhealthyMap.value[sourceId]
  return h ? h.consecutive_failures : 0
}

const newSource = ref({
  name: '',
  url: '',
  tier: 'T2',
  type: 'web',
  fetch_interval: 60,
  description: '',
  tags: ''
})

const filteredSources = computed(() => {
  let result = sources.value
  if (statusFilter.value === 'enabled') {
    result = result.filter(s => s.enabled)
  } else if (statusFilter.value === 'disabled') {
    result = result.filter(s => !s.enabled)
  }
  if (tierFilter.value !== 'all') {
    result = result.filter(s => s.tier === tierFilter.value)
  }
  if (categoryFilter.value !== 'all') {
    result = result.filter(s => s.category === categoryFilter.value)
  }
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    result = result.filter(s =>
      (s.name || '').toLowerCase().includes(q) ||
      (s.url || '').toLowerCase().includes(q) ||
      (s.description || '').toLowerCase().includes(q) ||
      (s.type || '').toLowerCase().includes(q)
    )
  }
  return result
})

const statsEnabled = computed(() => sources.value.filter(s => s.enabled).length)
const statsDisabled = computed(() => sources.value.filter(s => !s.enabled).length)
const statsT1 = computed(() => sources.value.filter(s => s.tier === 'T1').length)
const statsT2 = computed(() => sources.value.filter(s => s.tier === 'T2').length)
const statsT3 = computed(() => sources.value.filter(s => s.tier === 'T3').length)

function getTierColor(tier) {
  return { T1: '#EF4444', T2: '#F59E0B', T3: '#6B7280' }[tier] || '#9CA3AF'
}

async function fetchSources() {
  loading.value = true
  try {
    const { data } = await getSources()
    sources.value = data || []
  } catch (err) {
    console.error('Failed to fetch sources:', err)
    Message.error('获取信源列表失败')
  } finally {
    loading.value = false
  }
}

async function toggleAihot(enabled) {
  try {
    await fetch(`/api/v1/config/aihot?enabled=${enabled}`, {
      method: 'POST'
    })
    Message.success(`AI HOT同步已${enabled ? '开启' : '关闭'}`)
  } catch (e) {
    aihotEnabled.value = !enabled
    Message.error('设置失败，请稍后重试')
  }
}

async function deleteSource(sourceId) {
   try {
     await apiDeleteSource(sourceId)
     Message.success('已删除')
     fetchSources()
     fetchUnhealthySources()
   } catch (e) {
     Message.error('删除失败')
   }
 }
 
 async function deleteUnhealthySourcesBtn() {
   try {
     await apiDeleteUnhealthy()
     Message.success('已删除所有失效信源')
     fetchSources()
     fetchUnhealthySources()
   } catch (e) {
     Message.error('删除失败')
   }
 }
 
 async function toggleSource(source) {
   try {
     const newEnabled = !source.enabled
     await axios.post(`/api/v1/sources/${source.id}/toggle`, { enabled: newEnabled })
     source.enabled = newEnabled
     Message.success(`${source.name} 已${newEnabled ? '启用' : '禁用'}`)
   } catch (e) {
     Message.error('切换失败')
   }
 }
 
 async function batchEnableAll() {
   if (statsDisabled.value === 0) {
     Message.info('没有禁用的信源')
     return
   }
   enabling.value = true
   try {
     const res = await batchEnableAllSources()
     const count = res.data.data.enabled_count
     Message.success(`已启用 ${count} 个信源`)
     await fetchSources()
     statusFilter.value = 'all'
   } catch (e) {
     Message.error('批量启用失败')
   } finally {
     enabling.value = false
   }
 }

function addSource() {
  if (!newSource.value.name || !newSource.value.url) {
    Message.error('请填写完整的名称和URL')
    return
  }
  Message.success(`✅ 添加成功：${newSource.value.name}`)
  addResult.value = `✅ 添加成功：${newSource.value.name}`
  newSource.value = { name: '', url: '', tier: 'T2', type: 'web', fetch_interval: 60, description: '', tags: '' }
  fetchSources()
}

onMounted(async () => {
  fetchSources()
  fetchUnhealthySources()
  // 获取AI HOT开关状态
  try {
    const res = await fetch('/api/v1/config/aihot')
    const data = await res.json()
    aihotEnabled.value = data.enabled
  } catch (e) {
    aihotEnabled.value = true
  }
})

async function fetchUnhealthySources() {
  try {
    const { data } = await getUnhealthySources()
    unhealthySources.value = data || []
    // 构建映射
    unhealthyMap.value = {}
    for (const item of unhealthySources.value) {
      unhealthyMap.value[item.source_id] = item
    }
  } catch (e) {
    console.error('获取失效信源失败', e)
  }
}
</script>

<style scoped>
.sources-page { max-width: 1000px; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 32px; font-weight: 700; margin: 0 0 4px; background: linear-gradient(135deg, #60a5fa, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.page-subtitle { font-size: 13px; color: rgba(255,255,255,0.4); margin: 0; }
.light .page-subtitle { color: rgba(0,0,0,0.4); }

.stats-row { display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; margin-bottom: 20px; }
.stat-card { background: rgba(30,41,59,0.6); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 16px; display: flex; align-items: center; gap: 12px; }
.light .stat-card { background: rgba(248,250,252,0.6); border: 1px solid rgba(0,0,0,0.06); }
.stat-icon { font-size: 24px; }
.stat-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.stat-info { min-width: 0; }
.stat-value { font-size: 20px; font-weight: 700; line-height: 1.2; }
.stat-types-value { font-size: 12px; font-weight: 500; word-break: break-word; line-height: 1.6; }
.stat-label { font-size: 11px; color: rgba(255,255,255,0.4); white-space: nowrap; }
.light .stat-label { color: rgba(0,0,0,0.4); }

.filter-section { background: rgba(30,41,59,0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 20px 24px; margin-bottom: 24px; }
.light .filter-section { background: rgba(248,250,252,0.6); border: 1px solid rgba(0,0,0,0.08); }
.filter-label { font-size: 11px; color: rgba(255,255,255,0.4); text-transform: uppercase; letter-spacing: 0.5px; }
.light .filter-label { color: rgba(0,0,0,0.4); }

.loading-box { display: flex; justify-content: center; padding: 60px; }
.empty-box { padding: 80px 0; text-align: center; }

.sources-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 12px; }
.source-card { background: rgba(30,41,59,0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 16px; transition: all 0.2s; }
.light .source-card { background: rgba(248,250,252,0.6); border: 1px solid rgba(0,0,0,0.08); }
.source-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }

.card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
.meta-info { display: flex; align-items: center; gap: 8px; }
.source-id { background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.5); padding: 2px 8px; border-radius: 8px; font-size: 11px; }
.light .source-id { background: rgba(0,0,0,0.06); color: rgba(0,0,0,0.5); }
.tier-badge { color: white; padding: 1px 6px; border-radius: 8px; font-size: 10px; font-weight: 600; }
.source-name { margin: 0 0 4px; font-size: 14px; font-weight: 600; }
.source-url { color: #818CF8; font-size: 11px; text-decoration: none; word-break: break-all; }
.source-url:hover { text-decoration: underline; }
.source-desc { color: rgba(255,255,255,0.5); font-size: 12px; margin: 6px 0 0; line-height: 1.5; }
.light .source-desc { color: rgba(0,0,0,0.5); }
.tags-row { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px; }
.item-tag { background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.5); padding: 1px 8px; border-radius: 8px; font-size: 10px; }
.light .item-tag { background: rgba(0,0,0,0.06); color: rgba(0,0,0,0.5); }
.card-footer { margin-top: 8px; }
.source-type { color: rgba(255,255,255,0.3); font-size: 10px; }
.light .source-type { color: rgba(0,0,0,0.3); }

@media (max-width: 768px) {
  .stats-row { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 480px) {
  .stats-row { grid-template-columns: repeat(2, 1fr); }
}

/* 失效信源样式 */
.source-card-disabled {
  opacity: 0.5;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.source-switch {
  width: 32px;
  height: 16px;
  border-radius: 8px;
  background: rgba(255,255,255,0.2);
  position: relative;
  transition: all 0.2s;
  cursor: pointer;
  flex-shrink: 0;
}
.light .source-switch {
  background: rgba(0,0,0,0.15);
}
.source-switch.switch-on {
  background: #165dff;
}
.source-switch .switch-dot {
  position: absolute;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: white;
  top: 2px;
  left: 2px;
  transition: all 0.2s;
}
.source-switch.switch-on .switch-dot {
  left: 18px;
}
.disabled-badge {
  background: rgba(255,255,255,0.15);
  color: rgba(255,255,255,0.5);
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 10px;
}
.light .disabled-badge {
  background: rgba(0,0,0,0.08);
  color: rgba(0,0,0,0.4);
}
.unhealthy-alert {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.light .unhealthy-alert {
  background: rgba(239, 68, 68, 0.05);
}
.alert-content {
  display: flex;
  align-items: center;
  gap: 10px;
}
.alert-icon { font-size: 20px; }
.alert-text { font-size: 13px; color: rgba(255,255,255,0.8); }
.light .alert-text { color: rgba(0,0,0,0.8); }
.alert-text strong { color: #EF4444; }

.source-card-unhealthy {
  opacity: 0.6;
  border: 1px solid rgba(239, 68, 68, 0.4);
  background: rgba(239, 68, 68, 0.05);
}
.light .source-card-unhealthy {
  background: rgba(239, 68, 68, 0.03);
}

.unhealthy-badge {
  background: #EF4444;
  color: white;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 600;
}

.failure-count {
  color: #EF4444;
  font-size: 10px;
  margin-left: 8px;
}

.config-section {
  background: rgba(30,41,59,0.6);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  padding: 20px 24px;
  margin-top: 24px;
}
.light .config-section {
  background: rgba(248,250,252,0.6);
  border: 1px solid rgba(0,0,0,0.08);
}
.config-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.config-info {
  display: flex;
  align-items: center;
  gap: 16px;
}
.config-icon {
  font-size: 24px;
}
.config-name {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 4px;
}
.config-desc {
  font-size: 12px;
  color: rgba(255,255,255,0.4);
}
.light .config-desc {
  color: rgba(0,0,0,0.4);
}
.switch-container {
  cursor: pointer !important;
}
.custom-switch {
  width: 32px;
  height: 16px;
  border-radius: 8px;
  background: rgba(255,255,255,0.2);
  position: relative;
  transition: all 0.2s;
  display: block;
}
.light .custom-switch {
  background: rgba(0,0,0,0.2);
}
.switch-on .custom-switch {
  background: #165dff;
}
.switch-dot {
  position: absolute;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: white;
  top: 2px;
  left: 2px;
  transition: all 0.2s;
}
.switch-on .switch-dot {
  left: 18px;
}
</style>
