# -*- coding: utf-8 -*-
<template>
  <div class="data-quality">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">
        <el-icon><DataAnalysis /></el-icon>
        数据质量监控
      </h1>
      <p class="page-description">
        实时监控数据源健康状况和数据质量指标
      </p>
    </div>

    <!-- 顶部操作栏 -->
    <el-card class="action-card">
      <div class="action-bar">
        <div class="refresh-info">
          <el-icon><Timer /></el-icon>
          <span>上次更新: {{ lastUpdateTime }}</span>
        </div>
        <div class="action-buttons">
          <el-button
            type="primary"
            :loading="refreshing"
            @click="refreshMetrics"
          >
            <el-icon><Refresh /></el-icon>
            刷新指标
          </el-button>
          <el-switch
            v-model="autoRefresh"
            active-text="自动刷新"
            @change="toggleAutoRefresh"
          />
        </div>
      </div>
    </el-card>

    <!-- 关键指标卡片 -->
    <el-row :gutter="16" class="metrics-row">
      <el-col :span="6">
        <el-card class="metric-card availability-card">
          <div class="metric-header">
            <el-icon class="metric-icon success"><SuccessFilled /></el-icon>
            <span class="metric-title">数据源可用性</span>
          </div>
          <div class="metric-value">
            {{ formatPercent(calculateAverageAvailability()) }}
          </div>
          <div class="metric-footer">
            <el-tag :type="getAvailabilityType()" size="small">
              {{ getAvailabilityText() }}
            </el-tag>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="metric-card latency-card">
          <div class="metric-header">
            <el-icon class="metric-icon primary"><Timer /></el-icon>
            <span class="metric-title">数据延迟</span>
          </div>
          <div class="metric-value">
            {{ formatLatency(currentMetrics.data_latency_ms) }}
          </div>
          <div class="metric-footer">
            <el-tag :type="getLatencyType()" size="small">
              {{ getLatencyText() }}
            </el-tag>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="metric-card anomaly-card">
          <div class="metric-header">
            <el-icon class="metric-icon warning"><WarningFilled /></el-icon>
            <span class="metric-title">异常值比例</span>
          </div>
          <div class="metric-value">
            {{ formatPercent(currentMetrics.anomaly_ratio) }}
          </div>
          <div class="metric-footer">
            <el-tag :type="getAnomalyType()" size="small">
              {{ getAnomalyText() }}
            </el-tag>
          </div>
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card class="metric-card missing-card">
          <div class="metric-header">
            <el-icon class="metric-icon danger"><CircleCloseFilled /></el-icon>
            <span class="metric-title">数据缺失率</span>
          </div>
          <div class="metric-value">
            {{ formatPercent(currentMetrics.missing_rate) }}
          </div>
          <div class="metric-footer">
            <el-tag :type="getMissingType()" size="small">
              {{ getMissingText() }}
            </el-tag>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 主要内容区域 -->
    <el-row :gutter="16" class="content-row">
      <!-- 左侧：数据源健康度 -->
      <el-col :span="12">
        <el-card class="source-health-card">
          <template #header>
            <div class="card-header">
              <span>数据源健康度</span>
              <el-tag :type="getOverallHealthType()" size="small">
                {{ getOverallHealthText() }}
              </el-tag>
            </div>
          </template>

          <div v-loading="loading" class="source-list">
            <div
              v-for="(availability, source) in currentMetrics.source_availability"
              :key="source"
              class="source-item"
            >
              <div class="source-info">
                <div class="source-name">{{ formatSourceName(source) }}</div>
                <div class="source-metrics">
                  <span class="metric-label">可用性:</span>
                  <span class="metric-value" :class="getAvailabilityClass(availability)">
                    {{ formatPercent(availability) }}
                  </span>
                </div>
              </div>
              <el-progress
                :percentage="availability * 100"
                :status="getAvailabilityStatus(availability)"
                :stroke-width="12"
              />
            </div>

            <div v-if="Object.keys(currentMetrics.source_availability).length === 0" class="empty-state">
              <el-empty description="暂无数据源信息" :image-size="80" />
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：最新告警 -->
      <el-col :span="12">
        <el-card class="alerts-card">
          <template #header>
            <div class="card-header">
              <span>
                最新告警
                <el-badge v-if="alertSummary.unresolved > 0" :value="alertSummary.unresolved" class="badge" />
              </span>
              <el-button type="text" size="small" @click="viewAllAlerts">
                查看全部
              </el-button>
            </div>
          </template>

          <div v-loading="loading" class="alerts-list">
            <div
              v-for="alert in recentAlerts"
              :key="alert.id"
              class="alert-item"
              :class="'alert-' + alert.severity"
            >
              <div class="alert-header">
                <el-icon class="alert-icon">
                  <SuccessFilled v-if="alert.severity === 'info'" />
                  <WarningFilled v-else-if="alert.severity === 'warning'" />
                  <CircleCloseFilled v-else />
                </el-icon>
                <span class="alert-title">{{ alert.title }}</span>
                <el-tag :type="getSeverityType(alert.severity)" size="small">
                  {{ getSeverityText(alert.severity) }}
                </el-tag>
              </div>
              <div class="alert-message">{{ alert.message }}</div>
              <div class="alert-footer">
                <span class="alert-time">{{ formatTime(alert.timestamp) }}</span>
                <el-button
                  v-if="!alert.resolved"
                  type="text"
                  size="small"
                  @click="resolveAlert(alert.id)"
                >
                  标记已解决
                </el-button>
              </div>
            </div>

            <div v-if="recentAlerts.length === 0" class="empty-state">
              <el-empty description="暂无告警" :image-size="80" />
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 质量评分分布 -->
    <el-row :gutter="16" class="distribution-row">
      <el-col :span="24">
        <el-card class="distribution-card">
          <template #header>
            <span>质量评分分布</span>
          </template>

          <div v-loading="loading" class="distribution-chart">
            <div class="grade-bars">
              <div
                v-for="(count, grade) in currentMetrics.quality_score_distribution"
                :key="grade"
                class="grade-bar"
              >
                <div class="grade-label">{{ grade }}级</div>
                <el-progress
                  :percentage="calculateGradePercentage(count)"
                  :color="getGradeColor(grade)"
                  :show-text="false"
                />
                <div class="grade-count">{{ count }}</div>
              </div>
            </div>

            <div v-if="Object.keys(currentMetrics.quality_score_distribution).length === 0" class="empty-state">
              <el-empty description="暂无评分分布数据" :image-size="80" />
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  DataAnalysis,
  Timer,
  Refresh,
  SuccessFilled,
  WarningFilled,
  CircleCloseFilled
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { dataQualityApi } from '@/api/dataQuality'
import type { DataQualityMetrics, Alert } from '@/types/dataQuality'

