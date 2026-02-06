/**
 * 数据质量监控 API
 */

import { ApiClient } from './request'
import type {
  DataQualityMetrics,
  Alert,
  AlertSummary,
  RefreshResponse,
  ResolveAlertResponse
} from '@/types/dataQuality'

export const dataQualityApi = {
  /**
   * 获取当前数据质量指标
   */
  getMetrics: () =>
    ApiClient.get<DataQualityMetrics>('/api/data-quality/metrics'),

  /**
   * 获取历史指标数据
   * @param limit 返回记录数量
   */
  getMetricsHistory: (limit: number = 100) =>
    ApiClient.get<DataQualityMetrics[]>('/api/data-quality/metrics/history', {
      params: { limit }
    }),

  /**
   * 获取告警列表
   * @param limit 返回告警数量
   * @param resolved 筛选已解决/未解决的告警
   * @param severity 按严重程度筛选
   */
  getAlerts: (
    limit: number = 50,
    resolved?: boolean,
    severity?: string
  ) =>
    ApiClient.get<Alert[]>('/api/data-quality/alerts', {
      params: { limit, resolved, severity }
    }),

  /**
   * 获取告警摘要统计
   */
  getAlertSummary: () =>
    ApiClient.get<AlertSummary>('/api/data-quality/alerts/summary'),

  /**
   * 标记告警为已解决
   * @param alertId 告警ID
   */
  resolveAlert: (alertId: string) =>
    ApiClient.post<ResolveAlertResponse>(`/api/data-quality/alerts/${alertId}/resolve`),

  /**
   * 刷新数据质量指标
   */
  refresh: () =>
    ApiClient.post<RefreshResponse>('/api/data-quality/refresh')
}
