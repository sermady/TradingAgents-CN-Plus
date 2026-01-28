// Favorites Pinia Store - 自选股状态管理和缓存
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { favoritesApi } from '@/api/favorites'
import { tagsApi } from '@/api/tags'
import type { FavoriteItem } from '@/api/favorites'
import { ElMessage } from 'element-plus'

// 实时行情数据接口
interface QuoteUpdate {
  code: string
  current_price: number
  change_percent: number
  timestamp: string
}

export const useFavoritesStore = defineStore('favorites', () => {
  // ==================== 状态定义 ====================

  // 自选股列表
  const favorites = ref<FavoriteItem[]>([])

  // 实时行情缓存（用于快速更新）
  const quotesCache = ref<Map<string, QuoteUpdate>>(new Map())

  // 用户标签
  const userTags = ref<string[]>([])
  const tagColorMap = ref<Record<string, string>>({})

  // 加载状态
  const loading = ref(false)
  const tagsLoading = ref(false)

  // 实时行情订阅状态
  const quotesSubscribed = ref(false)

  // 缓存时间戳
  const lastFetchTime = ref<number>(0)
  const lastTagsFetchTime = ref<number>(0)

  // 缓存配置（毫秒）
  const CACHE_TTL = 60000 // 1分钟
  const TAGS_CACHE_TTL = 300000 // 5分钟（标签变化较少）

  // ==================== 计算属性 ====================

  // 是否需要刷新自选股数据
  const needsRefresh = computed(() => {
    const now = Date.now()
    return now - lastFetchTime.value > CACHE_TTL
  })

  // 是否需要刷新标签数据
  const needsTagsRefresh = computed(() => {
    const now = Date.now()
    return now - lastTagsFetchTime.value > TAGS_CACHE_TTL
  })

  // A股自选股列表
  const aStockFavorites = computed(() => {
    return favorites.value.filter(item => item.market === 'A股')
  })

  // 港股自选股列表
  const hkStockFavorites = computed(() => {
    return favorites.value.filter(item => item.market === '港股')
  })

  // 美股自选股列表
  const usStockFavorites = computed(() => {
    return favorites.value.filter(item => item.market === '美股')
  })

  // 获取所有自选股代码（用于订阅）
  const allStockCodes = computed(() => {
    return favorites.value.map(item => item.stock_code)
  })

  // ==================== 核心方法 ====================

  /**
   * 获取自选股列表（带缓存）
   * @param force 是否强制刷新
   */
  const fetchFavorites = async (force = false) => {
    // 如果缓存有效且非强制刷新，直接返回缓存
    if (!force && !needsRefresh.value && favorites.value.length > 0) {
      console.log('[FavoritesStore] 使用缓存数据')
      return favorites.value
    }

    loading.value = true
    try {
      console.log('[FavoritesStore] 从服务器获取数据')
      const res = await favoritesApi.list()
      favorites.value = res as FavoriteItem[]
      lastFetchTime.value = Date.now()
      return favorites.value
    } catch (error: any) {
      console.error('[FavoritesStore] 加载自选股失败:', error)
      ElMessage.error(error.message || '加载自选股失败')
      throw error
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取用户标签（带缓存）
   * @param force 是否强制刷新
   */
  const fetchUserTags = async (force = false) => {
    // 如果缓存有效且非强制刷新，直接返回缓存
    if (!force && !needsTagsRefresh.value && userTags.value.length > 0) {
      console.log('[FavoritesStore] 使用标签缓存')
      return { userTags: userTags.value, tagColorMap: tagColorMap.value }
    }

    tagsLoading.value = true
    try {
      console.log('[FavoritesStore] 从服务器获取标签')
      const res = await tagsApi.list()
      const list = res as any[]

      if (Array.isArray(list)) {
        userTags.value = list.map((t: any) => t.name)
        tagColorMap.value = list.reduce((acc: Record<string, string>, t: any) => {
          acc[t.name] = t.color
          return acc
        }, {})
      } else {
        userTags.value = []
        tagColorMap.value = {}
      }

      lastTagsFetchTime.value = Date.now()
      return { userTags: userTags.value, tagColorMap: tagColorMap.value }
    } catch (error) {
      console.error('[FavoritesStore] 加载标签失败:', error)
      userTags.value = []
      tagColorMap.value = {}
      return { userTags: [], tagColorMap: {} }
    } finally {
      tagsLoading.value = false
    }
  }

  /**
   * 添加自选股
   */
  const addFavorite = async (payload: any) => {
    try {
      await favoritesApi.add(payload)

      // 添加成功后，立即刷新缓存
      await fetchFavorites(true)
      ElMessage.success('添加成功')
      return true
    } catch (error: any) {
      console.error('[FavoritesStore] 添加自选股失败:', error)
      ElMessage.error(error.message || '添加失败')
      throw error
    }
  }

  /**
   * 更新自选股
   */
  const updateFavorite = async (code: string, payload: any) => {
    try {
      await favoritesApi.update(code, payload)

      // 更新成功后，立即刷新缓存
      await fetchFavorites(true)
      ElMessage.success('保存成功')
      return true
    } catch (error: any) {
      console.error('[FavoritesStore] 更新自选股失败:', error)
      ElMessage.error(error.message || '保存失败')
      throw error
    }
  }

  /**
   * 删除自选股
   */
  const removeFavorite = async (code: string) => {
    try {
      await favoritesApi.remove(code)

      // 删除成功后，立即刷新缓存
      await fetchFavorites(true)
      ElMessage.success('移除成功')
      return true
    } catch (error: any) {
      console.error('[FavoritesStore] 移除自选股失败:', error)
      ElMessage.error(error.message || '移除失败')
      throw error
    }
  }

  /**
   * 同步实时行情
   */
  const syncRealtime = async (dataSource: 'tushare' | 'akshare' = 'tushare') => {
    if (favorites.value.length === 0) {
      ElMessage.warning('没有自选股需要同步')
      return
    }

    try {
      const data = await favoritesApi.syncRealtime(dataSource)
      ElMessage.success(data.message || `同步完成: 成功 ${data.success_count} 只`)
      // 同步成功后，立即刷新缓存
      await fetchFavorites(true)
    } catch (error: any) {
      console.error('[FavoritesStore] 同步实时行情失败:', error)
      ElMessage.error(error.message || '同步失败，请稍后重试')
      throw error
    }
  }

  /**
   * 处理实时行情更新（来自 WebSocket）
   */
  const handleQuoteUpdate = (update: QuoteUpdate) => {
    // 更新缓存
    quotesCache.value.set(update.code, update)

    // 更新 favorites 列表中的对应项
    const index = favorites.value.findIndex(item => item.stock_code === update.code)
    if (index !== -1) {
      favorites.value[index].current_price = update.current_price
      favorites.value[index].change_percent = update.change_percent

      console.log(`[FavoritesStore] 更新行情: ${update.code} 价格=${update.current_price} 涨跌=${update.change_percent}%`)
    }
  }

  /**
   * 批量处理实时行情更新
   */
  const handleBatchQuoteUpdate = (updates: QuoteUpdate[]) => {
    updates.forEach(update => handleQuoteUpdate(update))
    console.log(`[FavoritesStore] 批量更新 ${updates.length} 只股票行情`)
  }

  /**
   * 订阅实时行情（标记状态）
   */
  const subscribeQuotes = () => {
    quotesSubscribed.value = true
    console.log('[FavoritesStore] 已订阅实时行情')
  }

  /**
   * 取消订阅实时行情
   */
  const unsubscribeQuotes = () => {
    quotesSubscribed.value = false
    quotesCache.value.clear()
    console.log('[FavoritesStore] 已取消订阅实时行情')
  }

  /**
   * 手动使缓存失效
   */
  const invalidateCache = () => {
    lastFetchTime.value = 0
    console.log('[FavoritesStore] 缓存已失效')
  }

  /**
   * 手动使标签缓存失效
   */
  const invalidateTagsCache = () => {
    lastTagsFetchTime.value = 0
    console.log('[FavoritesStore] 标签缓存已失效')
  }

  /**
   * 清空所有缓存
   */
  const clearCache = () => {
    favorites.value = []
    userTags.value = []
    tagColorMap.value = {}
    quotesCache.value.clear()
    lastFetchTime.value = 0
    lastTagsFetchTime.value = 0
    quotesSubscribed.value = false
    console.log('[FavoritesStore] 所有缓存已清空')
  }

  // ==================== 返回 ====================

  return {
    // 状态
    favorites,
    userTags,
    tagColorMap,
    loading,
    tagsLoading,
    quotesSubscribed,
    quotesCache,

    // 计算属性
    needsRefresh,
    needsTagsRefresh,
    aStockFavorites,
    hkStockFavorites,
    usStockFavorites,
    allStockCodes,

    // 方法
    fetchFavorites,
    fetchUserTags,
    addFavorite,
    updateFavorite,
    removeFavorite,
    syncRealtime,
    handleQuoteUpdate,
    handleBatchQuoteUpdate,
    subscribeQuotes,
    unsubscribeQuotes,
    invalidateCache,
    invalidateTagsCache,
    clearCache
  }
})

