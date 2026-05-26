<template>
  <Layout>
    <div class="all-page">
      <div class="page-header">
        <div>
          <h1 class="page-title">全部内容</h1>
          <p class="page-subtitle">全量内容时间线</p>
        </div>
        <div class="header-actions">
          <a-button v-if="selectedIds.size > 0" type="primary" size="large" @click="selectAll" :loading="downloading">
            全选
          </a-button>
          <a-button v-if="selectedIds.size > 0" type="primary" size="large" @click="batchDownload" :loading="downloading">
            批量下载 ({{ selectedIds.size }})
          </a-button>
          <a-button v-if="selectedIds.size > 0" size="large" @click="clearSelection">
            取消选择
          </a-button>
        </div>
      </div>

      <div class="category-tabs">
        <span v-for="cat in categories" :key="cat.value" :class="['cat-tab', { active: category === cat.value }]" @click="selectCategory(cat.value)">{{ cat.label }}</span>
      </div>

      <div class="search-bar">
        <a-input v-model="searchQuery" placeholder="搜索标题、摘要、信源..." size="large" @input="debounceSearch">
          <template #prefix><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg></template>
        </a-input>
      </div>

      <div class="filter-controls">
        <div class="filter-group">
          <label class="filter-label">时间范围</label>
          <a-radio-group v-model="timeFilter" type="button" @change="fetchData" size="small">
            <a-radio value="today">今天</a-radio>
            <a-radio value="yesterday">昨天</a-radio>
            <a-radio value="week">近一周</a-radio>
            <a-radio value="all">全部</a-radio>
          </a-radio-group>
        </div>
        <div class="filter-group">
          <label class="filter-label">最低评分</label>
          <a-slider v-model="minScore" :min="0" :max="200" :step="10" show-tooltip style="width:160px;" @change="fetchData" />
        </div>
      </div>

      <div v-if="loading" class="loading-box"><a-spin size="large" /></div>
      <div v-else-if="items.length === 0" class="empty-box"><a-empty description="暂无内容" /></div>
      <div v-else class="timeline-list">
        <div v-for="(group, dateKey) in groupedItems" :key="dateKey">
          <div class="date-header">{{ dateKey }}</div>
          <TimelineCard v-for="item in group" :key="item.id" :item="item" :showReason="false" :isSelected="selectedIds.has(item.id)" @select="toggleSelect" />
        </div>
      </div>
      <div v-if="totalPages > 1" class="pagination">
        <a-button @click="goToPage(1)" :disabled="currentPage === 1 || loading" size="small">首页</a-button>
        <a-button @click="goToPage(currentPage - 1)" :disabled="currentPage === 1 || loading" size="small">上一页</a-button>
        <span class="page-info">第 {{ currentPage }} / {{ totalPages }} 页（共 {{ totalCount }} 条）</span>
        <a-button @click="goToPage(currentPage + 1)" :disabled="currentPage === totalPages || loading" size="small">下一页</a-button>
        <a-button @click="goToPage(totalPages)" :disabled="currentPage === totalPages || loading" size="small">末页</a-button>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref, computed, onMounted, watch, inject } from 'vue'
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
const timeFilter = ref('all')
const minScore = ref(30)
const refreshCounter = inject('refreshCounter', ref(0))

const selectedIds = ref(new Set())
const downloading = ref(false)

let searchTimer = null
const debounceSearch = () => { clearTimeout(searchTimer); searchTimer = setTimeout(() => fetchData(), 300) }
const selectCategory = (val) => { category.value = val; fetchData() }

function toggleSelect(id) {
  if (selectedIds.value.has(id)) selectedIds.value.delete(id)
  else selectedIds.value.add(id)
}

function clearSelection() { selectedIds.value.clear() }

function selectAll() {
  if (selectedIds.value.size === items.value.length) {
    clearSelection()
  } else {
    items.value.forEach(item => selectedIds.value.add(item.id))
  }
}

