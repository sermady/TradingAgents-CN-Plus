<!-- 标签管理对话框组件 -->
<template>
  <el-dialog v-model="visible" title="标签管理" width="560px" @close="handleClose">
    <el-table :data="tagList" v-loading="loading" size="small" style="width: 100%; margin-bottom: 12px;">
      <el-table-column label="名称" min-width="220">
        <template #default="{ row }">
          <template v-if="row._editing">
            <el-input v-model="row._name" placeholder="标签名称" size="small" />
          </template>
          <template v-else>
            <el-tag :color="row.color" effect="dark" style="margin-right:6px"></el-tag>
            {{ row.name }}
          </template>
        </template>
      </el-table-column>

      <el-table-column label="颜色" width="140">
        <template #default="{ row }">
          <template v-if="row._editing">
            <el-select v-model="row._color" placeholder="选择颜色" size="small" style="width: 200px">
              <el-option v-for="c in colorPalette" :key="c" :label="c" :value="c">
                <span :style="{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }">
                  <span>{{ c }}</span>
                  <span :style="{ display: 'inline-block', width: '12px', height: '12px', border: '1px solid #ddd', borderRadius: '2px', marginLeft: '8px', background: c }"></span>
                </span>
              </el-option>
            </el-select>
            <span class="color-dot-preview" :style="{ background: row._color }"></span>
          </template>
          <template v-else>
            <span :style="{display:'inline-block',width:'14px',height:'14px',background: row.color,border:'1px solid #ddd',marginRight:'6px'}"></span>
            {{ row.color }}
          </template>
        </template>
      </el-table-column>

      <el-table-column label="排序" width="100" align="center">
        <template #default="{ row }">
          <template v-if="row._editing">
            <el-input v-model.number="row._sort" type="number" size="small" />
          </template>
          <template v-else>
            {{ row.sort_order }}
          </template>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <template v-if="row._editing">
            <el-button type="text" size="small" @click="handleSaveTag(row)">保存</el-button>
            <el-button type="text" size="small" @click="handleCancelEdit(row)">取消</el-button>
          </template>
          <template v-else>
            <el-button type="text" size="small" @click="handleEditTag(row)">编辑</el-button>
            <el-button type="text" size="small" style="color:#f56c6c" @click="handleDeleteTag(row)">删除</el-button>
          </template>
        </template>
      </el-table-column>
    </el-table>

    <div style="display:flex; gap:8px; align-items:center;">
      <el-input v-model="newTag.name" placeholder="新标签名" style="flex:1" />
      <el-select v-model="newTag.color" placeholder="选择颜色" style="width:200px">
        <el-option v-for="c in colorPalette" :key="c" :label="c" :value="c">
          <span :style="{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }">
            <span>{{ c }}</span>
            <span :style="{ display: 'inline-block', width: '12px', height: '12px', border: '1px solid #ddd', borderRadius: '2px', marginLeft: '8px', background: c }"></span>
          </span>
        </el-option>
      </el-select>
      <span class="color-dot-preview" :style="{ background: newTag.color }"></span>
      <el-input v-model.number="newTag.sort_order" type="number" placeholder="排序" style="width:120px" />
      <el-button type="primary" @click="handleCreateTag" :loading="loading">新增</el-button>
    </div>

    <template #footer>
      <el-button @click="handleClose">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

// 颜色可选项（20种预设颜色）
const COLOR_PALETTE = [
  '#409EFF', '#1677FF', '#2F88FF', '#52C41A', '#67C23A',
  '#13C2C2', '#FA8C16', '#E6A23C', '#F56C6C', '#EB2F96',
  '#722ED1', '#8E44AD', '#00BFBF', '#1F2D3D', '#606266',
  '#909399', '#C0C4CC', '#FF7F50', '#A0CFFF', '#2C3E50'
]

// Props
interface Props {
  modelValue: boolean
  tagList: any[]
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: false,
  tagList: () => [],
  loading: false
})

// Emits
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'create': [tag: any]
  'edit': [tag: any]
  'save': [tag: any]
  'delete': [tag: any]
  'cancel-edit': [tag: any]
}>()

// 响应式数据
const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const colorPalette = ref(COLOR_PALETTE)
const newTag = ref({ name: '', color: '#409EFF', sort_order: 0 })

// 方法
const handleCreateTag = () => {
  emit('create', { ...newTag.value })
  newTag.value = { name: '', color: '#409EFF', sort_order: 0 }
}

const handleEditTag = (row: any) => {
  emit('edit', row)
}

const handleSaveTag = (row: any) => {
  emit('save', row)
}

const handleCancelEdit = (row: any) => {
  emit('cancel-edit', row)
}

const handleDeleteTag = (row: any) => {
  emit('delete', row)
}

const handleClose = () => {
  visible.value = false
}
</script>

<style lang="scss" scoped>
.color-dot-preview {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 1px solid #ddd;
  border-radius: 2px;
  margin-left: 6px;
  vertical-align: middle;
}
</style>