const router = useRouter()

// 响应式数据
const loading = ref(false)
const refreshing = ref(false)
const autoRefresh = ref(false)
const lastUpdateTime = ref('-')
const refreshTimer = ref<number | null>(null)

const currentMetrics = ref<DataQualityMetrics>({
  timestamp: new Date().toISOString(),
  source_availability: {},
  data_latency_ms: 0,
  anomaly_ratio: 0,
  missing_rate: 0,
  cross_validation_pass_rate: 0,
  quality_score_distribution: {}
})

const recentAlerts = ref<Alert[]>([])
const alertSummary = ref({
  total: 0,
  unresolved: 0,
  critical: 0,
  error: 0,
  warning: 0,
  info: 0
})

// 数据源名称映射
const sourceNameMap: Record<string, string> = {
  tushare: 'Tushare',
  akshare: 'AKShare',
  baostock: 'BaoStock',
  finnhub: 'FinnHub',
  yahoo: 'Yahoo Finance'
}

// 方法
const formatPercent = (value: number) => {
  return `${(value * 100).toFixed(1)}%`
}

const formatLatency = (ms: number) => {
  if (ms < 1000) {
    return `${ms.toFixed(0)}ms`
  }
  return `${(ms / 1000).toFixed(2)}s`
}

const formatSourceName = (source: string) => {
  return sourceNameMap[source.toLowerCase()] || source
}

