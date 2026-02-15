# -*- coding: utf-8 -*-
<template>
  <el-dialog
    v-model="visible"
    :title="`任务进度 - ${taskId?.slice(0, 8)}...`"
    width="800px"
    @close="handleClose"
    destroy-on-close
  >
    <div v-loading="loading" class="progress-dialog">
      <!-- 总体进度 -->
      <div class="overall-progress">
        <div class="progress-header">
          <span class="progress-label">总体进度</span>
          <span class="progress-percentage">{{ progressData.progress_percentage || 0 }}%</span>
        </div>
        <el-progress
          :percentage="progressData.progress_percentage || 0"
          :status="progressStatus"
          :stroke-width="20"
        />
        <div class="progress-info">
          <span>{{ progressData.current_step_name || '初始化...' }}</span>
          <span class="time-info">
            已用时 {{ formatTime(progressData.elapsed_time) }}
            <span v-if="progressData.remaining_time > 0">
              / 预计剩余 {{ formatTime(progressData.remaining_time) }}
            </span>
          </span>
        </div>
      </div>

      <!-- 步骤列表 -->
      <div class="steps-list">
        <div class="section-title">
          <h4>执行步骤</h4>
          <el-tag :type="getStatusTagType(progressData.status)" size="small">
            {{ getStatusText(progressData.status) }}
          </el-tag>
        </div>

        <div class="steps-container">
          <div
            v-for="(step, index) in progressData.steps"
            :key="index"
            :class="[
              'step-item',
              `step-${step.status}`,
              { 'step-current': step.status === 'current' }
            ]"
          >
            <div class="step-icon">
              <el-icon v-if="step.status === 'completed'"><CircleCheck /></el-icon>
              <el-icon v-else-if="step.status === 'current'" class="spin"><Loading /></el-icon>
              <el-icon v-else-if="step.status === 'failed'"><CircleClose /></el-icon>
              <el-icon v-else><Clock /></el-icon>
            </div>
            <div class="step-content">
              <div class="step-header">
                <span class="step-name">{{ step.name }}</span>
                <span v-if="step.start_time && step.end_time" class="step-duration">
                  {{ formatDuration(step.end_time - step.start_time) }}
                </span>
              </div>
              <div class="step-description">{{ step.description }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 代理状态 -->
      <div v-if="agentStatusList.length > 0" class="agent-status">
        <div class="section-title">
          <h4>分析团队状态</h4>
        </div>
        <div class="agents-grid">
          <div
            v-for="(agent, name) in agentStatusList"
            :key="name"
            :class="['agent-item', `agent-${agent.status}`]"
          >
            <el-icon v-if="agent.status === 'completed'"><CircleCheck /></el-icon>
            <el-icon v-else-if="agent.status === 'in_progress'" class="spin"><Loading /></el-icon>
            <el-icon v-else><Clock /></el-icon>
            <span>{{ name }}</span>
          </div>
        </div>
      </div>

      <!-- 任务信息 -->
      <div class="task-info">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="任务ID">
            <el-text type="info" size="small">{{ taskId }}</el-text>
          </el-descriptions-item>
          <el-descriptions-item label="研究深度">
            {{ progressData.research_depth || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="分析师数量">
            {{ progressData.analysts?.length || 0 }}
          </el-descriptions-item>
          <el-descriptions-item label="LLM提供商">
            {{ progressData.llm_provider || '-' }}
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </div>

    <template #footer>
      <el-button @click="handleClose">关闭</el-button>
      <el-button type="primary" @click="refreshProgress" :loading="loading">
        刷新
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { CircleCheck, CircleClose, Clock, Loading } from '@element-plus/icons-vue'
import { analysisApi } from '@/api/analysis'

interface ProgressData {
  task_id: string
  status: string
  progress_percentage: number
  current_step: number
  current_step_name: string
  current_step_description: string
  steps: Array<{
    name: string
    description: string
    status: string
    start_time?: number
    end_time?: number
  }>
  agent_status: Record<string, { status: string; updated_at: number }>
  elapsed_time: number
  remaining_time: number
  estimated_total_time: number
  analysts: string[]
  research_depth: string
  llm_provider: string
}

const props = defineProps<{
  modelValue: boolean
  taskId?: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'close': []
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (val) => emit('update:modelValue', val)
})

const loading = ref(false)
const progressData = ref<ProgressData>({
  task_id: '',
  status: 'unknown',
  progress_percentage: 0,
  current_step: 0,
  current_step_name: '',
  current_step_description: '',
  steps: [],
  agent_status: {},
  elapsed_time: 0,
  remaining_time: 0,
  estimated_total_time: 0,
  analysts: [],
  research_depth: '',
  llm_provider: ''
})

// 代理状态列表（转换对象为数组以便遍历）
const agentStatusList = computed(() => {
  return Object.entries(progressData.value.agent_status || {}).map(([name, info]: [string, any]) => ({
    name,
    status: info.status || 'pending'
  }))
})

// 进度状态
const progressStatus = computed(() => {
  const status = progressData.value.status
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'exception'
  return undefined
})

// 获取进度数据
const fetchProgress = async () => {
  if (!props.taskId) return

  loading.value = true
  try {
    const response = await analysisApi.getTaskProgress(props.taskId)
    const data = (response as any)?.data?.data

    if (data) {
      progressData.value = {
        task_id: data.task_id || '',
        status: data.status || 'unknown',
        progress_percentage: data.progress_percentage || 0,
        current_step: data.current_step || 0,
        current_step_name: data.current_step_name || '',
        current_step_description: data.current_step_description || '',
        steps: data.steps || [],
        agent_status: data.agent_status || {},
        elapsed_time: data.elapsed_time || 0,
        remaining_time: data.remaining_time || 0,
        estimated_total_time: data.estimated_total_time || 0,
        analysts: data.analysts || [],
        research_depth: data.research_depth || '',
        llm_provider: data.llm_provider || ''
      }
    }
  } catch (error: any) {
    console.error('获取进度失败:', error)
    ElMessage.error(error?.message || '获取进度失败')
  } finally {
    loading.value = false
  }
}

const refreshProgress = () => {
  fetchProgress()
}

const handleClose = () => {
  emit('close')
}

// 格式化时间
const formatTime = (seconds: number) => {
  if (!seconds || seconds < 0) return '0秒'
  const minutes = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  if (minutes > 0) {
    return `${minutes}分${secs}秒`
  }
  return `${secs}秒`
}

const formatDuration = (seconds: number) => {
  if (!seconds || seconds < 0) return ''
  return formatTime(seconds)
}

const getStatusTagType = (status: string): 'success' | 'warning' | 'danger' | 'info' => {
  const map: Record<string, 'success' | 'warning' | 'danger' | 'info'> = {
    completed: 'success',
    running: 'warning',
    processing: 'warning',
    failed: 'danger',
    pending: 'info'
  }
  return map[status] || 'info'
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    completed: '已完成',
    running: '运行中',
    processing: '处理中',
    failed: '失败',
    pending: '等待中'
  }
  return map[status] || status
}

// 监听弹窗打开，自动获取进度
watch(() => props.modelValue, (newVal) => {
  if (newVal && props.taskId) {
    fetchProgress()
  }
})

// 监听taskId变化
watch(() => props.taskId, (newVal) => {
  if (newVal && props.modelValue) {
    fetchProgress()
  }
})
</script>

<style scoped lang="scss">
.progress-dialog {
  .overall-progress {
    margin-bottom: 24px;

    .progress-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;

      .progress-label {
        font-weight: 600;
        font-size: 14px;
      }

      .progress-percentage {
        font-size: 18px;
        font-weight: bold;
        color: var(--el-color-primary);
      }
    }

    .progress-info {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 8px;
      font-size: 13px;
      color: var(--el-text-color-regular);

      .time-info {
        color: var(--el-text-color-secondary);
      }
    }
  }

  .steps-list {
    margin-bottom: 24px;

    .section-title {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;

      h4 {
        margin: 0;
        font-size: 15px;
        font-weight: 600;
      }
    }

    .steps-container {
      max-height: 400px;
      overflow-y: auto;

      .step-item {
        display: flex;
        align-items: flex-start;
        padding: 12px;
        margin-bottom: 8px;
        border-radius: 6px;
        background: var(--el-fill-color-light);
        transition: all 0.3s;

        &.step-current {
          background: var(--el-color-primary-light-9);
          border-left: 3px solid var(--el-color-primary);
        }

        &.step-completed {
          opacity: 0.8;

          .step-icon {
            color: var(--el-color-success);
          }
        }

        &.step-failed {
          background: var(--el-color-danger-light-9);
          border-left: 3px solid var(--el-color-danger);

          .step-icon {
            color: var(--el-color-danger);
          }
        }

        .step-icon {
          margin-right: 12px;
          font-size: 20px;
          color: var(--el-text-color-placeholder);

          &.spin {
            animation: spin 1s linear infinite;
          }
        }

        .step-content {
          flex: 1;

          .step-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 4px;

            .step-name {
              font-weight: 600;
              font-size: 14px;
            }

            .step-duration {
              font-size: 12px;
              color: var(--el-text-color-secondary);
            }
          }

          .step-description {
            font-size: 13px;
            color: var(--el-text-color-regular);
            line-height: 1.5;
          }
        }
      }
    }
  }

  .agent-status {
    margin-bottom: 24px;

    .section-title {
      margin-bottom: 12px;

      h4 {
        margin: 0;
        font-size: 15px;
        font-weight: 600;
      }
    }

    .agents-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
      gap: 8px;

      .agent-item {
        display: flex;
        align-items: center;
        gap: 6px;
        padding: 8px 12px;
        border-radius: 4px;
        background: var(--el-fill-color-light);
        font-size: 13px;

        &.agent-in_progress {
          background: var(--el-color-primary-light-9);
          color: var(--el-color-primary);
          font-weight: 600;
        }

        &.agent-completed {
          opacity: 0.8;
        }
      }
    }
  }

  .task-info {
    padding-top: 16px;
    border-top: 1px solid var(--el-border-color-lighter);
  }
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
