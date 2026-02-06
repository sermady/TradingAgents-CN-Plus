<template>
  <div id="app" class="app-container">
    <!-- 网络状态指示器 -->
    <NetworkStatus />

    <!-- 主要内容区域 -->
    <router-view v-slot="{ Component, route }">
      <transition
        :name="(route?.meta?.transition as string) || 'fade'"
        mode="out-in"
        appear
      >
        <keep-alive :include="keepAliveComponents">
          <component :is="Component" :key="route?.fullPath || 'default'" />
        </keep-alive>
      </transition>
    </router-view>

    <!-- 配置向导 -->
    <ConfigWizard
      v-model="showConfigWizard"
      @complete="handleWizardComplete"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import NetworkStatus from '@/components/NetworkStatus.vue'
import axios from 'axios'
import { configApi } from '@/api/config'
import { useNotificationStore } from '@/stores/notifications'
import { useAuthStore } from '@/stores/auth'

// 需要缓存的组件
const keepAliveComponents = computed(() => [
  'Dashboard',
  'StockScreening',
  'AnalysisHistory'
])

// 配置向导
const showConfigWizard = ref(false)

// 检查是否需要显示配置向导
const checkFirstTimeSetup = async () => {
  try {
    // 检查是否已经完成过配置向导
    const wizardCompleted = localStorage.getItem('config_wizard_completed')
    if (wizardCompleted === 'true') {
      return
    }

    // 验证配置完整性
    const response = await axios.get('/api/system/config/validate')
    if (response.data.success) {
      const result = response.data.data

      // 如果有缺少的必需配置，显示配置向导
      if (!result.success && result.missing_required?.length > 0) {
        // 延迟显示，等待页面加载完成
        setTimeout(() => {
          showConfigWizard.value = true
        }, 1000)
      }
    }
  } catch (error) {
    console.error('检查配置失败:', error)
  }
}

// 配置向导完成处理
const handleWizardComplete = async (data: any) => {
  try {
    console.log('配置向导数据:', data)

    // 1. 保存大模型配置
    if (data.llm?.provider && data.llm?.apiKey) {
      try {
        // 先添加厂家（如果不存在）
        const providerMap: Record<string, { name: string; base_url?: string }> = {
          deepseek: { name: 'DeepSeek', base_url: 'https://api.deepseek.com' },
          dashscope: { name: '通义千问', base_url: 'https://dashscope.aliyuncs.com/api/v1' },
          openai: { name: 'OpenAI', base_url: 'https://api.openai.com/v1' },
          google: { name: 'Google Gemini', base_url: 'https://generativelanguage.googleapis.com/v1' }
        }

        const providerInfo = providerMap[data.llm.provider]
        if (providerInfo) {
          // 尝试添加厂家（如果已存在会失败，但不影响后续流程）
          try {
            await configApi.addLLMProvider({
              id: data.llm.provider,
              name: data.llm.provider,
              display_name: providerInfo.name,
              default_base_url: providerInfo.base_url,
              is_active: true,
              supported_features: ['chat', 'completion'] // 添加默认支持的功能
            })
          } catch (e) {
            // 厂家可能已存在，忽略错误
            console.log('厂家可能已存在:', e)
          }

          // 添加大模型配置
          if (data.llm.modelName) {
            await configApi.updateLLMConfig({
              provider: data.llm.provider,
              model_name: data.llm.modelName,
              enabled: true
            })

            // 设置为默认大模型
            await configApi.setDefaultLLM(data.llm.modelName)
          }
        }
      } catch (error) {
        console.error('保存大模型配置失败:', error)
        ElMessage.warning('大模型配置保存失败，请稍后在配置管理中手动配置')
      }
    }

    // 2. 保存数据源配置
    if (data.datasource?.type) {
      try {
        const dsConfig: any = {
          name: data.datasource.type,
          type: data.datasource.type,
          enabled: true
        }

        // 根据数据源类型添加认证信息
        if (data.datasource.type === 'tushare' && data.datasource.token) {
          dsConfig.api_key = data.datasource.token
        } else if (data.datasource.type === 'finnhub' && data.datasource.apiKey) {
          dsConfig.api_key = data.datasource.apiKey
        }

        await configApi.addDataSourceConfig(dsConfig)
        await configApi.setDefaultDataSource(data.datasource.type)
      } catch (error) {
        console.error('保存数据源配置失败:', error)
        ElMessage.warning('数据源配置保存失败，请稍后在配置管理中手动配置')
      }
    }

    // 3. 数据库配置（MongoDB 和 Redis）
    // 注意：数据库配置通常在 .env 文件中，这里只是记录用户的选择
    // 实际的数据库连接需要在后端 .env 文件中配置
    if (data.mongodb || data.redis) {
      console.log('数据库配置（需要在 .env 文件中设置）:', {
        mongodb: data.mongodb,
        redis: data.redis
      })
    }

    // 标记配置向导已完成
    localStorage.setItem('config_wizard_completed', 'true')

    ElMessage.success({
      message: '配置完成！欢迎使用 TradingAgents-CN',
      duration: 3000
    })
  } catch (error) {
    console.error('保存配置失败:', error)
    ElMessage.error('保存配置失败，请稍后重试')
  }
}

