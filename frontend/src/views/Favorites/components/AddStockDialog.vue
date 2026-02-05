<!-- 添加自选股对话框组件 -->
<template>
  <el-dialog
    v-model="visible"
    title="添加自选股"
    width="500px"
    @close="handleClose"
  >
    <el-form :model="form" :rules="rules" ref="formRef" label-width="100px">
      <el-form-item label="市场类型" prop="market">
        <el-select v-model="form.market" @change="handleMarketChange">
          <el-option label="A股" value="A股" />
          <el-option label="港股" value="港股" />
          <el-option label="美股" value="美股" />
        </el-select>
      </el-form-item>

      <el-form-item label="股票代码" prop="stock_code">
        <el-input
          v-model="form.stock_code"
          :placeholder="stockCodePlaceholder"
          @blur="fetchStockInfo"
        />
        <div style="font-size: 12px; color: #909399; margin-top: 4px;">
          {{ stockCodeHint }}
        </div>
      </el-form-item>

      <el-form-item label="股票名称" prop="stock_name">
        <el-input v-model="form.stock_name" placeholder="股票名称" />
        <div v-if="form.market !== 'A股'" style="font-size: 12px; color: #E6A23C; margin-top: 4px;">
          {{ form.market }}不支持自动获取，请手动输入股票名称
        </div>
      </el-form-item>

      <el-form-item label="标签">
        <el-select
          v-model="form.tags"
          multiple
          filterable
          allow-create
          placeholder="选择或创建标签"
        >
          <el-option v-for="tag in userTags" :key="tag" :label="tag" :value="tag">
            <span :style="{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }">
              <span>{{ tag }}</span>
              <span :style="{ display:'inline-block', width:'12px', height:'12px', border:'1px solid #ddd', borderRadius:'2px', marginLeft:'8px', background: getTagColor(tag) }"></span>
            </span>
          </el-option>
        </el-select>
      </el-form-item>

      <el-form-item label="备注">
        <el-input
          v-model="form.notes"
          type="textarea"
          :rows="2"
          placeholder="可选：添加备注信息"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" @click="handleSubmit" :loading="loading">
        添加
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { ApiClient } from '@/api/request'
import type { StockInfo } from '@/types/analysis'

// Props
interface Props {
  modelValue: boolean
  userTags: string[]
  tagColorMap: Record<string, string>
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: false,
  userTags: () => [],
  tagColorMap: () => ({})
})

// Emits
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'success': [data: typeof form.value]
}>()

// 响应式数据
const formRef = ref()
const loading = ref(false)
const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const form = ref({
  stock_code: '',
  stock_name: '',
  market: 'A股',
  tags: [] as string[],
  notes: ''
})

// 股票代码验证器
const validateStockCode = (rule: any, value: any, callback: any) => {
  if (!value) {
    callback(new Error('请输入股票代码'))
    return
  }

  const code = value.trim()
  const market = form.value.market

  if (market === 'A股') {
    // A股：6位数字
    if (!/^\d{6}$/.test(code)) {
      callback(new Error('A股代码必须是6位数字，如：000001'))
      return
    }
  } else if (market === '港股') {
    // 港股：4位数字 或 4-5位数字+.HK
    if (!/^\d{4,5}$/.test(code) && !/^\d{4,5}\.HK$/i.test(code)) {
      callback(new Error('港股代码格式：4位数字（如：0700）或带后缀（如：0700.HK）'))
      return
    }
  } else if (market === '美股') {
    // 美股：1-5个字母
    if (!/^[A-Z]{1,5}$/i.test(code)) {
      callback(new Error('美股代码必须是1-5个字母，如：AAPL'))
      return
    }
  }

  callback()
}

const rules = {
  market: [
    { required: true, message: '请选择市场类型', trigger: 'change' }
  ],
  stock_code: [
    { required: true, message: '请输入股票代码', trigger: 'blur' },
    { validator: validateStockCode, trigger: 'blur' }
  ],
  stock_name: [
    { required: true, message: '请输入股票名称', trigger: 'blur' }
  ]
}

// 计算属性
const stockCodePlaceholder = computed(() => {
  const market = form.value.market
  if (market === 'A股') {
    return '请输入6位数字代码，如：000001'
  } else if (market === '港股') {
    return '请输入4位数字代码，如：0700'
  } else if (market === '美股') {
    return '请输入股票代码，如：AAPL'
  }
  return '请输入股票代码'
})

const stockCodeHint = computed(() => {
  const market = form.value.market
  if (market === 'A股') {
    return '输入代码后失焦，将自动填充股票名称'
  } else if (market === '港股') {
    return '港股不支持自动获取名称，请手动输入'
  } else if (market === '美股') {
    return '美股不支持自动获取名称，请手动输入'
  }
  return ''
})

// 方法
const getTagColor = (name: string) => {
  return props.tagColorMap[name] || ''
}

const handleMarketChange = () => {
  form.value.stock_code = ''
  form.value.stock_name = ''
  // 清除验证错误
  if (formRef.value) {
    formRef.value.clearValidate(['stock_code', 'stock_name'])
  }
}

const fetchStockInfo = async () => {
  if (!form.value.stock_code) return

  try {
    const symbol = form.value.stock_code.trim()
    const market = form.value.market

      // 只有A股支持自动获取股票名称
      if (market === 'A股') {
        // ApiClient.get 已经解包了 response.data，所以直接返回 StockInfo 对象
        const stockInfo = await ApiClient.get<StockInfo>(`/api/stock-data/basic-info/${symbol}`)

        if (stockInfo?.name) {
          form.value.stock_name = stockInfo.name
          ElMessage.success(`已自动填充股票名称: ${stockInfo.name}`)
        } else {
          ElMessage.warning('未找到该股票信息，请手动输入股票名称')
        }
      }
  } catch (error: any) {
    console.error('获取股票信息失败:', error)
    ElMessage.warning('获取股票信息失败，请手动输入股票名称')
  }
}

const handleSubmit = async () => {
  try {
    await formRef.value.validate()
    // 传递表单数据给父组件
    emit('success', { ...form.value })
  } catch (error) {
    console.error('表单验证失败:', error)
  }
}

const handleClose = () => {
  form.value = {
    stock_code: '',
    stock_name: '',
    market: 'A股',
    tags: [],
    notes: ''
  }
  if (formRef.value) {
    formRef.value.clearValidate()
  }
  visible.value = false
}

// 监听对话框打开，重置表单
watch(visible, (val) => {
  if (val) {
    form.value = {
      stock_code: '',
      stock_name: '',
      market: 'A股',
      tags: [],
      notes: ''
    }
  }
})
</script>

<style lang="scss" scoped>
// 组件特定样式
</style>
