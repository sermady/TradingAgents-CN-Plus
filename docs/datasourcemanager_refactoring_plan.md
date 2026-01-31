# DataSourceManager Refactoring Plan

**Date**: 2026-01-31
**Target**: `tradingagents/dataflows/data_source_manager.py` (5,051 lines, 86 methods)

---

## Current State Analysis

### File Statistics
- **Total Lines**: 5,051
- **Total Methods**: 86
- **Classes**: 2 (DataSourceManager, USDataSourceManager)
- **Responsibilities**: 10+ distinct areas

### Code Smells
1. **God Class**: Way too many responsibilities
2. **High Coupling**: Everything depends on everything
3. **Low Cohesion**: Unrelated methods in same class
4. **Duplication**: Similar patterns repeated across methods
5. **Complexity**: Hard to test, hard to maintain

---

## Functional Area Breakdown

### 1. Configuration & Initialization (Lines 66-467)
**Methods**:
- `__init__`
- `_check_mongodb_enabled`
- `_get_default_source`
- `_check_available_sources`
- `_get_data_source_priority_order`
- `_identify_market_category`
- `get_current_source`
- `set_current_source`
- `_get_datasource_configs_from_db`

**Responsibility**: Setup, config loading, source selection

---

### 2. Data Adapters Management (Lines 638-698)
**Methods**:
- `_get_data_adapter`
- `_get_mongodb_adapter`
- `_get_tushare_adapter`
- `_get_akshare_adapter`
- `_get_baostock_adapter`

**Responsibility**: Provider instance management

---

### 3. Caching System (Lines 700-838)
**Methods**:
- `_get_cached_data`
- `_save_to_cache`
- `_get_smart_ttl`
- `_get_storage_location`
- `_get_volume_safely`
- `_format_stock_data_response`

**Responsibility**: Multi-level caching logic

---

### 4. Real-time Quotes (Lines 1488-1850)
**Methods**:
- `get_realtime_quote` ⭐ PRIMARY API
- `_get_realtime_quote_config`
- `_get_tushare_realtime_quote`
- `_get_tushare_realtime_quote_with_retry`
- `_get_akshare_realtime_quote`
- `_get_akshare_realtime_quote_with_retry`
- `_update_price_cache`

**Responsibility**: Real-time market data fetching

---

### 5. Historical Data (Lines 1316-2617)
**Methods**:
- `get_stock_dataframe` ⭐ PRIMARY API
- `get_stock_data` ⭐ PRIMARY API
- `get_stock_data_with_fallback` ⭐ PRIMARY API
- `_standardize_dataframe`
- `_get_mongodb_data`
- `_get_tushare_data`
- `_get_akshare_data`
- `_get_baostock_data`
- `_get_baostock_data_async`
- `_run_async_safe`
- `_try_fallback_sources`
- `_merge_realtime_quote_to_result`

**Responsibility**: Historical OHLCV data fetching

---

### 6. Stock Information (Lines 2617-3293)
**Methods**:
- `get_stock_info` ⭐ PRIMARY API
- `get_stock_basic_info` ⭐ PRIMARY API
- `_get_tushare_stock_info`
- `_get_akshare_stock_info`
- `_get_baostock_stock_info`
- `_try_fallback_stock_info`
- `_parse_stock_info_string`

**Responsibility**: Stock metadata and basic info

---

### 7. Fundamentals Data (Lines 277-370, 3293-4038)
**Methods**:
- `get_fundamentals_data` ⭐ PRIMARY API
- `get_china_stock_fundamentals_tushare`
- `_get_mongodb_fundamentals`
- `_get_tushare_fundamentals`
- `_get_tushare_financial_indicators`
- `_get_tushare_financial_reports`
- `_get_akshare_fundamentals`
- `_get_valuation_indicators`
- `_format_financial_data`
- `_generate_fundamentals_analysis`
- `_try_fallback_fundamentals`

**Responsibility**: Financial data and fundamentals

---

### 8. News Data (Lines 383-467, 3939-4038)
**Methods**:
- `get_news_data` ⭐ PRIMARY API
- `_get_mongodb_news`
- `_get_tushare_news`
- `_get_akshare_news`
- `_try_fallback_news`

**Responsibility**: News and sentiment data

---

### 9. Data Quality & Validation (Lines 4038-4623)
**Methods**:
- `get_data_quality_score` ⭐ PRIMARY API
- `_check_data_completeness`
- `_check_data_consistency`
- `_check_data_timeliness`
- `_check_data_source_reliability`
- `get_best_source_for_metric`
- `is_realtime_capable`
- `_is_trading_hours`
- `get_data_with_validation`
- `cross_validate_metric`
- `_analyze_cross_validation_results`
- `_parse_data_string`

