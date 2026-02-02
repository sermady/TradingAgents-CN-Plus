import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { notificationsApi, type NotificationItem } from '@/api/notifications'
import { useAuthStore } from '@/stores/auth'

export const useNotificationStore = defineStore('notifications', () => {
  const items = ref<NotificationItem[]>([])
  const unreadCount = ref(0)
  const loading = ref(false)
  const drawerVisible = ref(false)

  // 🔥 WebSocket 连接状态
  const ws = ref<WebSocket | null>(null)
  const wsConnected = ref(false)
  let wsReconnectTimer: any = null
  let wsReconnectAttempts = 0
  const maxReconnectAttempts = 10  // 增加重连次数
  let isManualDisconnect = false  // 🔥 标记是否手动断开（避免自动重连）
  let connectionStartTime = 0  // 🔥 连接创建时间戳（用于诊断）
  let connectionId = 0  // 🔥 连接ID（用于日志追踪）
  let wsListenerAdded = false  // 🔥 页面生命周期监听是否已添加
  let isConnecting = false  // 🔥 连接状态锁，防止并发连接

  // 连接状态
  const connected = computed(() => wsConnected.value)

  const hasUnread = computed(() => unreadCount.value > 0)

  async function refreshUnreadCount() {
    try {
      const res = await notificationsApi.getUnreadCount()
      unreadCount.value = res?.data?.count ?? 0
    } catch {
      // noop
    }
  }

  async function loadList(status: 'unread' | 'all' = 'all') {
    loading.value = true
    try {
      const res = await notificationsApi.getList({ status, page: 1, page_size: 20 })
      items.value = res?.data?.items ?? []
    } catch {
      items.value = []
    } finally {
      loading.value = false
    }
  }

  async function markRead(id: string) {
    await notificationsApi.markRead(id)
    const idx = items.value.findIndex(x => x.id === id)
    if (idx !== -1) items.value[idx].status = 'read'
    if (unreadCount.value > 0) unreadCount.value -= 1
  }

  async function markAllRead() {
    await notificationsApi.markAllRead()
    items.value = items.value.map(x => ({ ...x, status: 'read' }))
    unreadCount.value = 0
  }

  function addNotification(n: Omit<NotificationItem, 'id' | 'status' | 'created_at'> & { id?: string; created_at?: string; status?: 'unread' | 'read' }) {
    const id = n.id || `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
    const created_at = n.created_at || new Date().toISOString()
    const item: NotificationItem = {
      id,
      title: n.title,
      content: n.content,
      type: n.type,
      status: n.status ?? 'unread',
      created_at,
      link: n.link,
      source: n.source
    }
    items.value.unshift(item)
    if (item.status === 'unread') unreadCount.value += 1
  }

  // 🔥 添加页面生命周期监听（防止连接泄漏）
  function addPageLifecycleListeners() {
    if (wsListenerAdded) return
    wsListenerAdded = true

    // 页面刷新/关闭前发送关闭信号
    window.addEventListener('beforeunload', () => {
      isManualDisconnect = true
      if (ws.value) {
        try { ws.value.close(1000, 'Page unload') } catch {}
      }
    })

    // 页面可见性变化监听（处理休眠场景）
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible' && !ws.value && !isManualDisconnect) {
        // 页面从后台恢复，且连接已断开，尝试重连
        console.log('[WS] 页面恢复可见，尝试重连...')
        connectWebSocket()
      }
    })

    console.log('[WS] 页面生命周期监听已添加')
  }

  // 🔥 连接 WebSocket（优先）
  function connectWebSocket() {
    try {
      // 🔥 防止并发连接 - 如果正在连接中，直接返回
      if (isConnecting) {
        console.log('[WS] 连接正在进行中，跳过本次连接请求')
        return
      }

      // 🔥 如果已有活跃连接，不需要重新连接
      if (ws.value && ws.value.readyState === WebSocket.OPEN) {
        console.log('[WS] 已有活跃连接，无需重复连接')
        return
      }

      // 标记为正在连接
      isConnecting = true

      // 标记为非手动断开（允许自动重连）
      isManualDisconnect = false

      // 若已存在连接但非 OPEN 状态，清理旧连接
      if (ws.value) {
        console.log('[WS] 清理旧连接...')
        try {
          ws.value.close(1000, 'Reconnecting')
        } catch (e) {
          console.warn('[WS] 关闭旧连接失败:', e)
        }
        ws.value = null
      }
      if (wsReconnectTimer) { clearTimeout(wsReconnectTimer); wsReconnectTimer = null }

      const authStore = useAuthStore()
      const token = authStore.token || localStorage.getItem('auth-token') || ''
      if (!token) {
        console.warn('[WS] 未找到 token，无法连接 WebSocket')
        return
      }

      // WebSocket 连接地址
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const host = window.location.host
      const wsUrl = `${wsProtocol}//${host}/api/ws/notifications?token=${encodeURIComponent(token)}`

      connectionId++
      connectionStartTime = Date.now()
      console.log(`[WS] 🔌 创建新连接 #${connectionId} -> ${wsUrl}`)

      const socket = new WebSocket(wsUrl)
      ws.value = socket

      socket.onopen = () => {
        const duration = Date.now() - connectionStartTime
        console.log(`[WS] ✅ 连接成功 #${connectionId} (耗时: ${duration}ms)`)
        wsConnected.value = true
        wsReconnectAttempts = 0
        isConnecting = false  // 🔥 重置连接锁
        // 添加页面生命周期监听
        addPageLifecycleListeners()
      }

      socket.onerror = (error) => {
        console.error(`[WS] ❌ 连接错误 #${connectionId}:`, error)
        isConnecting = false  // 🔥 重置连接锁
      }

      socket.onclose = (event) => {
        const duration = Date.now() - connectionStartTime
        const isManual = isManualDisconnect || event.reason === 'Page unload' || event.reason === 'Reconnecting'
        console.log(
          `[WS] 🔌 连接关闭 #${connectionId}: code=${event.code}, reason="${event.reason}", ` +
          `存活: ${duration}ms, 手动断开: ${isManual}`
        )
        wsConnected.value = false
        ws.value = null
        isConnecting = false  // 🔥 重置连接锁

        // 🔥 关键：手动断开时不重连
        if (isManual) {
          console.log('[WS] 手动断开连接，停止重连')
          return
        }

        // 自动重连（异常断开时）
        if (wsReconnectAttempts < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, wsReconnectAttempts), 30000)
          console.log(`[WS] 🔄 ${delay}ms 后重连 (${wsReconnectAttempts + 1}/${maxReconnectAttempts})`)

          wsReconnectTimer = setTimeout(() => {
            wsReconnectAttempts++
            connectWebSocket()
          }, delay)
        } else {
          console.error('[WS] ⚠️ 达到最大重连次数，停止重连')
        }
      }

      socket.onerror = (error) => {
        console.error(`[WS] ❌ 连接错误 #${connectionId}:`, error)
        wsConnected.value = false
      }

      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          handleWebSocketMessage(message)
        } catch (error) {
          console.error('[WS] 解析消息失败:', error)
        }
      }
    } catch (error) {
      console.error('[WS] 连接失败:', error)
      wsConnected.value = false
    }
  }

  // 处理 WebSocket 消息
  function handleWebSocketMessage(message: any) {
    console.log('[WS] 收到消息:', message)

    switch (message.type) {
      case 'connected':
        console.log('[WS] 连接确认:', message.data)
        break

      case 'notification':
        // 处理通知
        if (message.data && message.data.title && message.data.type) {
          addNotification({
            id: message.data.id,
            title: message.data.title,
            content: message.data.content,
            type: message.data.type,
            link: message.data.link,
            source: message.data.source,
            created_at: message.data.created_at,
            status: message.data.status || 'unread'
          })
        }
        break

      case 'heartbeat':
        // 心跳消息，无需处理
        break

      default:
        console.warn('[WS] 未知消息类型:', message.type)
    }
  }

  // 断开 WebSocket
  function disconnectWebSocket() {
    console.log('[WS] 🔌 手动断开连接...')
    isManualDisconnect = true  // 🔥 标记为手动断开，避免自动重连

    if (wsReconnectTimer) {
      clearTimeout(wsReconnectTimer)
      wsReconnectTimer = null
    }

    if (ws.value) {
      try { 
        ws.value.close(1000, 'Manual disconnect')
        console.log('[WS] 已发送关闭信号')
      } catch (e) {
        console.warn('[WS] 关闭连接失败:', e)
      }
      ws.value = null
    }

    wsConnected.value = false
    wsReconnectAttempts = 0
  }

  // 🔥 连接 WebSocket
  function connect() {
    console.log('[Notifications] 开始连接...')
    connectWebSocket()
  }

  // 🔥 断开 WebSocket
  function disconnect() {
    console.log('[Notifications] 断开连接...')
    disconnectWebSocket()
  }

  function setDrawerVisible(v: boolean) {
    drawerVisible.value = v
  }

  return {
    items,
    unreadCount,
    hasUnread,
    loading,
    drawerVisible,
    connected,
    wsConnected,
    refreshUnreadCount,
    loadList,
    markRead,
    markAllRead,
    addNotification,
    connect,
    disconnect,
    connectWebSocket,
    disconnectWebSocket,
    setDrawerVisible
  }
})
