import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 10000,
  headers: {
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache'
  }
})

// 获取内容列表
export function getList(params = {}) {
  params._t = Date.now() // 防缓存时间戳
  return api.get('/list', { params })
}

// 获取日报列表
export function getDaily(params = {}) {
  return api.get('/daily', { params })
}

// 获取内容详情
export function getDetail(id) {
  return api.get(`/detail/${id}`)
}

// 获取信源列表
export function getSources() {
  return api.get('/sources')
}

// 获取失效信源列表
export function getUnhealthySources() {
  return api.get('/sources/unhealthy')
}

// 删除信源
export function deleteSource(sourceId) {
  return api.delete(`/sources/${sourceId}`)
}

// 批量删除失效信源
export function deleteUnhealthySources() {
  return api.delete('/sources/unhealthy')
}

// 批量启用所有禁用信源
export function batchEnableAllSources() {
  return api.post('/sources/batch-enable')
}

// ========== 信源健康监控 API ==========

// 获取健康统计
export function getHealthStats() {
  return api.get('/health/stats')
}

// 获取所有信源健康状态
export function getAllSourceHealth() {
  return api.get('/health/sources')
}

// 获取健康日志
export function getHealthLogs(params = {}) {
  return api.get('/health/logs', { params })
}

// 手动检测信源
export function checkSourceHealth(sourceId) {
  return api.post(`/health/check/${sourceId}`)
}

// 批量生成推荐理由
export function batchGenerateReasons() {
  return api.post('/reasons/batch')
}

// 为单条内容生成推荐理由
export function generateReason(id) {
  return api.post(`/reason/${id}`)
}

export default api
