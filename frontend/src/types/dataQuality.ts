/**
 * 数据质量监控相关类型定义
 */

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

/** API 响应类型 */
export interface MetricsResponse extends DataQualityMetrics {}

export interface AlertsResponse {
  alerts: Alert[]
}

export interface AlertSummaryResponse extends AlertSummary {}

export interface RefreshResponse {
  success: boolean
  message: string
  metrics: DataQualityMetrics
  new_alerts_count: number
}

export interface ResolveAlertResponse {
  success: boolean
  message: string
  alert_id: string
}