const formatTime = (timestamp: string) => {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now.getTime() - date.getTime()

  if (diff < 60000) {
    return '刚刚'
  } else if (diff < 3600000) {
    return `${Math.floor(diff / 60000)}分钟前`
  } else if (diff < 86400000) {
    return `${Math.floor(diff / 3600000)}小时前`
  } else {
    return date.toLocaleString('zh-CN')
  }
}

const calculateAverageAvailability = () => {
  const values = Object.values(currentMetrics.value.source_availability)
  if (values.length === 0) return 0
  return values.reduce((a, b) => a + b, 0) / values.length
}

const calculateGradePercentage = (count: number) => {
  const total = Object.values(currentMetrics.value.quality_score_distribution).reduce((a, b) => a + b, 0)
  if (total === 0) return 0
  return (count / total) * 100
}

const getAvailabilityType = () => {
  const avg = calculateAverageAvailability()
  if (avg >= 0.95) return 'success'
  if (avg >= 0.90) return ''
  if (avg >= 0.80) return 'warning'
  return 'danger'
}

const getAvailabilityText = () => {
  const avg = calculateAverageAvailability()
  if (avg >= 0.95) return '优秀'
  if (avg >= 0.90) return '良好'
  if (avg >= 0.80) return '一般'
  return '较差'
}

const getLatencyType = () => {
  const ms = currentMetrics.value.data_latency_ms
  if (ms < 500) return 'success'
  if (ms < 2000) return ''
  if (ms < 5000) return 'warning'
  return 'danger'
}

const getLatencyText = () => {
  const ms = currentMetrics.value.data_latency_ms
  if (ms < 500) return '优秀'
  if (ms < 2000) return '良好'
  if (ms < 5000) return '偏高'
  return '过高'
}

const getAnomalyType = () => {
  const ratio = currentMetrics.value.anomaly_ratio
  if (ratio < 0.02) return 'success'
  if (ratio < 0.05) return ''
  if (ratio < 0.10) return 'warning'
  return 'danger'
}

const getAnomalyText = () => {
  const ratio = currentMetrics.value.anomaly_ratio
  if (ratio < 0.02) return '正常'
  if (ratio < 0.05) return '良好'
  if (ratio < 0.10) return '偏高'
  return '过高'
}

const getMissingType = () => {
  const rate = currentMetrics.value.missing_rate
  if (rate < 0.05) return 'success'
  if (rate < 0.10) return ''
  if (rate < 0.20) return 'warning'
  return 'danger'
}

const getMissingText = () => {
  const rate = currentMetrics.value.missing_rate
  if (rate < 0.05) return '正常'
  if (rate < 0.10) return '良好'
  if (rate < 0.20) return '偏高'
  return '过高'
}

const getOverallHealthType = () => {
  const avg = calculateAverageAvailability()
  if (avg >= 0.95) return 'success'
  if (avg >= 0.90) return ''
  if (avg >= 0.80) return 'warning'
  return 'danger'
}

const getOverallHealthText = () => {
  const avg = calculateAverageAvailability()
  if (avg >= 0.95) return '健康'
  if (avg >= 0.90) return '良好'
  if (avg >= 0.80) return '警告'
  return '危险'
}

const getAvailabilityClass = (availability: number) => {
  if (availability >= 0.95) return 'success'
  if (availability >= 0.90) return 'good'
  if (availability >= 0.80) return 'warning'
  return 'danger'
}

const getAvailabilityStatus = (availability: number) => {
  if (availability >= 0.95) return 'success'
  if (availability >= 0.90) return undefined
  if (availability >= 0.80) return 'warning'
  return 'exception'
}