**Responsibility**: Data quality assessment and validation

---

### 10. US Market Data (Lines 4768-5051)
**Class**: USDataSourceManager

**Methods**:
- `__init__`
- `_check_mongodb_enabled`
- `_get_default_source`
- `_check_available_sources`
- `_get_enabled_sources_from_db`
- `_get_datasource_configs_from_db`
- `get_current_source`
- `set_current_source`

**Responsibility**: US stock data management (already separate class)

---

## Proposed Component Structure

```
tradingagents/dataflows/
├── data_source_manager.py          # Reduced to ~800 lines (facade/contract)
├── providers/
│   ├── __init__.py
│   ├── base_provider.py            # Already exists
│   ├── china/
│   │   ├── tushare.py              # Already exists
│   │   ├── akshare.py              # Already exists
│   │   └── baostock.py             # Already exists
│   └── composite/                  # NEW: Composite providers
│       ├── __init__.py
│       ├── realtime_quote_provider.py    # Extract from DSM
│       ├── historical_data_provider.py   # Extract from DSM
│       ├── stock_info_provider.py        # Extract from DSM
│       ├── fundamentals_provider.py      # Extract from DSM
│       └── news_provider.py              # Extract from DSM
├── routing/
│   ├── __init__.py
│   └── data_source_router.py       # NEW: Routing and fallback logic
├── quality/
│   ├── __init__.py
│   └── data_quality_manager.py     # NEW: Quality assessment
└── cache/
    └── cache_manager.py            # Already exists (enhance)
```

---

## Phased Implementation Plan

### Phase 1: Foundation (Week 1)
1. Create new directory structure
2. Implement `DataSourceRouter` - Extract routing/fallback logic
3. Implement `RealtimeQuoteProvider` - Most critical and isolated
4. Keep `DataSourceManager` as facade, delegate to new components
5. Full backward compatibility

### Phase 2: Core Data (Week 2)
1. Implement `HistoricalDataProvider`
2. Implement `StockInfoProvider`
3. Update `DataSourceManager` to use providers
4. Add deprecation warnings for old methods

### Phase 3: Specialized Data (Week 3)
1. Implement `FundamentalsProvider`
2. Implement `NewsProvider`
3. Implement `DataQualityManager`
4. Complete facade delegation

### Phase 4: Cleanup (Week 4)
1. Remove old method implementations
2. Keep only facade/API layer
3. Update all imports across codebase
4. Comprehensive testing

---

## Extraction Priority

### Priority 1: RealtimeQuoteProvider
**Why**:
- Isolated functionality
- Critical for trading
- Clear boundaries
- Easy to test

**Scope**: Lines 1488-1850 (~362 lines)

### Priority 2: DataSourceRouter
**Why**:
- Core infrastructure
- Enables other refactors
- Fallback logic is reusable

**Scope**: Routing logic scattered across file

### Priority 3: HistoricalDataProvider
**Why**:
- Most frequently used
- Complex fallback chains
- Big impact on file size

**Scope**: Lines 1316-2617 (~1,301 lines)

### Priority 4: StockInfoProvider
**Why**:
- Clean separation
- Well-defined API
- Medium complexity

**Scope**: Lines 2617-3293 (~676 lines)

---

## Risk Mitigation

### Backward Compatibility
- Keep `DataSourceManager` as facade
- All existing methods remain
- Delegate to new components
- Add deprecation warnings in Phase 3

### Testing Strategy
1. Extract with tests
2. Keep old tests passing
3. Add new component tests
4. Integration tests for facade

### Rollback Plan
- Each phase is independent
- Git tags at each phase
- Can revert individual components
- Facade pattern allows gradual migration

---

## Success Metrics

1. **File Size**: Reduce from 5,051 lines to < 1,000 lines
2. **Method Count**: Reduce from 86 to < 20 (facade only)
3. **Test Coverage**: Maintain or improve
4. **Complexity**: Reduce cyclomatic complexity by 50%
5. **Coupling**: Each component < 5 dependencies

---

## Next Steps

1. ✅ **Current**: Complete analysis and planning
2. 🔄 **Next**: Create component extraction structure
3. ⏳ **Then**: Implement RealtimeQuoteProvider (Priority 1)
4. ⏳ **Then**: Implement DataSourceRouter
5. ⏳ **Then**: Refactor DataSourceManager facade

---

**Status**: Planning Complete - Ready for Implementation
