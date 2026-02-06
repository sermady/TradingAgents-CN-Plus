<template>
  <div class="header-actions">
    <!-- 主题切换 -->
    <el-tooltip content="切换主题" placement="bottom">
      <el-button type="text" @click="toggleTheme" class="action-btn">
        <el-icon>
          <Sunny v-if="appStore.isDarkTheme" />
          <Moon v-else />
        </el-icon>
      </el-button>
    </el-tooltip>

    <!-- 全屏切换 -->
    <el-tooltip content="全屏" placement="bottom">
      <el-button type="text" @click="toggleFullscreen" class="action-btn">
        <el-icon><FullScreen /></el-icon>
      </el-button>
    </el-tooltip>

    <!-- 通知 -->
    <el-tooltip content="通知" placement="bottom">
      <el-badge :value="unreadCount" :hidden="unreadCount === 0">
        <el-button type="text" @click="openDrawer" class="action-btn">
          <el-icon><Bell /></el-icon>
        </el-button>
      </el-badge>
    </el-tooltip>

    <!-- 帮助 -->
    <el-tooltip content="帮助" placement="bottom">
      <el-button type="text" @click="showHelp" class="action-btn">
        <el-icon><QuestionFilled /></el-icon>
      </el-button>
    </el-tooltip>

    <!-- 通知抽屉（方案B） -->
    <el-drawer v-model="drawerVisible" direction="rtl" size="360px" :with-header="true" title="消息中心">
      <div class="notif-toolbar">
        <el-segmented v-model="filter" :options="[{label: '全部', value: 'all'}, {label: '未读', value: 'unread'}]" size="small" />
        <el-button size="small" text type="primary" @click="onMarkAllRead" :disabled="unreadCount===0">全部已读</el-button>
      </div>
      <el-scrollbar max-height="calc(100vh - 160px)">
        <el-empty v-if="items.length===0" description="暂无通知" />
        <div v-else class="notif-list">
          <div v-for="n in items" :key="n.id" class="notif-item" :class="{unread: n.status==='unread'}">
            <div class="row">
              <el-tag :type="tagType(n.type)" size="small">{{ typeLabel(n.type) }}</el-tag>
              <span class="time">{{ toLocal(n.created_at) }}</span>
            </div>
            <div class="title" @click="go(n)">{{ n.title }}</div>
            <div class="content" v-if="n.content">{{ n.content }}</div>
            <div class="ops">
              <el-button size="small" text type="primary" @click="go(n)" :disabled="!n.link">查看</el-button>
              <el-button size="small" text @click="onMarkRead(n)" v-if="n.status==='unread'">标记已读</el-button>
            </div>
          </div>
        </div>
      </el-scrollbar>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useAppStore } from '@/stores/app'
import { useNotificationStore } from '@/stores/notifications'
import { useAuthStore } from '@/stores/auth'
import { storeToRefs } from 'pinia'
import {
  Sunny,
  Moon,
  FullScreen,
  Bell,
  QuestionFilled
} from '@element-plus/icons-vue'

const appStore = useAppStore()
const authStore = useAuthStore()
const notifStore = useNotificationStore()
const { unreadCount, items } = storeToRefs(notifStore)
const drawerVisible = ref(false)
const filter = ref<'all' | 'unread'>('all')
let timerCount: any = null
let timerList: any = null

const toggleTheme = () => { appStore.toggleTheme() }
const toggleFullscreen = () => {
  if (document.fullscreenElement) document.exitFullscreen()
  else document.documentElement.requestFullscreen()
}

function openDrawer() {
  drawerVisible.value = true
  notifStore.loadList(filter.value)
}
function onMarkRead(n: any) { notifStore.markRead(n.id) }
function onMarkAllRead() { notifStore.markAllRead() }
function typeLabel(t: string) { return t === 'analysis' ? '分析' : t === 'alert' ? '预警' : '系统' }
function tagType(t: string) { return t === 'analysis' ? 'success' : t === 'alert' ? 'warning' : 'info' }
function toLocal(iso: string) { try { return new Date(iso).toLocaleString() } catch { return iso } }
function go(n: any) { if (n.link) window.open(n.link, '_blank') }

 onMounted(() => {
  // 刷新未读数（一次性）
  notifStore.refreshUnreadCount()
  // 🔥 WebSocket 连接已在 App.vue 中管理，这里不再重复连接
  // notifStore.connect() // 已由 App.vue 统一管理

  // 🔥 优化：只在 WebSocket 未连接时启用轮询作为降级方案
  // 当 WebSocket 连接正常时，完全依赖推送，不进行 HTTP 轮询
  timerCount = setInterval(() => {
    // 只在 WebSocket 未连接时才轮询
    if (!notifStore.wsConnected) {
      notifStore.refreshUnreadCount()
    }
  }, 30000)

  watch(drawerVisible, (v) => {
    if (v) {
      notifStore.loadList(filter.value)
      // 打开通知抽屉时，如果 WebSocket 已连接，不需要轮询列表
      if (!notifStore.wsConnected) {
        timerList = setInterval(() => notifStore.loadList(filter.value), 60000)
      }
    } else if (timerList) {
      clearInterval(timerList)
      timerList = null
    }
  }, { immediate: true })
  watch(filter, () => { if (drawerVisible.value) notifStore.loadList(filter.value) })

  // 🔥 WebSocket 连接状态变化时，控制轮询
  watch(() => notifStore.wsConnected, (connected) => {
    if (connected) {
      console.log('[HeaderActions] WebSocket 已连接，禁用通知轮询，完全依赖推送')
    } else {
      console.log('[HeaderActions] WebSocket 已断开，启用通知轮询作为降级方案')
      // WebSocket 断开时，尝试重新连接（如果用户已登录）
      if (authStore.isAuthenticated && !notifStore.wsConnected) {
        console.log('[HeaderActions] 尝试重新连接 WebSocket')
        notifStore.connect()
      }
    }
  })
})

onUnmounted(() => {
  if (timerCount) clearInterval(timerCount)
  if (timerList) clearInterval(timerList)
  // 🔥 WebSocket 连接由 App.vue 统一管理，这里不再断开
  // 避免路由切换导致 WebSocket 断开
  // notifStore.disconnect() // 已由 App.vue 统一管理
})

function showHelp() {
  window.open('https://mp.weixin.qq.com/s/ppsYiBncynxlsfKFG8uEbw', '_blank')
}
</script>

<style lang="scss" scoped>
.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;

  .action-btn {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;

    .el-icon { font-size: 18px; }
  }
}

/* 通知抽屉样式 */
.notif-toolbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.notif-list { display: flex; flex-direction: column; gap: 12px; }
.notif-item { padding: 10px 8px; border-radius: 8px; border: 1px solid var(--el-border-color-lighter); }
.notif-item.unread { background: var(--el-fill-color-light); }
.notif-item .row { display: flex; align-items: center; justify-content: space-between; font-size: 12px; color: var(--el-text-color-secondary); margin-bottom: 4px; }
.notif-item .title { font-weight: 600; cursor: pointer; margin-bottom: 4px; }
.notif-item .title:hover { text-decoration: underline; }
.notif-item .content { font-size: 12px; color: var(--el-text-color-regular); }
.notif-item .ops { display: flex; gap: 8px; margin-top: 6px; }
</style>
