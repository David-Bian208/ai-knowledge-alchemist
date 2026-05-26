<template>
  <Layout>
    <div class="timeline-page">
      <div class="page-header">
        <div>
          <h1 class="page-title">精选内容</h1>
          <p class="page-subtitle">AI自动挑选的高价值内容</p>
        </div>
        <div class="header-actions">
          <a-button 
            v-if="items.length > 0"
            type="primary" 
            size="large"
            @click="selectAll"
          >
            {{ selectedIds.size === items.length ? '取消全选' : '全选' }}
          </a-button>
          <a-button 
            v-if="selectedIds.size > 0"
            type="primary" 
            size="large"
            @click="batchDownload"
            :loading="downloading"
          >
            批量下载 ({{ selectedIds.size }})
          </a-button>
          <a-button 
            v-if="selectedIds.size > 0"
            size="large"
            @click="clearSelection"
          >
            取消选择
          </a-button>
        </div>
      </div>

      <div class="category-tabs">
        <span 
          v-for="cat in categories" 
          :key="cat.value"
          :class="['cat-tab', { active: category === cat.value }]"
          @click="selectCategory(cat.value)"
        >
          {{ cat.label }}
        </span>
      </div>

      <div class="search-bar">
        <a-input
          v-model="searchQuery"
          placeholder="搜索标题、摘要、信源..."
          size="large"
          class="search-input"
          @input="debounceSearch"
        >
          <template #prefix>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"></circle>
              <path d="m21 21-4.35-4.35"></path>
            </svg>
          </template>
        </a-input>
      </div>

      <div class="filter-controls">
        <div class="filter-group">
          <label class="filter-label">时间范围（按发布时间）</label>
          <a-radio-group v-model="timeFilter" type="button" @change="fetchData" size="small">
            <a-radio value="today">今天</a-radio>
            <a-radio value="yesterday">昨天</a-radio>
            <a-radio value="week">本周</a-radio>
            <a-radio value="custom">自定义</a-radio>
          </a-radio-group>
          <div v-if="timeFilter === 'custom'" class="custom-date-range">
            <a-date-picker v-model="customStart" :style="{ width: '150px' }" placeholder="开始日期" @change="fetchData" />
            <span class="date-sep">至</span>
            <a-date-picker v-model="customEnd" :style="{ width: '150px' }" placeholder="结束日期" @change="fetchData" />
          </div>
        </div>

        <div class="filter-group">
          <label class="filter-label">信源等级</label>
          <a-radio-group v-model="tierFilter" type="button" @change="fetchData" size="small">
            <a-radio value="all">全部</a-radio>
            <a-radio value="T1">T1 核心</a-radio>
            <a-radio value="T2">T2 重要</a-radio>
            <a-radio value="T3">T3 一般</a-radio>
          </a-radio-group>
        </div>
      </div>

      <div v-if="loading" class="loading-box">
        <a-spin size="large" />
      </div>

      <div v-else-if="items.length === 0" class="empty-box">
        <a-empty description="暂无精选内容" />
      </div>

      <div v-else class="timeline-list">
        <div v-for="(group, dateKey) in groupedItems" :key="dateKey">
          <div class="date-header">{{ dateKey }}</div>
          <TimelineCard 
            v-for="item in group" 
            :key="item.id" 
            :item="item"
            :isSelected="selectedIds.has(item.id)"
            @select="toggleSelect"
          />
        </div>
      </div>

      <div v-if="totalPages > 1" class="pagination">
        <a-button 
          @click="goToPage(1)" 
          :disabled="currentPage === 1 || loading"
          size="small"
        >
          首页
        </a-button>
        <a-button 
          @click="goToPage(currentPage - 1)" 
          :disabled="currentPage === 1 || loading"
          size="small"
        >
          上一页
        </a-button>
        <span class="page-info">第 {{ currentPage }} / {{ totalPages }} 页（共 {{ totalCount }} 条）</span>
        <a-button 
          @click="goToPage(currentPage + 1)" 
          :disabled="currentPage === totalPages || loading"
          size="small"
        >
          下一页
        </a-button>
        <a-button 
          @click="goToPage(totalPages)" 
          :disabled="currentPage === totalPages || loading"
          size="small"
        >
          末页
        </a-button>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, inject, watch } from 'vue'
import Layout from '../components/Layout.vue'
import TimelineCard from '../components/TimelineCard.vue'
import { getList } from '../api'
import { Message } from '@arco-design/web-vue'

const categories = [
  { value: 'all', label: '全部' },
  { value: 'ai-models', label: '模型' },
  { value: 'ai-products', label: '产品' },
  { value: 'industry', label: '行业' },
  { value: 'paper', label: '论文' },
  { value: 'tip', label: '技巧' }
]

const items = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = 50
const totalCount = ref(0)

const searchQuery = ref('')
const category = ref('all')
const timeFilter = ref('week')
const tierFilter = ref('all')
const customStart = ref('')
const customEnd = ref('')

const refreshCounter = inject('refreshCounter', ref(0))
const downloadStatuses = ref({})

let searchTimer = null
const debounceSearch = () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    fetchData()
  }, 300)
}

const selectCategory = (val) => {
  category.value = val
  fetchData()
}

// 下载选择
const selectedIds = ref(new Set())
const downloading = ref(false)

function toggleSelect(id) {
  if (selectedIds.value.has(id)) {
    selectedIds.value.delete(id)
  } else {
    selectedIds.value.add(id)
  }
}

function clearSelection() {
  selectedIds.value.clear()
}

function selectAll() {
  if (selectedIds.value.size === items.value.length) {
    clearSelection()
  } else {
    items.value.forEach(item => selectedIds.value.add(item.id))
  }
}

