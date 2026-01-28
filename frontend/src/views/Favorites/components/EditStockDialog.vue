<!-- 编辑自选股对话框组件 -->
<template>
  <el-dialog
    v-model="visible"
    title="编辑自选股"
    width="520px"
    @close="handleClose"
  >
    <el-form :model="form" ref="formRef" label-width="100px">
      <el-form-item label="股票">
        <div>{{ form.stock_code }}｜{{ form.stock_name }}（{{ form.market }}）</div>
      </el-form-item>

      <el-form-item label="标签">
        <el-select v-model="form.tags" multiple filterable allow-create placeholder="选择或创建标签">
          <el-option v-for="tag in userTags" :key="tag" :label="tag" :value="tag">
            <span :style="{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }">
              <span>{{ tag }}</span>
              <span :style="{ display:'inline-block', width:'12px', height:'12px', border:'1px solid #ddd', borderRadius:'2px', marginLeft:'8px', background: getTagColor(tag) }"></span>
            </span>
          </el-option>
        </el-select>
      </el-form-item>

      <el-form-item label="备注">
        <el-input v-model="form.notes" type="textarea" :rows="2" placeholder="可选：添加备注信息" />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" :loading="loading" @click="handleSubmit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

// Props
interface Props {
  modelValue: boolean
  userTags: string[]
  tagColorMap: Record<string, string>
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: false,
  userTags: () => [],
  tagColorMap: () => ({}),
  loading: false
})

// Emits
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'submit': []
}>()

// 响应式数据
const formRef = ref()
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

// 方法
const getTagColor = (name: string) => {
  return props.tagColorMap[name] || ''
}

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
