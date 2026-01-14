/**
 * 实时行情 API
 *
 * 提供股票实时行情数据和市场状态查询功能
 */

import { ApiClient, ApiResponse } from './request'

// 实时行情数据接口
export interface RealtimeQuote {
  symbol: string
  name?: string
  price: number
  change: number
  change_pct: number
  open?: number
  high?: number
  low?: number
  pre_close?: number
  volume?: number
  amount?: number
  market_status: string
  market_status_desc: string
  is_realtime: boolean
  timestamp: string
  source: string
}

// 市场状态接口
export interface MarketStatus {
  market_type: string
  status: string
  status_desc: string
  is_trading_day: boolean
  next_session?: {
    start: string
    end: string
  }
}

// 批量行情响应接口
export interface BatchQuotesResponse {
  quotes: Record<string, RealtimeQuote>
  failed: string[]
  success_count: number
  failed_count: number
}

// 是否使用实时数据响应接口
export interface ShouldUseRealtimeResponse {
  should_use: boolean
  reason: string
  analysis_date: string
  is_today: boolean
  market_status: string
  market_status_desc: string
  is_trading_hours: boolean
}

/**
 * 获取单只股票的实时行情
 * @param symbol 股票代码（6位数字，如 000001）
 * @param marketType 市场类型（A股/港股/美股）
 */
export async function getRealtimeQuote(
  symbol: string,
  marketType: string = 'A股'
): Promise<ApiResponse<RealtimeQuote>> {
  return await ApiClient.get(`/api/realtime/quote/${symbol}`, {
    market_type: marketType
  })
}

/**
 * 批量获取股票实时行情
 * @param symbols 股票代码列表（最多50只）
 * @param marketType 市场类型
 */
export async function getRealtimeQuotesBatch(
  symbols: string[],
  marketType: string = 'A股'
): Promise<ApiResponse<BatchQuotesResponse>> {
  return await ApiClient.post('/api/realtime/quotes/batch', {
    symbols,
    market_type: marketType
  })
}

/**
 * 获取市场状态
 * @param marketType 市场类型（A股/港股/美股）
 */
export async function getMarketStatus(
  marketType: string = 'A股'
): Promise<ApiResponse<MarketStatus>> {
  return await ApiClient.get('/api/realtime/market-status', {
    market_type: marketType
  })
}

/**
 * 判断是否应该使用实时数据
 * @param analysisDate 分析日期（YYYY-MM-DD 或 'today'）
 * @param marketType 市场类型
 */
export async function shouldUseRealtime(
  analysisDate: string,
  marketType: string = 'A股'
): Promise<ApiResponse<ShouldUseRealtimeResponse>> {
  return await ApiClient.get('/api/realtime/should-use-realtime', {
    analysis_date: analysisDate,
    market_type: marketType
  })
}

// 默认导出所有方法
export default {
  getRealtimeQuote,
  getRealtimeQuotesBatch,
  getMarketStatus,
  shouldUseRealtime
}
