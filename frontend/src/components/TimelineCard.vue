<template>
  <div class="timeline-card" :class="{ 'card-selected': isSelected }" @click="handleClick">
    <div class="time-column">
      <div class="time-row">
        <span v-if="hasPublishedTime" class="time-dot published-dot"></span>
        <span v-else class="time-dot ingested-dot"></span>
        <div class="time-main">{{ primaryTime }}</div>
      </div>
      <div v-if="showIngestTime" class="time-row time-sub">
        <span class="time-dot secondary-dot"></span>
        <div class="time-text">{{ ingestDisplay }}</div>
      </div>
    </div>
    
    <div class="content-card">
      <div class="card-header">
        <div class="author-info">
          <span class="select-checkbox" :class="{ checked: isSelected }">
            <svg v-if="isSelected" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
          </span>
          <span class="author-name">{{ item.source || '未知信源' }}</span>
          <span v-if="item.source_tier" class="tier-badge" :style="{ background: getTierColor(item.source_tier) }">{{ item.source_tier }}</span>
          <span class="download-dot" :class="{ 'dot-downloaded': isDownloaded, 'dot-not-downloaded': !isDownloaded }"></span>
        </div>
        <div class="score-box">
          <span class="score-value" :style="{ color: scoreColor }">{{ Math.round(item.final_score || 0) }}</span>
          <span class="score-label">分</span>
        </div>
      </div>
      
      <h3 class="title">
        <a :href="item.url || '#'" target="_blank" rel="noopener noreferrer" @click.stop>{{ item.title || '无标题' }}</a>
      </h3>
      
      <p class="summary">{{ truncatedSummary }}</p>
      
      <div v-if="isShortContent" class="content-warning">
        <span class="warning-icon">⚠️</span>
        <span class="warning-text">内容较短，建议查看原文</span>
      </div>
      
      <div class="tags-row">
        <span v-if="item.content_type" class="tag tag-type">{{ item.content_type }}</span>
        <span v-if="item.category" class="tag tag-category">{{ categoryLabel }}</span>
        <span v-for="tag in displayTags" :key="tag" class="tag tag-item">{{ tag }}</span>
      </div>
      
      <div v-if="displayReason" class="recommendation">
        <span class="rec-icon">💡</span>
        <span class="rec-label">推荐理由</span>
        <span class="rec-text">{{ displayReason }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const CATEGORY_MAP = {
  all: '全部',
  'ai-models': '模型',
  'ai-products': '产品',
  industry: '行业',
  paper: '论文',
  tip: '技巧'
}

const props = defineProps({
  item: { type: Object, required: true },
  showReason: { type: Boolean, default: true },
  isDownloaded: { type: Boolean, default: false },
  isSelected: { type: Boolean, default: false }
})

const emit = defineEmits(['select'])

const handleClick = () => {
  emit('select', props.item.id)
}

const categoryLabel = computed(() => CATEGORY_MAP[props.item.category] || props.item.category || '')

const scoreColor = computed(() => {
  const score = props.item.final_score || 0
  if (score >= 110) return '#EF4444'
  if (score >= 100) return '#F59E0B'
  if (score >= 90) return '#3B82F6'
  if (score >= 80) return '#10B981'
  return '#9CA3AF'
})

const truncatedSummary = computed(() => {
  const s = props.item.summary || '暂无摘要'
  return s.length > 200 ? s.slice(0, 200) + '...' : s
})

const isShortContent = computed(() => {
  // 判断内容是否过短（小于200字符）
  const content = props.item.content || props.item.summary || ''
  return content.length < 200
})

const displayTags = computed(() => {
  let tags = props.item.tags
  if (typeof tags === 'string') { try { tags = JSON.parse(tags) } catch { tags = [] } }
  return (tags || []).slice(0, 3)
})

// Time display logic
const publishedAt = computed(() => props.item.publishedAt || props.item.publish_date || '')
const ingestedAt = computed(() => props.item.ingestedAt || props.item.ingested_at || '')

const hasPublishedTime = computed(() => !!publishedAt.value)

// 主时间：优先显示官方发布时间，没有则显示录入时间
const primaryTime = computed(() => {
  if (publishedAt.value) {
    return formatTime(publishedAt.value)
  }
  return formatTime(ingestedAt.value) + ' (录入)'
})

// 副时间：录入时间（当有发布时间时才显示）
const showIngestTime = computed(() => {
  return hasPublishedTime.value && ingestedAt.value
})

const ingestDisplay = computed(() => {
  if (!ingestedAt.value) return ''
  return '录入 ' + formatTime(ingestedAt.value)
})

// 推荐理由：优先用后端返回的（LLM生成的AI HOT风格）
const displayReason = computed(() => {
  return props.showReason ? (props.item.recommendation_reason || null) : null
})

function getTierColor(tier) {
  return { T1: '#EF4444', T2: '#F59E0B', T3: '#6B7280' }[tier] || '#9CA3AF'
}

function formatTime(dateStr) {
  if (!dateStr) return '--'
  try {
    const d = new Date(dateStr)
    const y = d.getFullYear()
    const m = d.getMonth() + 1
    const day = d.getDate()
    return `${y}-${m}-${day}`
  } catch {
    return '--'
  }
}
</script>

<style scoped>
.timeline-card {
  display: flex;
  gap: 16px;
  padding: 16px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  cursor: pointer;
  transition: background 0.15s;
  border-radius: 8px;
  margin: 0 -8px;
  padding: 16px 8px;
}

.timeline-card:hover {
  background: rgba(255, 255, 255, 0.03);
}

.timeline-card.card-selected {
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.2);
}