async function batchDownload() {
  if (selectedIds.value.size === 0) {
    Message.warning('请先选择要下载的内容')
    return
  }
  // 过滤有效ID（确保都是数字）
  const validIds = Array.from(selectedIds.value)
    .map(id => Number(id))
    .filter(id => !isNaN(id) && id > 0)
  if (validIds.length === 0) {
    Message.warning('选中内容无效，请重新选择')
    return
  }
  if (validIds.length > 100) {
    Message.warning('单次最多选择100篇内容下载')
    return
  }
  
  downloading.value = true
  try {
    const res = await fetch('/api/v1/download/zip', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ article_ids: validIds })
    })
    
    const contentType = res.headers.get('content-type')
    if (contentType && (contentType.includes('application/zip') || contentType.includes('text/markdown'))) {
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      // 获取文件名
      const disposition = res.headers.get('content-disposition') || ''
      let fileName = `ai_pulse_${new Date().toISOString().slice(0, 10)}`
      if (disposition.includes("UTF-8''")) {
        const encoded = disposition.split("UTF-8''")[1]
        if (encoded) fileName = decodeURIComponent(encoded)
      } else if (disposition.includes('filename="')) {
        fileName = disposition.split('filename="')[1].split('"')[0]
      } else if (contentType.includes('text/markdown')) {
        fileName = `${validIds[0]}_content.md`
      }
      a.download = fileName
      a.click()
      URL.revokeObjectURL(url)
      Message.success('下载已开始')
      clearSelection()
    } else {
      const data = await res.json()
      if (data.code === 0) {
        Message.info(data.message || '所选内容已全部下载过')
      } else {
        Message.error(data.message || '下载失败')
      }
    }
  } catch (e) {
    Message.error('下载失败：' + e.message)
  } finally {
    downloading.value = false
  }
}

const totalPages = computed(() => Math.ceil(totalCount.value / pageSize) || 1)

const groupedItems = computed(() => {
  const groups = {}
  const itemCount = items.value.length
  for (let i = 0; i < itemCount; i++) {
    const item = items.value[i]
    const pubDate = item.publishedAt || item.publish_date || ''
    let dateKey = '今天'
    if (pubDate) {
      try {
        const dt = new Date(pubDate)
        const delta = Math.floor((Date.now() - dt.getTime()) / (1000 * 60 * 60 * 24))
        if (delta === 0) dateKey = '今天'
        else if (delta === 1) dateKey = '昨天'
        else dateKey = dt.toLocaleDateString('zh-CN', { month: 'long', day: 'numeric' })
      } catch {
        dateKey = '其他'
      }
    }
    if (!groups[dateKey]) groups[dateKey] = []
    groups[dateKey].push(item)
  }
  return groups
})

function getFlatItemsWithKeys() {
  const groups = groupedItems.value
  const result = []
  let counter = 0
  for (const [dateKey, groupItems] of Object.entries(groups)) {
    result.push({ uniqueKey: `date-${dateKey}-${counter++}`, type: 'date', label: dateKey })
    for (const item of groupItems) {
      result.push({ uniqueKey: `item-${item.id}-${counter++}`, type: 'card', data: item })
    }
  }
  return result
}

function getGroupedItems() {
  return groupedItems.value
}

async function fetchData(reset = true) {
  if (reset) {
    currentPage.value = 1
  }
  loading.value = true
  try {
    const params = {
      page: currentPage.value,
      size: pageSize,
      category: category.value === 'all' ? undefined : category.value,
      q: searchQuery.value || undefined,
      time_filter: timeFilter.value === 'custom' ? 'custom' : timeFilter.value
    }
    
    // 自定义时间范围
    if (timeFilter.value === 'custom') {
      if (customStart.value) params.date_start = customStart.value
      if (customEnd.value) params.date_end = customEnd.value
    }
    
    const response = await getList(params)
    const list = response.data.items || response.data || []
    totalCount.value = response.data.total || list.length || 0
    
    let filtered = list
    if (tierFilter.value !== 'all') {
      filtered = filtered.filter(i => i.source_tier === tierFilter.value)
    }
    
    items.value = filtered
  } catch (err) {
    console.error('Failed to fetch items:', err)
  } finally {
    loading.value = false
  }
}

function goToPage(p) {
  if (p < 1 || p > totalPages.value || loading.value) return
  currentPage.value = p
  fetchData(false)
}

watch(refreshCounter, () => {
  fetchData()
})

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.timeline-page {
  max-width: 900px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.header-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
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

.light .page-subtitle {
  color: rgba(0, 0, 0, 0.4);
}

.category-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.light .category-tabs {
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.cat-tab {
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.light .cat-tab {
  color: rgba(0, 0, 0, 0.6);
}

.cat-tab:hover {
  background: rgba(99, 102, 241, 0.1);
  color: #60a5fa;
}

.cat-tab.active {
  background: rgba(99, 102, 241, 0.15);
  color: #60a5fa;
}

.search-bar {
  margin-bottom: 16px;
}

.filter-controls {
  display: flex;
  gap: 24px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.custom-date-range {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.date-sep {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
}

.filter-label {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.4);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.light .filter-label {
  color: rgba(0, 0, 0, 0.4);
}

.loading-box {
  display: flex;
  justify-content: center;
  padding: 60px;
}

.empty-box {
  padding: 80px 0;
  text-align: center;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px 0;
}

.page-info {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
  margin: 0 8px;
}

.light .page-info {
  color: rgba(0, 0, 0, 0.5);
}

.timeline-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.date-header {
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.5);
  padding: 24px 0 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.04);
}

.light .date-header {
  color: rgba(0, 0, 0, 0.5);
  border-top: 1px solid rgba(0, 0, 0, 0.04);
}

.load-more {
  display: flex;
  justify-content: center;
  padding: 24px 0;
}
</style>
