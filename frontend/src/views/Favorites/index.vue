<template>
  <div class="favorites">
    <div class="page-header">
      <h1 class="page-title">
        <el-icon><Star /></el-icon>
        我的自选股
      </h1>
      <p class="page-description">
        管理您关注的股票
      </p>
    </div>

    <!-- 操作栏 -->
    <el-card class="action-card" shadow="never">
      <el-row :gutter="16" align="middle" style="margin-bottom: 16px;">
        <el-col :span="8">
          <el-input
            v-model="searchKeyword"
            placeholder="搜索股票代码或名称"
            clearable
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-col>

        <el-col :span="4">
          <el-select v-model="selectedMarket" placeholder="市场" clearable>
            <el-option label="A股" value="A股" />
            <el-option label="港股" value="港股" />
            <el-option label="美股" value="美股" />
          </el-select>
        </el-col>

        <el-col :span="4">
          <el-select v-model="selectedBoard" placeholder="板块" clearable>
            <el-option label="主板" value="主板" />
            <el-option label="创业板" value="创业板" />
            <el-option label="科创板" value="科创板" />
            <el-option label="北交所" value="北交所" />
          </el-select>
        </el-col>

        <el-col :span="4">
          <el-select v-model="selectedExchange" placeholder="交易所" clearable>
            <el-option label="上海证券交易所" value="上海证券交易所" />
            <el-option label="深圳证券交易所" value="深圳证券交易所" />
            <el-option label="北京证券交易所" value="北京证券交易所" />
          </el-select>
        </el-col>

        <el-col :span="4">
          <el-select v-model="selectedTag" placeholder="标签" clearable>
            <el-option
              v-for="tag in userTags"
              :key="tag"
              :label="tag"
              :value="tag"
            />
          </el-select>
        </el-col>
      </el-row>

      <el-row :gutter="16" align="middle">
        <el-col :span="24">
          <div class="action-buttons">
            <el-button @click="refreshData">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <!-- 只有有A股自选股时才显示同步实时行情按钮 -->
            <el-button
              v-if="hasAStocks"
              type="success"
              @click="syncAllRealtime"
              :loading="syncRealtimeLoading"
            >
              <el-icon><Refresh /></el-icon>
              同步实时行情
            </el-button>
            <!-- 只有选中的股票都是A股时才显示批量同步按钮 -->
            <el-button
              v-if="selectedStocksAreAllAShares"
              type="primary"
              @click="showBatchSyncDialog"
            >
              <el-icon><Download /></el-icon>
              批量同步数据
            </el-button>
            <el-button @click="openTagManager">
              标签管理
            </el-button>
            <el-button type="primary" @click="showAddDialog">
              <el-icon><Plus /></el-icon>
              添加自选股
            </el-button>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 自选股列表 -->
    <el-card class="favorites-list-card" shadow="never">
      <!-- 加载状态 -->
      <div v-if="loading" v-loading="loading" style="min-height: 400px;"></div>

      <!-- 虚拟滚动表格 -->
      <FavoritesVirtualTable
        v-else-if="filteredFavorites.length > 0"
        :data="filteredFavorites"
        :selected-stocks="selectedStocks"
        :tag-color-map="tagColorMap"
        @selection-change="handleSelectionChange"
        @view-detail="viewStockDetail"
        @edit="editFavorite"
        @sync="showSingleSyncDialog"
        @analyze="analyzeFavorite"
        @remove="removeFavorite"
      />

      <!-- 空状态 -->
      <div v-else class="empty-state">
        <el-empty description="暂无自选股">
          <el-button type="primary" @click="showAddDialog">
            添加第一只自选股
          </el-button>
        </el-empty>
      </div>
    </el-card>

    <!-- 添加自选股对话框 -->
    <AddStockDialog
      v-model="addDialogVisible"
      :user-tags="userTags"
      :tag-color-map="tagColorMap"
      @success="handleAddFavorite"
    />

    <!-- 编辑自选股对话框 -->
    <EditStockDialog
      ref="editDialogRef"
      v-model="editDialogVisible"
      :user-tags="userTags"
      :tag-color-map="tagColorMap"
      :loading="editLoading"
      @submit="handleUpdateFavorite"
    />

    <!-- 标签管理对话框 -->
    <TagManagerDialog
      v-model="tagDialogVisible"
      :tag-list="tagList"
      :loading="tagLoading"
      @create="handleCreateTag"
      @edit="handleEditTag"
      @save="handleSaveTag"
      @delete="handleDeleteTag"
      @cancel-edit="handleCancelEditTag"
    />

    <!-- 批量同步对话框 -->
    <BatchSyncDialog
      ref="batchSyncDialogRef"
      v-model="batchSyncDialogVisible"
      :selected-count="selectedStocks.length"
      :loading="batchSyncLoading"
      @submit="handleBatchSync"
    />

    <!-- 单个股票同步对话框 -->
    <SingleSyncDialog
      ref="singleSyncDialogRef"
      v-model="singleSyncDialogVisible"
      :current-stock="currentSyncStock"
      :loading="singleSyncLoading"
      @submit="handleSingleSync"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'