.light .timeline-card.card-selected {
  background: rgba(99, 102, 241, 0.06);
  border-color: rgba(99, 102, 241, 0.15);
}
.timeline-card:hover { background: rgba(255,255,255,0.02); }
.light .timeline-card { border-bottom: 1px solid rgba(0,0,0,0.04); }
.light .timeline-card:hover { background: rgba(0,0,0,0.02); }

.time-column { min-width: 80px; text-align: right; padding-top: 2px; display: flex; flex-direction: column; gap: 2px; }
.time-row { display: flex; align-items: center; justify-content: flex-end; gap: 6px; }
.time-main { font-size: 14px; font-weight: 600; color: rgba(255,255,255,0.7); line-height: 1.2; }
.light .time-main { color: rgba(0,0,0,0.6); }
.time-sub { margin-top: 2px; }
.time-text { font-size: 10px; color: rgba(255,255,255,0.3); }
.light .time-text { color: rgba(0,0,0,0.3); }
.time-dot { width: 5px; height: 5px; border-radius: 50%; flex-shrink: 0; }
.published-dot { background: #60a5fa; }
.ingested-dot { background: #10B981; }
.secondary-dot { background: rgba(255,255,255,0.2); }
.light .secondary-dot { background: rgba(0,0,0,0.15); }

.content-card { flex: 1; min-width: 0; }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.author-info { display: flex; align-items: center; gap: 8px; }
.author-name { font-size: 12px; font-weight: 500; color: rgba(255,255,255,0.5); }
.light .author-name { color: rgba(0,0,0,0.5); }
.tier-badge {
  color: white;
  padding: 1px 6px;
  border-radius: 8px;
  font-size: 10px;
  font-weight: 600;
}
.select-checkbox {
  width: 16px;
  height: 16px;
  border: 1.5px solid rgba(255, 255, 255, 0.2);
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.15s;
  color: transparent;
}
.select-checkbox.checked {
  background: #6366F1;
  border-color: #6366F1;
  color: white;
}
.light .select-checkbox {
  border-color: rgba(0, 0, 0, 0.15);
}
.download-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dot-downloaded {
  background: #10B981;
  box-shadow: 0 0 6px rgba(16, 185, 129, 0.4);
}
.dot-not-downloaded {
  background: rgba(255, 255, 255, 0.2);
}
.light .dot-not-downloaded {
  background: rgba(0, 0, 0, 0.15);
}
.aihot-badge {
  background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%);
  color: #c22e2e;
  padding: 1px 6px;
  border-radius: 8px;
  font-size: 10px;
  font-weight: 600;
  margin-left: 4px;
}
.score-box { text-align: right; display: flex; align-items: baseline; gap: 2px; }
.score-value { font-size: 18px; font-weight: 700; line-height: 1; }
.score-label { font-size: 11px; color: rgba(255,255,255,0.4); }
.light .score-label { color: rgba(0,0,0,0.4); }

.title { margin: 0 0 8px; font-size: 15px; font-weight: 600; line-height: 1.6; }
.title a { color: rgba(255,255,255,0.9); text-decoration: none; transition: color 0.2s; }
.light .title a { color: #1e293b; }
.title a:hover { color: #60a5fa; }

.summary { color: rgba(255,255,255,0.5); font-size: 13px; line-height: 1.7; margin: 0 0 8px; }
.light .summary { color: rgba(0,0,0,0.5); }

.tags-row { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
.tag { padding: 2px 8px; border-radius: 10px; font-size: 11px; }
.tag-type { background: rgba(99,102,241,0.15); color: #818CF8; }
.tag-category { background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.4); }
.light .tag-category { background: rgba(0,0,0,0.06); color: rgba(0,0,0,0.4); }
.tag-item { background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.5); }
.light .tag-item { background: rgba(0,0,0,0.06); color: rgba(0,0,0,0.5); }

.recommendation { background: rgba(99,102,241,0.06); border-radius: 8px; padding: 8px 12px; margin-top: 8px; color: rgba(255,255,255,0.7); font-size: 12px; line-height: 1.6; display: flex; align-items: flex-start; gap: 6px; }
.rec-icon { font-size: 14px; flex-shrink: 0; }
.rec-label { color: #818CF8; font-weight: 600; white-space: nowrap; }
.rec-text { color: rgba(255,255,255,0.6); }
.light .recommendation { background: rgba(99,102,241,0.04); color: rgba(0,0,0,0.6); }
.light .rec-label { color: #6366F1; }
.light .rec-text { color: rgba(0,0,0,0.5); }

.content-warning {
  background: rgba(255, 193, 7, 0.08);
  border-radius: 6px;
  padding: 6px 10px;
  margin: 8px 0;
  display: flex;
  align-items: center;
  gap: 6px;
}
.warning-icon {
  font-size: 12px;
}
.warning-text {
  font-size: 11px;
  color: #F59E0B;
}
.light .content-warning {
  background: rgba(255, 193, 7, 0.06);
}
</style>
