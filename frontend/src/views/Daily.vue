<template>
  <Layout>
    <div class="daily-page">
      <div class="page-header">
        <h1 class="page-title">每日日报</h1>
        <p class="page-subtitle">每日结构化行业简报</p>
      </div>

      <div class="daily-header">
        <div class="daily-date">
          <span class="daily-year">{{ daily.year }}</span>
          <span class="daily-month">{{ daily.month }}</span>
          <span class="daily-day">{{ daily.day }}</span>
        </div>
        <div class="daily-meta">
          <span class="daily-count">{{ daily.total || 0 }} 条内容</span>
        </div>
        <a-button 
          type="primary" 
          size="large"
          @click="handleGenerate"
          :loading="isGenerating"
        >
          <template #icon v-if="isGenerating"><icon-loading /></template>
          {{ isGenerating ? '生成中...' : '生成日报' }}
        </a-button>
      </div>

      <div v-if="!dailyReady.ready && !loading && !dailyContent" class="daily-hint">
        <a-alert type="info" closable>
          {{ dailyReady.message || '当天精选内容不足10条，无法生成日报' }}
        </a-alert>
      </div>

      <div v-if="loading" class="loading-box"><a-spin size="large" /></div>
      <div v-else-if="!dailyContent" class="empty-box">
        <a-empty description="暂无日报内容" />
      </div>
      <div v-else class="daily-content">
        <!-- Intro / 导语 -->
        <div v-if="dailyContent.lead?.leadParagraph" class="daily-intro">{{ dailyContent.lead.leadParagraph }}</div>

        <!-- Sections by category -->
        <div v-for="section in sections" :key="section.key" class="daily-section">
          <div class="section-header">
            <span class="section-num">{{ section.num }}</span>
            <span class="section-title">{{ section.title }}</span>
            <span class="section-count">{{ section.items.length }}</span>
          </div>
          <div class="section-items">
            <div v-for="item in section.items" :key="item.id" class="daily-item">
              <div class="item-header">
                <span class="item-source">{{ item.source }}</span>
                <span class="item-tier" :style="{ background: getTierColor(item.source_tier) }">{{ item.source_tier }}</span>
                <span class="item-time">{{ formatItemTime(item) }}</span>
                <span class="item-score" :style="{ color: getScoreColor(item.final_score) }">{{ Math.round(item.final_score) }}</span>
              </div>
              <h3 class="item-title"><a :href="item.url || '#'" target="_blank">{{ item.title }}</a></h3>
              <p class="item-summary">{{ item.summary }}</p>
              <div v-if="item.tags && item.tags.length" class="item-tags">
                <span v-for="tag in (typeof item.tags === 'string' ? JSON.parse(item.tags) : item.tags)" :key="tag" class="item-tag">{{ tag }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Date picker -->
      <div class="daily-nav">
        <a-button @click="prevDay" :disabled="!canPrev">← 前一天</a-button>
        <a-date-picker v-model="selectedDate" @change="onDateChange" :style="{ width: '180px' }" />
        <a-button @click="nextDay" :disabled="!canNext">后一天 →</a-button>
      </div>
    </div>
  </Layout>
</template>

<script setup>
import { ref, computed, onMounted, watch, inject } from 'vue'
import Layout from '../components/Layout.vue'
import { getDaily } from '../api'
import { Message, Modal } from '@arco-design/web-vue'
import { IconLoading } from '@arco-design/web-vue/es/icon'

const loading = ref(false)
const dailyContent = ref(null)
const selectedDate = ref(null)
const refreshCounter = inject('refreshCounter', ref(0))
const dailyReady = ref({ ready: false, count: 0, message: '' })
const isGenerating = ref(false)

watch(refreshCounter, () => {
  if (selectedDate.value) {
    const dateStr = selectedDate.value.toISOString().split('T')[0]
    fetchDaily(dateStr)
    checkReady(dateStr)
  }
})

const daily = computed(() => {
  if (!dailyContent.value) return { year: '', month: '', day: '', total: 0 }
  const totalItems = (dailyContent.value.sections || []).reduce((sum, s) => sum + (s.items?.length || 0), 0)
  const d = selectedDate.value || new Date()
  return {
    year: d.getFullYear(),
    month: d.toLocaleDateString('zh-CN', { month: 'long' }),
    day: d.toLocaleDateString('zh-CN', { day: 'numeric', weekday: 'long' }),
    total: totalItems
  }
})

const sectionMap = {
  'ai-models': { num: '01', title: '模型发布/更新', key: 'ai-models' },
  'ai-products': { num: '02', title: '产品发布/更新', key: 'ai-products' },
  'industry': { num: '03', title: '行业动态', key: 'industry' },
  'paper': { num: '04', title: '论文研究', key: 'paper' },
  'tip': { num: '05', title: '技巧与观点', key: 'tip' }
}

const sections = computed(() => {
  if (!dailyContent.value?.sections) return []
  return dailyContent.value.sections.map(s => ({
    num: sectionMap[s.key]?.num || '--',
    title: s.label,
    key: s.key,
    items: (s.items || []).map(item => ({
      ...item,
      source: item.sourceName || '',
      source_tier: item.sourceTier || '',
      category: s.key,
      final_score: item.score || 0
    }))
  }))
})

function getTierColor(tier) { return { T1: '#EF4444', T2: '#F59E0B', T3: '#6B7280' }[tier] || '#9CA3AF' }
function getScoreColor(score) {
  if (score >= 110) return '#EF4444'; if (score >= 100) return '#F59E0B'; if (score >= 90) return '#3B82F6'; if (score >= 80) return '#10B981'; return '#9CA3AF'
}

function formatItemTime(item) {
  const pubDate = item.publishedAt || item.publish_date
  if (pubDate) {
    try {
      const d = new Date(pubDate)
      return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    } catch { return '' }
  }
  return ''
}

async function checkReady(dateStr) {
  try {
    const res = await fetch(`/api/v1/daily/check?date=${dateStr}`)
    const data = await res.json()
    dailyReady.value = data
  } catch (e) {
    dailyReady.value = { ready: false, count: 0, message: '检查失败' }
  }
}

async function handleGenerate() {
  const dateStr = selectedDate.value ? selectedDate.value.toISOString().split('T')[0] : ''
  
  // 如果日报已存在，弹出确认
  if (dailyContent.value) {
    Modal.confirm({
      title: '覆盖更新',
      content: `${dateStr} 的日报已存在，是否覆盖重新生成？`,
      okText: '确认覆盖',
      cancelText: '取消',
      onOk: () => doGenerate(dateStr, true)
    })
  } else {
    doGenerate(dateStr, false)
  }
}

async function doGenerate(dateStr, force) {
  isGenerating.value = true
  try {
    const res = await fetch('/api/v1/daily/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ date: dateStr, force })
    })
    const data = await res.json()
    if (data.code === 0) {
      Message.success(data.message || '日报生成成功')
      await fetchDaily(dateStr)
    } else {
      if (data.exists) {
        Modal.confirm({
          title: '日报已存在',
          content: `${dateStr} 的日报已存在，是否覆盖重新生成？`,
          okText: '确认覆盖',
          cancelText: '取消',
          onOk: () => doGenerate(dateStr, true)
        })
      } else {
        Message.error(data.message || '日报生成失败')
      }
    }
  } catch (e) {
    Message.error('日报生成失败：' + e.message)
  } finally {
    isGenerating.value = false
  }
}

