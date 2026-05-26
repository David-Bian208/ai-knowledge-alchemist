import { createRouter, createWebHistory } from 'vue-router'
import Timeline from '../views/Timeline.vue'
import AllDynamics from '../views/AllDynamics.vue'
import Daily from '../views/Daily.vue'
import Sources from '../views/Sources.vue'
import Update from '../views/Update.vue'
import DownloadSettings from '../views/DownloadSettings.vue'
import SourceHealth from '../views/SourceHealth.vue'

const routes = [
  { path: '/', redirect: '/timeline' },
  { path: '/timeline', name: 'timeline', component: Timeline },
  { path: '/all', name: 'all', component: AllDynamics },
  { path: '/daily', name: 'daily', component: Daily },
  { path: '/sources', name: 'sources', component: Sources },
  { path: '/update', name: 'update', component: Update },
  { path: '/download', name: 'download', component: DownloadSettings },
  { path: '/health', name: 'health', component: SourceHealth }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
