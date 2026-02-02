# Dead Code Analysis Report

**Project**: TradingAgents-CN
**Date**: 2026-02-02
**Analyzed by**: Claude Code

---

## Summary

| Category | Count | Severity |
|----------|-------|----------|
| Unused Imports (Python) | 45+ | Low |
| Unused Variables | 8 | Low |
| Unreachable Code | 4 | Medium |
| Unused Dependencies (Frontend) | 7 | Low |

---

## Python Backend Analysis

### Unused Imports (Safe to Remove)

#### app/ directory
1. `app/core/config_compat.py:14` - `lru_cache` (90% confidence)
2. `app/core/database.py:15` - `RedisConnectionError` (90% confidence)
3. `app/core/logging_config.py:15` - `ConcurrentRotatingFileHandler` (90% confidence)
4. `app/main.py:349` - `croniter` (90% confidence)
5. `app/models/user.py:10-11` - `JsonSchemaValue`, `core_schema` (90% confidence)
6. `app/routers/analysis.py:29` - `AnalysisBatchResponse`, `AnalysisHistoryQuery`, `AnalysisTaskResponse` (90% confidence)
7. `app/routers/config.py:13` - `ConfigTestResponse` (90% confidence)
8. `app/routers/config.py:83` - `deepcopy` (90% confidence)
9. `app/services/data_sources/baostock_adapter.py` - unreachable code after 'return' (100% confidence)
10. `app/services/database_service.py:15` - `motor` (90% confidence)
11. `app/services/queue_service.py:19` - `GLOBAL_CONCURRENT_KEY` (90% confidence)
12. `app/services/unified_cache_service.py:23` - `PyMongoError` (90% confidence)

#### tradingagents/ directory
1. `tradingagents/agents/analysts/fundamentals_analyst.py:2` - `ChatPromptTemplate`, `MessagesPlaceholder` (90% confidence)
2. `tradingagents/agents/analysts/market_analyst.py:2` - `ChatPromptTemplate`, `MessagesPlaceholder` (90% confidence)
3. `tradingagents/agents/analysts/news_analyst.py:2` - `ChatPromptTemplate`, `MessagesPlaceholder` (90% confidence)
4. `tradingagents/agents/analysts/social_media_analyst.py:2` - `ChatPromptTemplate`, `MessagesPlaceholder` (90% confidence)
5. `tradingagents/agents/utils/agent_states.py:2` - `Sequence` (90% confidence)
6. `tradingagents/agents/utils/agent_states.py:7` - `ToolNode` (90% confidence)
7. `tradingagents/agents/utils/agent_utils.py:5` - `ChatPromptTemplate`, `MessagesPlaceholder` (90% confidence)
8. `tradingagents/agents/utils/agent_utils.py:20` - `log_analysis_step` (90% confidence)
9. `tradingagents/config/runtime_settings.py:181` - `_Optional` (90% confidence)
10. `tradingagents/dataflows/cache/db_cache.py:35` - `RedisConnectionError` (90% confidence)
11. `tradingagents/dataflows/news/reddit.py:6` - `contextmanager` (90% confidence)
12. `tradingagents/dataflows/optimized_china_data.py:26` - `get_financial_data_with_fallback` (90% confidence)
13. `tradingagents/llm_adapters/dashscope_openai_adapter.py:9` - `Sequence` (90% confidence)
14. `tradingagents/llm_adapters/dashscope_openai_adapter.py:12` - `SecretStr` (90% confidence)
15. `tradingagents/llm_adapters/deepseek_adapter.py:9` - `SystemMessage` (90% confidence)
16. `tradingagents/llm_adapters/google_openai_adapter.py:9` - `Sequence` (90% confidence)
17. `tradingagents/llm_adapters/google_openai_adapter.py:12` - `SystemMessage` (90% confidence)
18. `tradingagents/llm_adapters/google_openai_adapter.py:14` - `SecretStr` (90% confidence)
19. `tradingagents/utils/financial_calendar.py:19` - `calendar` (90% confidence)