import {
  Star,
  Search,
  Refresh,
  Plus,
  Download
} from '@element-plus/icons-vue'
import { favoritesApi } from '@/api/favorites'
import { tagsApi } from '@/api/tags'
import { stockSyncApi } from '@/api/stockSync'
import { normalizeMarketForAnalysis } from '@/utils/market'
import type { FavoriteItem } from '@/api/favorites'
import { useAuthStore } from '@/stores/auth'
import { useFavoritesStore } from '@/stores/favorites'

// 导入子组件
import AddStockDialog from './components/AddStockDialog.vue'
import EditStockDialog from './components/EditStockDialog.vue'
import TagManagerDialog from './components/TagManagerDialog.vue'
import BatchSyncDialog from './components/BatchSyncDialog.vue'
import SingleSyncDialog from './components/SingleSyncDialog.vue'
import FavoritesVirtualTable from './components/FavoritesVirtualTable.vue'

const router = useRouter()

// 使用 Favorites Store（缓存 + 实时行情）
const favoritesStore = useFavoritesStore()
const { favorites, userTags, tagColorMap, loading, tagsLoading } = storeToRefs(favoritesStore)

const searchKeyword = ref('')
const selectedTag = ref('')
const selectedMarket = ref('')
const selectedBoard = ref('')
const selectedExchange = ref('')

// 批量选择
const selectedStocks = ref<FavoriteItem[]>([])

// 对话框状态
const addDialogVisible = ref(false)
const editDialogVisible = ref(false)
const tagDialogVisible = ref(false)
const batchSyncDialogVisible = ref(false)
const singleSyncDialogVisible = ref(false)

// 加载状态
const editLoading = ref(false)
const tagLoading = ref(false)
const batchSyncLoading = ref(false)
const singleSyncLoading = ref(false)
const syncRealtimeLoading = ref(false)

// 对话框引用
const editDialogRef = ref()
const batchSyncDialogRef = ref()
const singleSyncDialogRef = ref()

// 标签管理
const tagList = ref<any[]>([])

// 单个股票同步
const currentSyncStock = ref({
  stock_code: '',
  stock_name: ''
})

// 计算属性
const filteredFavorites = computed<FavoriteItem[]>(() => {
  let result: FavoriteItem[] = favorites.value

  // 关键词搜索
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter((item: FavoriteItem) =>
      item.stock_code.toLowerCase().includes(keyword) ||
      item.stock_name.toLowerCase().includes(keyword)
    )
  }

  // 市场筛选
  if (selectedMarket.value) {
    result = result.filter((item: FavoriteItem) =>
      item.market === selectedMarket.value
    )
  }

  // 板块筛选
  if (selectedBoard.value) {
    result = result.filter((item: FavoriteItem) =>
      item.board === selectedBoard.value
    )
  }

  // 交易所筛选
  if (selectedExchange.value) {
    result = result.filter((item: FavoriteItem) =>
      item.exchange === selectedExchange.value
    )
  }

  // 标签筛选
  if (selectedTag.value) {
    result = result.filter((item: FavoriteItem) =>
      (item.tags || []).includes(selectedTag.value)
    )
  }

  return result
})

