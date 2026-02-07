/**
 * 数据质量监控相关类型定义
 */

/** 通用 API 响应包装 */
export interface ApiResponse<T> {
  success?: boolean
  data?: T
  error?: string
  message?: string
}

/** 数据质量指标 */
export interface DataQualityMetrics {
  /** 时间戳 */
  timestamp: string
  /** 数据源可用性 {source: availability_rate} */
  source_availability: Record<string, number>
  /** 数据延迟（毫秒） */
  data_latency_ms: number
  /** 异常值比例 */
  anomaly_ratio: number
  /** 数据缺失率 */
  missing_rate: number
  /** 交叉验证通过率 */
  cross_validation_pass_rate: number
  /** 质量评分分布 {grade: count} */
  quality_score_distribution: Record<string, number>
}

/** 告警严重程度 */
export type AlertSeverity = 'info' | 'warning' | 'error' | 'critical'

/** 告警信息 */
export interface Alert {
  /** 告警ID */
  id: string
  /** 严重程度 */
  severity: AlertSeverity
  /** 标题 */
  title: string
  /** 消息内容 */
  message: string
  /** 时间戳 */
  timestamp: string
  /** 指标名称 */
  metric_name: string
  /** 当前值 */
  current_value: number
  /** 阈值 */
  threshold: number
  /** 是否已解决 */
  resolved: boolean
}

/** 告警摘要 */
export interface AlertSummary {
  /** 总告警数 */
  total: number
  /** 未解决告警数 */
  unresolved: number
  /** 严重告警数 */
  critical: number
  /** 错误告警数 */
  error: number
  /** 警告告警数 */
  warning: number
  /** 信息告警数 */
  info: number
}

/** 刷新响应 */
export interface RefreshResponse {
  success: boolean
  message: string
  metrics: DataQualityMetrics
  new_alerts_count: number
}

/** 解决告警响应 */
export interface ResolveAlertResponse {
  success: boolean
  message: string
  alert_id: string
}

/** 类型守卫：检查是否为 DataQualityMetrics */
export function isDataQualityMetrics(obj: unknown): obj is DataQualityMetrics {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'timestamp' in obj &&
    'source_availability' in obj &&
    'data_latency_ms' in obj
  )
}

/** 类型守卫：检查是否为 Alert */
export function isAlert(obj: unknown): obj is Alert {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'id' in obj &&
    'severity' in obj &&
    'title' in obj &&
    'message' in obj
  )
}

/** 类型守卫：检查是否为 Alert 数组 */
export function isAlertArray(obj: unknown): obj is Alert[] {
  return Array.isArray(obj) && obj.every(isAlert)
}

/** 类型守卫：检查是否为 AlertSummary */
export function isAlertSummary(obj: unknown): obj is AlertSummary {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'total' in obj &&
    'unresolved' in obj
  )
}
