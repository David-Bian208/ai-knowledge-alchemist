<template>
  <div :class="['app-container', theme]">
    <router-view />
  </div>
</template>

<script setup>
import { ref, provide, onMounted } from 'vue'

const theme = ref('dark')

onMounted(() => {
  const saved = localStorage.getItem('ai-pulse-theme')
  if (saved) theme.value = saved
})

const setTheme = (t) => {
  theme.value = t
  localStorage.setItem('ai-pulse-theme', t)
}

provide('theme', theme)
provide('setTheme', setTheme)

const refreshCounter = ref(0)
provide('refreshCounter', refreshCounter)

const incrementRefreshCounter = () => {
  refreshCounter.value++
}
provide('incrementRefreshCounter', incrementRefreshCounter)
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.app-container {
  min-height: 100vh;
}

.app-container.dark {
  background: linear-gradient(135deg, #0a0f1e 0%, #0f172a 50%, #0a0f1e 100%);
  color: rgba(255, 255, 255, 0.9);
}

.app-container.light {
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 50%, #f8fafc 100%);
  color: #1e293b;
}
</style>