// 判断是否有A股自选股
const hasAStocks = computed(() => {
  return favorites.value.some(item => item.market === 'A股')
})

// 判断选中的股票是否都是A股
const selectedStocksAreAllAShares = computed(() => {
  if (selectedStocks.value.length === 0) return false
  return selectedStocks.value.every(item => item.market === 'A股')
})

// 数据加载方法（使用 Store）
const loadFavorites = async (force = false) => {
  await favoritesStore.fetchFavorites(force)
}

const loadUserTags = async (force = false) => {
  await favoritesStore.fetchUserTags(force)
}

const loadTagList = async () => {
  tagLoading.value = true
  try {
    const res = await tagsApi.list()
    tagList.value = (res as any)?.data || []
  } catch (e) {
    console.error('加载标签列表失败:', e)
  } finally {
    tagLoading.value = false
  }
}

// 同步实时行情（使用 Store）
const syncAllRealtime = async () => {
  if (favorites.value.length === 0) {
    ElMessage.warning('没有自选股需要同步')
    return
  }

  syncRealtimeLoading.value = true
  try {
    await favoritesStore.syncRealtime('tushare')
  } catch (error: any) {
    console.error('同步实时行情失败:', error)
    ElMessage.error(error.message || '同步失败，请稍后重试')
  } finally {
    syncRealtimeLoading.value = false
  }
}

// 刷新数据（强制刷新，跳过缓存）
const refreshData = () => {
  loadFavorites(true)  // force = true
  loadUserTags(true)   // force = true
}

// 显示添加对话框
const showAddDialog = () => {
  addDialogVisible.value = true
}

// 处理添加自选股（使用 Store）
const handleAddFavorite = async (formData: any) => {
  try {
    if (!formData) return

    const payload = { ...formData }
    await favoritesStore.addFavorite(payload as any)
    addDialogVisible.value = false
  } catch (error: any) {
    console.error('添加自选股失败:', error)
    // Store 已经显示错误消息，这里不需要重复
  }
}

// 编辑自选股
const editFavorite = (row: any) => {
  const form = editDialogRef.value?.form
  if (form) {
    form.stock_code = row.stock_code
    form.stock_name = row.stock_name
    form.market = row.market || 'A股'
    form.tags = Array.isArray(row.tags) ? [...row.tags] : []
    form.notes = row.notes || ''
  }
  editDialogVisible.value = true
}

// 处理更新自选股（使用 Store）
const handleUpdateFavorite = async () => {
  try {
    const form = editDialogRef.value?.form
    if (!form) return

    editLoading.value = true
    const payload = {
      tags: form.tags,
      notes: form.notes
    }
    await favoritesStore.updateFavorite(form.stock_code, payload as any)
    editDialogVisible.value = false
  } catch (error: any) {
    console.error('更新自选股失败:', error)
    // Store 已经显示错误消息，这里不需要重复
  } finally {
    editLoading.value = false
  }
}

// 分析自选股
const analyzeFavorite = (row: any) => {
  router.push({
    name: 'SingleAnalysis',
    query: { stock: row.stock_code, market: normalizeMarketForAnalysis(row.market || 'A股') }
  })
}