async function batchDownload() {
  if (selectedIds.value.size === 0) { Message.warning('请先选择要下载的内容'); return }
  // 过滤有效ID
  const validIds = Array.from(selectedIds.value).map(id => Number(id)).filter(id => !isNaN(id) && id > 0)
  if (validIds.length === 0) { Message.warning('选中内容无效，请重新选择'); return }
  if (validIds.length > 100) { Message.warning('单次最多选择100篇内容下载'); return }
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
      if (data.code === 0) Message.info(data.message || '所选内容已全部下载过')
      else Message.error(data.message || '下载失败')
    }
  } catch (e) { Message.error('下载失败：' + e.message) }
  finally { downloading.value = false }
}

const totalPages = computed(() => Math.ceil(totalCount.value / pageSize) || 1)

watch(refreshCounter, () => { fetchData() })

const groupedItems = computed(() => {
  const groups = {}
  items.value.forEach(item => {
    const pubDate = item.publishedAt || item.publish_date || ''
    let dateKey = '今天'
    if (pubDate) {
      try { const dt = new Date(pubDate); const d = Math.floor((Date.now() - dt.getTime()) / 86400000); dateKey = d === 0 ? '今天' : d === 1 ? '昨天' : dt.toLocaleDateString('zh-CN', { month: 'long', day: 'numeric' }) } catch { dateKey = '其他' }
    }
    if (!groups[dateKey]) groups[dateKey] = []
    groups[dateKey].push(item)
  })
  return groups
})

async function fetchData(reset = true) {
  if (reset) { currentPage.value = 1 }
  loading.value = true
  try {
    const params = { page: currentPage.value, size: pageSize, mode: 'all', category: category.value === 'all' ? undefined : category.value, q: searchQuery.value || undefined, min_score: minScore.value, time_filter: timeFilter.value === 'all' ? 'all' : timeFilter.value }
    const { data } = await getList(params)
    const list = data.items || data || []
    totalCount.value = data.total || list.length || 0
    items.value = list
  } catch (err) { console.error('Failed:', err) } finally { loading.value = false }
}
function goToPage(p) {
  if (p < 1 || p > totalPages.value || loading.value) return
  currentPage.value = p
  fetchData(false)
}
onMounted(() => fetchData())
</script>

<style scoped>
.all-page { max-width: 900px; margin: 0 auto; }
.page-header { margin-bottom: 24px; display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.header-actions { display: flex; gap: 8px; flex-shrink: 0; }
.page-title { font-size: 32px; font-weight: 700; margin: 0 0 4px; background: linear-gradient(135deg, #60a5fa, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.page-subtitle { font-size: 13px; color: rgba(255,255,255,0.4); margin: 0; }
.light .page-subtitle { color: rgba(0,0,0,0.4); }
.category-tabs { display: flex; gap: 8px; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid rgba(255,255,255,0.06); }
.light .category-tabs { border-bottom: 1px solid rgba(0,0,0,0.06); }
.cat-tab { padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 500; color: rgba(255,255,255,0.6); cursor: pointer; transition: all 0.2s; white-space: nowrap; }
.light .cat-tab { color: rgba(0,0,0,0.6); }
.cat-tab:hover { background: rgba(99,102,241,0.1); color: #60a5fa; }
.cat-tab.active { background: rgba(99,102,241,0.15); color: #60a5fa; }
.search-bar { margin-bottom: 16px; }
.filter-controls { display: flex; gap: 24px; margin-bottom: 24px; flex-wrap: wrap; align-items: flex-end; }
.filter-group { display: flex; flex-direction: column; gap: 8px; }
.filter-label { font-size: 11px; color: rgba(255,255,255,0.4); text-transform: uppercase; letter-spacing: 0.5px; }
.light .filter-label { color: rgba(0,0,0,0.4); }
.loading-box { display: flex; justify-content: center; padding: 60px; }
.empty-box { padding: 80px 0; text-align: center; }
.timeline-list { display: flex; flex-direction: column; }
.date-header { font-size: 14px; font-weight: 600; color: rgba(255,255,255,0.5); padding: 24px 0 16px; border-top: 1px solid rgba(255,255,255,0.04); }
.light .date-header { color: rgba(0,0,0,0.5); border-top: 1px solid rgba(0,0,0,0.04); }
.load-more { display: flex; justify-content: center; padding: 24px 0; }
</style>