const getGradeColor = (grade: string) => {
  const colors: Record<string, string> = {
    A: '#67c23a',
    B: '#409eff',
    C: '#e6a23c',
    D: '#f56c6c',
    F: '#909399'
  }
  return colors[grade] || '#909399'
}

const getSeverityType = (severity: string) => {
  const types: Record<string, any> = {
    info: 'info',
    warning: 'warning',
    error: 'danger',
    critical: 'danger'
  }
  return types[severity] || 'info'
}

const getSeverityText = (severity: string) => {
  const texts: Record<string, string> = {
    info: '信息',
    warning: '警告',
    error: '错误',
    critical: '严重'
  }
  return texts[severity] || '未知'
}

// 加载数据
const loadMetrics = async () => {
  try {
    loading.value = true
    const response = await dataQualityApi.getMetrics() as any
    if (response.success || response.data) {
      currentMetrics.value = response.data || response
      lastUpdateTime.value = new Date().toLocaleTimeString('zh-CN')
    }
  } catch (error) {
    console.error('加载指标失败:', error)
    ElMessage.error('加载数据质量指标失败')
  } finally {
    loading.value = false
  }
}

const loadAlerts = async () => {
  try {
    loading.value = true
    const response = await dataQualityApi.getAlerts(10) as any
    if (response.success || response.data) {
      recentAlerts.value = response.data || response || []
    }
  } catch (error) {
    console.error('加载告警失败:', error)
  } finally {
    loading.value = false
  }
}

const loadAlertSummary = async () => {
  try {
    const response = await dataQualityApi.getAlertSummary() as any
    if (response.success || response.data) {
      alertSummary.value = response.data || response || alertSummary.value
    }
  } catch (error) {
    console.error('加载告警摘要失败:', error)
  }
}

const refreshMetrics = async () => {
  try {
    refreshing.value = true
    const response = await dataQualityApi.refresh() as any
    if (response.success || response.data) {
      await loadMetrics()
      const newAlertsCount = response.data?.new_alerts_count || 0
      if (newAlertsCount > 0) {
        ElMessage.warning(`检测到 ${newAlertsCount} 个新告警`)
      } else {
        ElMessage.success('指标已刷新')
      }
    }
  } catch (error) {
    console.error('刷新指标失败:', error)
    ElMessage.error('刷新指标失败')
  } finally {
    refreshing.value = false
  }
}

const resolveAlert = async (alertId: string) => {
  try {
    await dataQualityApi.resolveAlert(alertId)
    await loadAlerts()
    await loadAlertSummary()
    ElMessage.success('告警已标记为已解决')
  } catch (error) {
    console.error('解决告警失败:', error)
    ElMessage.error('解决告警失败')
  }
}

const viewAllAlerts = () => {
  // 可以跳转到告警详情页面
  ElMessage.info('告警详情页面开发中')
}

const toggleAutoRefresh = (enabled: boolean) => {
  if (enabled) {
    refreshTimer.value = window.setInterval(async () => {
      await loadMetrics()
      await loadAlerts()
      await loadAlertSummary()
    }, 30000) // 30秒刷新
    ElMessage.info('自动刷新已启用 (30秒)')
  } else {
    if (refreshTimer.value) {
      clearInterval(refreshTimer.value)
      refreshTimer.value = null
    }
    ElMessage.info('自动刷新已关闭')
  }
}

// 生命周期
onMounted(async () => {
  await Promise.all([
    loadMetrics(),
    loadAlerts(),
    loadAlertSummary()
  ])
})

onUnmounted(() => {
  if (refreshTimer.value) {
    clearInterval(refreshTimer.value)
  }
})
</script>