// 移除自选股（使用 Store）
const removeFavorite = async (row: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要从自选股中移除 ${row.stock_name} 吗？`,
      '确认移除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    await favoritesStore.removeFavorite(row.stock_code)
  } catch (e) {
    // 用户取消或失败（Store 已处理错误消息）
  }
}

// 查看股票详情
const viewStockDetail = (row: any) => {
  router.push({
    name: 'StockDetail',
    params: { code: String(row.stock_code || '').toUpperCase() }
  })
}

// 处理表格选择变化
const handleSelectionChange = (selection: FavoriteItem[]) => {
  selectedStocks.value = selection
}

// 标签管理方法
const openTagManager = async () => {
  tagDialogVisible.value = true
  await loadTagList()
}

const handleCreateTag = async (tag: any) => {
  if (!tag.name || !tag.name.trim()) {
    ElMessage.warning('请输入标签名')
    return
  }
  tagLoading.value = true
  try {
    await tagsApi.create({ ...tag })
    ElMessage.success('创建成功')
    await loadTagList()
    await loadUserTags()
  } catch (e: any) {
    console.error('创建标签失败:', e)
    ElMessage.error(e?.message || '创建失败')
  } finally {
    tagLoading.value = false
  }
}

const handleEditTag = (row: any) => {
  row._editing = true
  row._name = row.name
  row._color = row.color
  row._sort = row.sort_order
}

const handleCancelEditTag = (row: any) => {
  row._editing = false
}

const handleSaveTag = async (row: any) => {
  tagLoading.value = true
  try {
    await tagsApi.update(row.id, {
      name: row._name ?? row.name,
      color: row._color ?? row.color,
      sort_order: row._sort ?? row.sort_order,
    })
    ElMessage.success('保存成功')
    row._editing = false
    await loadTagList()
    await loadUserTags()
  } catch (e: any) {
    console.error('保存标签失败:', e)
    ElMessage.error(e?.message || '保存失败')
  } finally {
    tagLoading.value = false
  }
}

const handleDeleteTag = async (row: any) => {
  try {
    await ElMessageBox.confirm(`确定删除标签 ${row.name} 吗？`, '删除标签', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    tagLoading.value = true
    await tagsApi.remove(row.id)
    ElMessage.success('已删除')
    await loadTagList()
    await loadUserTags()
  } catch (e) {
    // 用户取消或失败
  } finally {
    tagLoading.value = false
  }
}

// 批量同步方法
const showBatchSyncDialog = () => {
  if (selectedStocks.value.length === 0) {
    ElMessage.warning('请先选择要同步的股票')
    return
  }
  batchSyncDialogVisible.value = true
}

const handleBatchSync = async () => {
  const form = batchSyncDialogRef.value?.form
  if (!form) return

  if (form.syncTypes.length === 0) {
    ElMessage.warning('请至少选择一种同步内容')
    return
  }

  batchSyncLoading.value = true
  try {
    const symbols = selectedStocks.value.map(stock => stock.stock_code)

    const res = await stockSyncApi.syncBatch({
      symbols,
      sync_historical: form.syncTypes.includes('historical'),
      sync_financial: form.syncTypes.includes('financial'),
      data_source: form.dataSource,
      days: form.days
    }) as any

    if (res.success) {
      const data = res.data
      let message = `批量同步完成 (共 ${symbols.length} 只股票)\n`

      if (data.historical_sync) {
        message += `✅ 历史数据: ${data.historical_sync.success_count}/${data.historical_sync.success_count + data.historical_sync.error_count} 成功，共 ${data.historical_sync.total_records} 条记录\n`
      }

      if (data.financial_sync) {
        message += `✅ 财务数据: ${data.financial_sync.success_count}/${data.financial_sync.total_symbols} 成功\n`
      }

      if (data.basic_sync) {
        message += `✅ 基础数据: ${data.basic_sync.success_count}/${data.basic_sync.total_symbols} 成功\n`
      }

      ElMessage.success(message)
      batchSyncDialogVisible.value = false
      await loadFavorites()
    } else {
      ElMessage.error((res as any).message || '批量同步失败')
    }
  } catch (error: any) {
    console.error('批量同步失败:', error)
    ElMessage.error(error.message || '批量同步失败，请稍后重试')
  } finally {
    batchSyncLoading.value = false
  }
}

// 单个股票同步方法
const showSingleSyncDialog = (row: FavoriteItem) => {
  currentSyncStock.value = {
    stock_code: row.stock_code,
    stock_name: row.stock_name
  }
  singleSyncDialogVisible.value = true
}

const handleSingleSync = async () => {
  const form = singleSyncDialogRef.value?.form
  if (!form) return

  if (form.syncTypes.length === 0) {
    ElMessage.warning('请至少选择一种同步内容')
    return
  }

  singleSyncLoading.value = true
  try {
    const res = await stockSyncApi.syncSingle({
      symbol: currentSyncStock.value.stock_code,
      sync_realtime: form.syncTypes.includes('realtime'),
      sync_historical: form.syncTypes.includes('historical'),
      sync_financial: form.syncTypes.includes('financial'),
      data_source: form.dataSource,
      days: form.days
    }) as any

    if (res.success) {
      const data = res.data
      let message = `股票 ${currentSyncStock.value.stock_code} 数据同步完成\n`

      if (data.realtime_sync) {
        if (data.realtime_sync.success) {
          message += `✅ 实时行情同步成功\n`
        } else {
          message += `❌ 实时行情同步失败: ${data.realtime_sync.error || '未知错误'}\n`
        }
      }

      if (data.historical_sync) {
        if (data.historical_sync.success) {
          message += `✅ 历史数据: ${data.historical_sync.records || 0} 条记录\n`
        } else {
          message += `❌ 历史数据同步失败: ${data.historical_sync.error || '未知错误'}\n`
        }
      }

      if (data.financial_sync) {
        if (data.financial_sync.success) {
          message += `✅ 财务数据同步成功\n`
        } else {
          message += `❌ 财务数据同步失败: ${data.financial_sync.error || '未知错误'}\n`
        }
      }

      if (data.basic_sync) {
        if (data.basic_sync.success) {
          message += `✅ 基础数据同步成功\n`
        } else {
          message += `❌ 基础数据同步失败: ${data.basic_sync.error || '未知错误'}\n`
        }
      }

      ElMessage.success(message)
      singleSyncDialogVisible.value = false
      await loadFavorites()
    } else {
      ElMessage.error((res as any).message || '同步失败')
    }
  } catch (error: any) {
    console.error('同步失败:', error)
    ElMessage.error(error.message || '同步失败，请稍后重试')
  } finally {
    singleSyncLoading.value = false
  }
}

// 格式化方法
const getChangeClass = (changePercent: number) => {
  if (changePercent > 0) return 'text-red'
  if (changePercent < 0) return 'text-green'
  return ''
}

const formatPrice = (value: any): string => {
  const n = Number(value)
  return typeof n === 'number' && Number.isFinite(n) ? n.toFixed(2) : '-'
}

const formatPercent = (n: any) => {
  const num = typeof n === 'number' && Number.isFinite(n) ? n : 0
  const sign = num >= 0 ? '+' : ''
  return `${sign}${num.toFixed(2)}%`
}

const formatDate = (dateStr: string) => {
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

// 生命周期
onMounted(() => {
  const auth = useAuthStore()
  if (auth.isAuthenticated) {
    loadFavorites()
    loadUserTags()
  }
})
</script>

<style lang="scss" scoped>
.favorites {
  .page-header {
    margin-bottom: 24px;

    .page-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 24px;
      font-weight: 600;
      color: var(--el-text-color-primary);
      margin: 0 0 8px 0;
    }

    .page-description {
      color: var(--el-text-color-regular);
      margin: 0;
    }
  }

  .action-card {
    margin-bottom: 24px;

    .action-buttons {
      display: flex;
      gap: 8px;
      justify-content: flex-end;
    }
  }

  .favorites-list-card {
    .empty-state {
      padding: 40px;
      text-align: center;
    }

    .text-red {
      color: #f56c6c;
    }

    .text-green {
      color: #67c23a;
    }
  }
}
</style>
