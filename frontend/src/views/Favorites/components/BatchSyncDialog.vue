<!-- 批量同步对话框组件 -->
<template>
  <el-dialog
    v-model="visible"
    title="批量同步股票数据"
    width="500px"
    @close="handleClose"
  >
    <el-alert
      type="info"
      :closable="false"
      style="margin-bottom: 16px;"
    >
      已选择 <strong>{{ selectedCount }}</strong> 只股票
    </el-alert>

    <el-form :model="form" label-width="120px">
      <el-form-item label="同步内容">
        <el-checkbox-group v-model="form.syncTypes">
          <el-checkbox label="historical">历史行情数据</el-checkbox>
          <el-checkbox label="financial">财务数据</el-checkbox>
          <el-checkbox label="basic">基础数据</el-checkbox>
        </el-checkbox-group>
      </el-form-item>

      <el-form-item label="数据源">
        <el-radio-group v-model="form.dataSource">
          <el-radio label="tushare">Tushare</el-radio>
          <el-radio label="akshare">AKShare</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="历史数据天数" v-if="form.syncTypes.includes('historical')">
        <el-input-number v-model="form.days" :min="1" :max="3650" />
        <span style="margin-left: 10px; color: #909399; font-size: 12px;">
          (最多3650天，约10年)
        </span>
      </el-form-item>
    </el-form>

    <el-alert
      type="warning"
      :closable="false"
      style="margin-top: 16px;"
    >
      批量同步可能需要较长时间，请耐心等待
    </el-alert>

    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" @click="handleSubmit" :loading="loading">
        开始同步
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

// Props
interface Props {
  modelValue: boolean
  selectedCount: number
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: false,
  selectedCount: 0,
  loading: false
})

// Emits
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'submit': []
}>()

// 响应式数据
const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const form = ref({
  syncTypes: ['historical', 'financial'],
  dataSource: 'tushare' as 'tushare' | 'akshare',
  days: 365
})

// 方法
const handleSubmit = () => {
  emit('submit')
}

const handleClose = () => {
  visible.value = false
}

// 暴露给父组件
defineExpose({
  form
})
</script>

<style lang="scss" scoped>
// 组件特定样式
</style>
