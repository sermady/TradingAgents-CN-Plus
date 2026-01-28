<!-- 自选股表格组件 -->
<template>
  <div class="favorites-table">
    <!-- 工具栏：全选和列表信息 -->
    <div class="table-toolbar">
      <el-checkbox
        v-model="allSelected"
        :indeterminate="indeterminate"
        @change="handleSelectAll"
      >
        全选
      </el-checkbox>
      <span class="table-info">
        共 {{ data.length }} 只股票
        <span v-if="selectedCodes.size > 0">，已选 {{ selectedCodes.size }} 只</span>
      </span>
    </div>

    <!-- 表格 -->
    <el-table
      :data="data"
      style="width: 100%"
      @selection-change="handleTableSelectionChange"
      row-key="stock_code"
    >
      <el-table-column type="selection" width="55" />

      <el-table-column prop="stock_code" label="股票代码" width="120">
        <template #default="{ row }">
          <el-link type="primary" @click="$emit('view-detail', row)">
            {{ row.stock_code }}
          </el-link>
        </template>
      </el-table-column>

      <el-table-column prop="stock_name" label="股票名称" width="150" />

      <el-table-column prop="market" label="市场" width="80" />

      <el-table-column prop="board" label="板块" width="100" />

      <el-table-column prop="exchange" label="交易所" width="140" />

      <el-table-column prop="current_price" label="当前价格" width="100">
        <template #default="{ row }">
          <span v-if="row.current_price !== null && row.current_price !== undefined">
            ¥{{ formatPrice(row.current_price) }}
          </span>
          <span v-else>-</span>
        </template>
      </el-table-column>

      <el-table-column prop="change_percent" label="涨跌幅" width="100">
        <template #default="{ row }">
          <span
            v-if="row.change_percent !== null && row.change_percent !== undefined"
            :class="getChangeClass(row.change_percent)"
          >
            {{ formatPercent(row.change_percent) }}
          </span>
          <span v-else>-</span>
        </template>
      </el-table-column>

      <el-table-column prop="tags" label="标签" min-width="150">
        <template #default="{ row }">
          <el-tag
            v-for="tag in row.tags"
            :key="tag"
            size="small"
            :color="getTagColor(tag)"
            effect="dark"
            style="margin-right: 4px;"
          >
            {{ tag }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="added_at" label="添加时间" width="120">
        <template #default="{ row }">
          {{ formatDate(row.added_at) }}
        </template>
      </el-table-column>

      <el-table-column label="操作" width="260" fixed="right">
        <template #default="{ row }">
          <el-button type="text" size="small" @click="$emit('edit', row)">
            编辑
          </el-button>
          <el-button
            v-if="row.market === 'A股'"
            type="text"
            size="small"
            @click="$emit('sync', row)"
            style="color: #409EFF;"
          >
            同步
          </el-button>
          <el-button type="text" size="small" @click="$emit('analyze', row)">
            分析
          </el-button>
          <el-button type="text" size="small" @click="$emit('remove', row)" style="color: #f56c6c;">
            移除
          </el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { FavoriteItem } from '@/api/favorites'

// Props
interface Props {
  data: FavoriteItem[]
  selectedStocks: FavoriteItem[]
  tagColorMap: Record<string, string>
  containerHeight?: string
}

const props = withDefaults(defineProps<Props>(), {
  data: () => [],
  selectedStocks: () => [],
  tagColorMap: () => ({}),
  containerHeight: '600px'
})

// Emits
const emit = defineEmits<{
  'selection-change': [value: FavoriteItem[]]
  'view-detail': [row: FavoriteItem]
  'edit': [row: FavoriteItem]
  'sync': [row: FavoriteItem]
  'analyze': [row: FavoriteItem]
  'remove': [row: FavoriteItem]
}>()

// 选择状态管理
const selectedCodes = ref<Set<string>>(new Set())

// 全选状态
const allSelected = computed({
  get: () => props.data.length > 0 && selectedCodes.value.size === props.data.length,
  set: (val: boolean) => {
    if (val) {
      selectedCodes.value = new Set(props.data.map(item => item.stock_code))
    } else {
      selectedCodes.value.clear()
    }
    emitSelectionChange()
  }
})

// 半选状态
const indeterminate = computed(() => {
  const size = selectedCodes.value.size
  return size > 0 && size < props.data.length
})

// 监听外部选择变化
watch(() => props.selectedStocks, (newVal) => {
  selectedCodes.value = new Set(newVal.map(item => item.stock_code))
}, { immediate: true })

// 表格选择变化
const handleTableSelectionChange = (selection: FavoriteItem[]) => {
  selectedCodes.value = new Set(selection.map(item => item.stock_code))
  emitSelectionChange()
}

// 处理全选
const handleSelectAll = (value: boolean) => {
  if (value) {
    selectedCodes.value = new Set(props.data.map(item => item.stock_code))
  } else {
    selectedCodes.value.clear()
  }
  emitSelectionChange()
}

// 触发选择变化事件
const emitSelectionChange = () => {
  const selected = props.data.filter(item => selectedCodes.value.has(item.stock_code))
  emit('selection-change', selected)
}

// 格式化方法
const getTagColor = (name: string) => {
  return props.tagColorMap[name] || ''
}

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
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleDateString('zh-CN')
}
</script>

<style lang="scss" scoped>
.favorites-table {
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  background: var(--el-bg-color);
}

.table-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  background: var(--el-fill-color-lighter);

  .table-info {
    font-size: 14px;
    color: var(--el-text-color-regular);
  }
}

.text-red {
  color: #f56c6c;
}

.text-green {
  color: #67c23a;
}
</style>