// WebSocket 连接管理（在 App 级别管理，避免路由切换导致断开）
const notifStore = useNotificationStore()
const authStore = useAuthStore()

// 生命周期
onMounted(() => {
  console.log('[App] 🚀 应用挂载，初始化 WebSocket 管理...')

  // 检查是否需要显示配置向导
  checkFirstTimeSetup()

  // 🔥 在应用级别建立 WebSocket 连接（避免路由切换导致断开）
  // 只在用户已登录时连接
  if (authStore.isAuthenticated && authStore.token) {
    console.log('[App] ✅ 用户已登录，准备建立 WebSocket 连接')
    // 延迟一点执行，确保其他初始化完成
    setTimeout(() => {
      notifStore.connect()
    }, 100)
  } else {
    console.log('[App] ⏳ 用户未登录，跳过 WebSocket 连接')
  }

  // 监听登录状态变化，自动连接/断开 WebSocket
  watch(() => authStore.isAuthenticated, (isAuthenticated, wasAuthenticated) => {
    console.log(`[App] 👤 登录状态变化: ${wasAuthenticated} -> ${isAuthenticated}`)
    if (isAuthenticated && authStore.token) {
      console.log('[App] ✅ 用户登录成功，建立 WebSocket 连接')
      notifStore.connect()
    } else if (wasAuthenticated && !isAuthenticated) {
      console.log('[App] 👋 用户登出，断开 WebSocket 连接')
      notifStore.disconnect()
    }
  })
})

onUnmounted(() => {
  // 🔥 应用卸载时断开 WebSocket（例如用户关闭浏览器标签）
  notifStore.disconnect()
})
</script>

<style lang="scss">
.app-container {
  min-height: 100vh;
  background-color: var(--el-bg-color-page);
  transition: background-color 0.3s ease;
}

.global-loading {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 9999;
  background: linear-gradient(90deg, #409EFF 0%, #67C23A 100%);
  height: 2px;
}

// 路由过渡动画
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-left-enter-active,
.slide-left-leave-active {
  transition: all 0.3s ease;
}

.slide-left-enter-from {
  transform: translateX(30px);
  opacity: 0;
}

.slide-left-leave-to {
  transform: translateX(-30px);
  opacity: 0;
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s ease;
}

.slide-up-enter-from {
  transform: translateY(30px);
  opacity: 0;
}

.slide-up-leave-to {
  transform: translateY(-30px);
  opacity: 0;
}

// 响应式设计
@media (max-width: 768px) {
  .app-container {
    padding: 0;
  }
}
</style>
