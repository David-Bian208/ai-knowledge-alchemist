<template>
  <div class="layout">
    <aside class="left-nav">
      <div class="logo-box">
        <div class="logo-text">AI-Pulse</div>
        <div class="logo-subtitle">精选行业动态</div>
      </div>
      <nav class="nav-list">
        <router-link
            v-for="item in navItems"
            :key="item.path"
            :to="item.path"
            class="nav-item"
            :class="{ active: $route.path === item.path }"
          >
            <span class="nav-icon">{{ item.icon }}</span>
            <span class="nav-label">{{ item.label }}</span>
          </router-link>
      </nav>
      <div class="theme-toggle" @click="toggleTheme">
        {{ theme === 'dark' ? '☀️' : '🌙' }}
      </div>
    </aside>
    <main class="right-content">
      <slot />
    </main>
  </div>
</template>

<script setup>
import { inject } from 'vue'

const theme = inject('theme')
const setTheme = inject('setTheme')

const navItems = [
  { path: '/timeline', icon: '', label: '精选内容' },
  { path: '/all', icon: '', label: '全部内容' },
  { path: '/daily', icon: '', label: '每日日报' },
  { path: '/sources', icon: '', label: '信源管理' },
  { path: '/update', icon: '', label: '内容更新' },
  { path: '/download', icon: '', label: '下载设置' },
  { path: '/health', icon: '', label: '信源监控' }
]

const toggleTheme = () => {
  setTheme(theme.value === 'dark' ? 'light' : 'dark')
}
</script>

<style scoped>
.layout {
  display: flex;
  min-height: 100vh;
}

.left-nav {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: 220px;
  background: rgba(15, 23, 42, 0.95);
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  padding: 24px 0;
  z-index: 100;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.light .left-nav {
  background: rgba(248, 250, 252, 0.98);
  border-right: 1px solid rgba(0, 0, 0, 0.06);
}

.logo-box {
  padding: 0 20px 28px;
  text-align: center;
}

.logo-text {
  font-size: 24px;
  font-weight: 700;
  background: linear-gradient(135deg, #60a5fa, #8b5cf6);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 4px;
}

.logo-subtitle {
  font-size: 10px;
  color: rgba(255, 255, 255, 0.4);
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.light .logo-subtitle {
  color: rgba(0, 0, 0, 0.4);
}

.nav-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 0 12px;
  flex: 1;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border-radius: 8px;
  text-decoration: none;
  transition: all 0.2s;
  font-size: 13px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.6);
}

.light .nav-item {
  color: rgba(0, 0, 0, 0.6);
}

.nav-item:hover {
  background: rgba(99, 102, 241, 0.08);
  color: rgba(255, 255, 255, 0.9);
}

.light .nav-item:hover {
  color: rgba(0, 0, 0, 0.9);
}

.nav-item.active {
  background: rgba(99, 102, 241, 0.12);
  color: #60a5fa;
}



.nav-icon {
  font-size: 14px;
  opacity: 0.8;
}

.nav-label {
  white-space: nowrap;
}

.refresh-box {
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.refresh-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.last-update {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.3);
  text-align: center;
}

.light .last-update {
  color: rgba(0, 0, 0, 0.3);
}

.refresh-status {
  font-size: 11px;
  text-align: center;
  display: block;
}

.refresh-status.status-success {
  color: #10B981;
}

.refresh-status.status-error {
  color: #EF4444;
}

.theme-toggle {
  position: fixed;
  bottom: 20px;
  right: 20px;
  background: rgba(30, 41, 59, 0.8);
  backdrop-filter: blur(8px);
  color: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  width: 40px;
  height: 40px;
  font-size: 16px;
  cursor: pointer;
  z-index: 1000;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.light .theme-toggle {
  background: rgba(248, 250, 252, 0.8);
  border: 1px solid rgba(0, 0, 0, 0.08);
  color: rgba(0, 0, 0, 0.7);
}

.theme-toggle:hover {
  transform: scale(1.05);
  background: rgba(99, 102, 241, 0.2);
  color: #60a5fa;
}

.right-content {
  margin-left: 220px;
  padding: 28px 32px;
  min-height: 100vh;
  width: calc(100vw - 220px);
}

@media (max-width: 768px) {
  .left-nav {
    width: 180px;
    padding: 20px 0;
  }
  
  .logo-text {
    font-size: 20px;
  }
  
  .right-content {
    margin-left: 180px;
    padding: 20px;
    width: calc(100vw - 180px);
  }
}

@media (max-width: 576px) {
  .left-nav {
    display: none;
  }
  .right-content {
    margin-left: 0;
    width: 100vw;
    padding: 16px;
  }
}
</style>