async function fetchDaily(dateStr) {
  loading.value = true
  try {
    const { data } = await getDaily({ date: dateStr })
    dailyContent.value = data
  } catch (err) {
    console.error('Failed to fetch daily:', err)
  } finally { loading.value = false }
}

function onDateChange(val) {
  if (!val) return
  const d = new Date(val)
  const dateStr = d.toISOString().split('T')[0]
  fetchDaily(dateStr)
  checkReady(dateStr)
}

function prevDay() {
  if (!selectedDate.value) return
  const d = new Date(selectedDate.value)
  d.setDate(d.getDate() - 1)
  selectedDate.value = d
  onDateChange(d)
}

function nextDay() {
  if (!selectedDate.value) return
  const d = new Date(selectedDate.value)
  d.setDate(d.getDate() + 1)
  if (d > new Date()) return
  selectedDate.value = d
  onDateChange(d)
}

const canPrev = computed(() => !!selectedDate.value)
const canNext = computed(() => {
  if (!selectedDate.value) return false
  return new Date(selectedDate.value) < new Date()
})

onMounted(() => {
  selectedDate.value = new Date()
  const dateStr = new Date().toISOString().split('T')[0]
  fetchDaily(dateStr)
  checkReady(dateStr)
})
</script>

<style scoped>
.daily-page { max-width: 900px; margin: 0 auto; }
.page-header { margin-bottom: 24px; }
.page-title { font-size: 32px; font-weight: 700; margin: 0 0 4px; background: linear-gradient(135deg, #60a5fa, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.page-subtitle { font-size: 13px; color: rgba(255,255,255,0.4); margin: 0; }
.light .page-subtitle { color: rgba(0,0,0,0.4); }

.daily-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 32px; padding-bottom: 20px; border-bottom: 1px solid rgba(255,255,255,0.06); }
.light .daily-header { border-bottom: 1px solid rgba(0,0,0,0.06); }
.daily-date { display: flex; gap: 12px; align-items: baseline; }
.daily-year { font-size: 14px; color: rgba(255,255,255,0.4); }
.daily-month { font-size: 18px; font-weight: 600; }
.daily-day { font-size: 18px; font-weight: 600; }
.light .daily-year { color: rgba(0,0,0,0.4); }
.daily-meta { font-size: 13px; color: rgba(255,255,255,0.5); }
.light .daily-meta { color: rgba(0,0,0,0.5); }

.daily-hint { margin-bottom: 20px; }

.daily-intro { background: rgba(99,102,241,0.08); border-radius: 12px; padding: 16px 20px; margin-bottom: 24px; font-size: 14px; line-height: 1.8; color: rgba(255,255,255,0.7); border-left: 3px solid #6366F1; }
.light .daily-intro { background: rgba(99,102,241,0.06); color: rgba(0,0,0,0.7); }

.daily-section { margin-bottom: 32px; }
.section-header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 1px solid rgba(255,255,255,0.04); }
.light .section-header { border-bottom: 1px solid rgba(0,0,0,0.04); }
.section-num { font-size: 24px; font-weight: 700; background: linear-gradient(135deg, #10B981, #3B82F6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; }
.section-title { font-size: 18px; font-weight: 600; }
.section-count { font-size: 12px; color: rgba(255,255,255,0.4); background: rgba(255,255,255,0.06); padding: 2px 8px; border-radius: 8px; }
.light .section-count { color: rgba(0,0,0,0.4); background: rgba(0,0,0,0.06); }

.section-items { display: flex; flex-direction: column; gap: 0; }
.daily-item { padding: 16px 0; border-bottom: 1px solid rgba(255,255,255,0.04); }
.light .daily-item { border-bottom: 1px solid rgba(0,0,0,0.04); }
.item-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.item-source { font-size: 12px; color: rgba(255,255,255,0.4); }
.light .item-source { color: rgba(0,0,0,0.4); }
.item-tier { color: white; padding: 1px 6px; border-radius: 8px; font-size: 10px; font-weight: 600; }
.item-time { font-size: 11px; color: rgba(255,255,255,0.3); }
.light .item-time { color: rgba(0,0,0,0.3); }
.item-score { font-size: 14px; font-weight: 700; }
.item-title { margin: 0 0 8px; font-size: 15px; font-weight: 600; line-height: 1.6; }
.item-title a { color: rgba(255,255,255,0.9); text-decoration: none; }
.light .item-title a { color: #1e293b; }
.item-title a:hover { color: #60a5fa; }
.item-summary { color: rgba(255,255,255,0.5); font-size: 13px; line-height: 1.7; margin: 0 0 8px; }
.light .item-summary { color: rgba(0,0,0,0.5); }
.item-tags { display: flex; gap: 6px; flex-wrap: wrap; }
.item-tag { background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.5); padding: 2px 8px; border-radius: 8px; font-size: 11px; }
.light .item-tag { background: rgba(0,0,0,0.06); color: rgba(0,0,0,0.5); }

.daily-nav { display: flex; justify-content: center; gap: 12px; margin-top: 32px; padding-top: 24px; border-top: 1px solid rgba(255,255,255,0.06); }
.light .daily-nav { border-top: 1px solid rgba(0,0,0,0.06); }
.loading-box { display: flex; justify-content: center; padding: 60px; }
.empty-box { padding: 80px 0; text-align: center; }
</style>