<style lang="scss" scoped>
.data-quality {
  padding: 16px;

  .page-header {
    margin-bottom: 24px;

    .page-title {
      font-size: 24px;
      font-weight: 600;
      margin: 0 0 8px 0;
      display: flex;
      align-items: center;
      gap: 12px;
      color: var(--el-text-color-primary);
    }

    .page-description {
      font-size: 14px;
      color: var(--el-text-color-regular);
      margin: 0;
    }
  }

  .action-card {
    margin-bottom: 16px;

    .action-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .refresh-info {
        display: flex;
        align-items: center;
        gap: 8px;
        color: var(--el-text-color-regular);
        font-size: 14px;
      }

      .action-buttons {
        display: flex;
        align-items: center;
        gap: 16px;
      }
    }
  }

  .metrics-row {
    margin-bottom: 16px;

    .metric-card {
      .metric-header {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 12px;

        .metric-icon {
          font-size: 24px;

          &.success { color: #67c23a; }
          &.primary { color: #409eff; }
          &.warning { color: #e6a23c; }
          &.danger { color: #f56c6c; }
        }

        .metric-title {
          font-size: 14px;
          color: var(--el-text-color-regular);
        }
      }

      .metric-value {
        font-size: 28px;
        font-weight: 600;
        color: var(--el-text-color-primary);
        margin-bottom: 12px;
      }

      .metric-footer {
        display: flex;
        gap: 8px;
      }
    }
  }

  .content-row {
    margin-bottom: 16px;

    .source-health-card,
    .alerts-card {
      .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;

        .badge {
          margin-left: 8px;
        }
      }
    }

    .source-list {
      .source-item {
        padding: 16px 0;

        &:not(:last-child) {
          border-bottom: 1px solid var(--el-border-color-lighter);
        }

        .source-info {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 8px;

          .source-name {
            font-weight: 600;
            color: var(--el-text-color-primary);
          }

          .source-metrics {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;

            .metric-label {
              color: var(--el-text-color-regular);
            }

            .metric-value {
              font-weight: 600;

              &.success { color: #67c23a; }
              &.good { color: #409eff; }
              &.warning { color: #e6a23c; }
              &.danger { color: #f56c6c; }
            }
          }
        }
      }
    }

    .alerts-list {
      max-height: 400px;
      overflow-y: auto;

      .alert-item {
        padding: 12px;
        margin-bottom: 12px;
        border-radius: 6px;
        border-left: 3px solid;

        &.alert-info {
          background-color: var(--el-color-info-light-9);
          border-left-color: var(--el-color-info);
        }

        &.alert-warning {
          background-color: var(--el-color-warning-light-9);
          border-left-color: var(--el-color-warning);
        }

        &.alert-error,
        &.alert-critical {
          background-color: var(--el-color-danger-light-9);
          border-left-color: var(--el-color-danger);
        }

        .alert-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 8px;

          .alert-icon {
            font-size: 18px;
          }

          .alert-title {
            flex: 1;
            font-weight: 600;
            color: var(--el-text-color-primary);
          }
        }

        .alert-message {
          font-size: 13px;
          color: var(--el-text-color-regular);
          margin-bottom: 8px;
          line-height: 1.5;
        }

        .alert-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;

          .alert-time {
            font-size: 12px;
            color: var(--el-text-color-placeholder);
          }
        }
      }
    }
  }

  .distribution-row {
    .distribution-chart {
      .grade-bars {
        display: flex;
        flex-direction: column;
        gap: 16px;

        .grade-bar {
          display: flex;
          align-items: center;
          gap: 16px;

          .grade-label {
            width: 40px;
            font-weight: 600;
            color: var(--el-text-color-primary);
          }

          .el-progress {
            flex: 1;
          }

          .grade-count {
            width: 40px;
            text-align: right;
            font-weight: 600;
            color: var(--el-text-color-regular);
          }
        }
      }
    }
  }

  .empty-state {
    text-align: center;
    padding: 40px 20px;
  }
}

// 响应式设计
@media (max-width: 768px) {
  .data-quality {
    .metrics-row {
      .el-col {
        margin-bottom: 12px;
      }
    }

    .content-row {
      .el-col {
        margin-bottom: 16px;
      }
    }

    .action-card {
      .action-bar {
        flex-direction: column;
        gap: 12px;

        .action-buttons {
          width: 100%;
          justify-content: space-between;
        }
      }
    }
  }
}
</style>