#### web/ directory
1. `web/app.py:39` - `check_authentication`, `render_user_info` (90% confidence)
2. `web/app.py:40` - `render_activity_summary_widget`, `render_user_activity_dashboard` (90% confidence)
3. `web/run_web.py:31` - `plotly` (90% confidence)
4. `web/utils/persistence.py:9` - `parse_qs`, `urlencode` (90% confidence)
5. `web/utils/report_exporter.py:42` - `get_docker_pdf_extra_args` (90% confidence)

### Unused Variables (Safe to Remove)

1. `app/services/data_sources/data_consistency_checker.py:34-36` - `secondary`, `primary_name`, `secondary_name` (100% confidence)
2. `app/services/data_sources/data_consistency_checker.py:44` - `secondary` (100% confidence)
3. `app/worker/analysis_worker.py:52` - `frame` (100% confidence)
4. `tradingagents/config/config_manager.py:838` - `current_cost` (100% confidence)
5. `tradingagents/dataflows/providers/base_provider.py:412` - `exc_type`, `exc_val`, `exc_tb` (100% confidence)
6. `tradingagents/graph/reflection.py:64` - `component_type` (100% confidence)
7. `web/run_web.py:249` - `frame` (100% confidence)

### Unreachable Code (Requires Manual Review)

1. `app/services/data_sources/baostock_adapter.py:339` - unreachable code after 'return' (100% confidence)
2. `tradingagents/dataflows/cache/mongodb_cache_adapter.py:279` - unreachable code after 'return' (100% confidence)
3. `tradingagents/dataflows/providers/us/alpha_vantage_common.py:141` - unreachable code after 'raise' (100% confidence)

### Test Files - Unused Imports (Safe to Remove)

1. `tests/config/test_logging_config.py:28` - `caplog` (100% confidence)
2. `tests/conftest.py` - Multiple unused fixtures and imports (see full vulture report)
3. `tests/e2e/test_complete_workflows.py:25` - `test_user_token` (100% confidence)
4. `tests/services/test_quotes_backfill.py:38` - `ordered` (100% confidence)
5. `tests/services/test_quotes_ingestion_and_enrichment.py:106` - `ordered` (100% confidence)
6. `tests/tradingagents/test_app_cache_toggle.py:3` - `builtins` (90% confidence)
7. `tests/unit/services/test_auth_service.py:18` - `JWTError` (90% confidence)
8. `tests/unit/tools/analysis/test_indicators_uil.py:1` - `math` (90% confidence)

---

## Frontend Analysis

### Unused Dependencies (from depcheck)

**Unused dependencies:**
- `@types/sortablejs`
- `diff`
- `lodash-es`
- `mermaid`
- `vue3-markdown-it`

**Unused devDependencies:**
- `@types/lodash-es`
- `@typescript-eslint/eslint-plugin`
- `@typescript-eslint/parser`
- `@vue/compiler-sfc`
- `@vue/eslint-config-prettier`
- `@vue/eslint-config-typescript`
- `eslint-plugin-vue`

**Missing dependencies:**
- `@rushstack/eslint-patch`
- `vitest`

### ts-prune Results

The ts-prune output shows many exports that are marked as "(used in module)" which means they are used within their own module but not exported elsewhere. This is normal for API modules.

**No critical dead code found** in TypeScript exports - most exported items are part of the API layer and are used through the module system.

---

## Safe Deletion Priority

### Phase 1: Unused Imports (Safest)
- All unused imports listed above
- These have no side effects

### Phase 2: Unused Variables (Safe)
- Variables that are assigned but never read
- Exception handler variables that are unused

### Phase 3: Unreachable Code (Caution)
- Code after return/raise statements
- Verify logic before deleting

### Phase 4: Frontend Dependencies (Caution)
- Verify each dependency is truly unused
- Check for dynamic imports

---

## Recommendations

1. **Start with unused imports** - They are the safest to remove
2. **Run tests after each deletion** - Ensure nothing breaks
3. **Manual review for unreachable code** - Verify business logic
4. **Check frontend dependencies carefully** - May be used dynamically

---

## Files Modified

| File | Changes |
|------|---------|
| See safe-deletions.md | List of all deletions |

---

*Generated by Claude Code on 2026-02-02*
