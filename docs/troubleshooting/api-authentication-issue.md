# API认证问题诊断报告

## 问题描述

```
tradingagents-backend | 2026-01-22 13:21:18,863 | WARNING  | auth_db
❌ 没有Authorization header

tradingagents-backend | 2026-01-22 13:21:18 | INFO     | webapi
❌  GET /api/realtime/quote/AAPL - 状态: 401 - 耗时: 0.018s trace=d0474038-8c7a-45b1-ae23-f3689ac87fd
```

## 问题分析

### 1. 后端认证机制

**文件**: `app/routers/auth_db.py`

`get_current_user()` 函数通过 FastAPI 的 `Header` 依赖项获取 Authorization header：

```python
async def get_current_user(authorization: Optional[str] = Header(default=None)) -> dict:
    if not authorization:
        logger.warning("❌ 没有Authorization header")
        raise HTTPException(status_code=401, detail="No authorization header")

    if not authorization.lower().startswith("bearer "):
        logger.warning(f"❌ Authorization header格式错误: {authorization[:20]}...")
        raise HTTPException(status_code=401, detail="Invalid authorization format")

    token = authorization.split(" ", 1)[1]
    token_data = AuthService.verify_token(token)

    # ... 后续验证逻辑
```

**实时行情端点** (`app/routers/realtime.py:62-67`):

```python
@router.get("/quote/{symbol}", response_model=dict)
async def get_realtime_quote(
    symbol: str,
    market_type: str = Query(default="A股", description="市场类型: A股/港股/美股"),
    current_user: dict = Depends(get_current_user)  # ← 需要认证
):
```

### 2. 前端认证流程

**Auth Store** (`frontend/src/stores/auth.ts`):

初始化时验证 token 格式：

```typescript
const isValidToken = (token: string | null): boolean => {
  if (!token || typeof token !== 'string') return false
  // 检查是否是mock token
  if (token === 'mock-token' || token.startsWith('mock-')) {
    console.warn('⚠️ 检测到mock token，将被清除:', token)
    return false
  }
  // JWT token应该有3个部分，用.分隔
  return token.split('.').length === 3
}

const validToken = isValidToken(token) ? token : null

// 如果token无效，清除相关数据
if (!validToken || !validRefreshToken) {
  console.log('🧹 清除无效的认证信息')
  localStorage.removeItem('auth-token')
  localStorage.removeItem('refresh-token')
  localStorage.removeItem('user-info')
}
```

**Axios 拦截器** (`frontend/src/api/request.ts:96-121`):

```typescript
// 请求拦截器
instance.interceptors.request.use((config: any) => {
  const authStore = useAuthStore()

  // 添加认证头
  if (!config.skipAuth) {
    const token = authStore.token || localStorage.getItem('auth-token')
    if (token) {
      config.headers = config.headers || {}
      config.headers.Authorization = `Bearer ${token}`
      console.log('🔐 已设置Authorization头:', {...})
    } else {
      console.log('⚠️ 未设置Authorization头:', {
        skipAuth: config.skipAuth,
        hasToken: !!authStore.token,
        localStored: !!localStorage.getItem('auth-token'),
        url: config.url
      })
    }
  }
  return config
})
```

**实时行情 API 调用** (`frontend/src/api/realtime.ts:69-71`):

```typescript
export async function getRealtimeQuote(
  symbol: string,
  marketType: string = 'A股'
): Promise<ApiResponse<RealtimeQuote>> {
  return await ApiClient.get(`/api/realtime/quote/${symbol}`, {
    market_type: marketType
  })
}
```

### 3. 问题根因

前端请求 `/api/realtime/quote/AAPL` 时没有携带 `Authorization` header，导致后端返回 401。

**可能的原因**：

1. **用户未登录** - `authStore.token` 为 `null`，`localStorage` 中也没有有效的 token
2. **Token 格式无效** - Auth store 初始化时检测到 token 格式不正确（不是 JWT 格式），自动清除
3. **Token 过期** - Token 已过期，前端尝试刷新失败
4. **请求时机问题** - 在登录完成前就发起了请求

## 解决方案

### 方案 1: 确保用户登录（推荐）

前端在调用需要认证的 API 之前，应确保用户已登录：

```typescript
// 在调用 getRealtimeQuote 之前检查
const authStore = useAuthStore()
if (!authStore.isAuthenticated) {
  ElMessage.warning('请先登录')
  router.push('/login')
  return
}

// 已登录，可以调用 API
const quote = await getRealtimeQuote('AAPL', '美股')
```

### 方案 2: 检查浏览器控制台日志

打开浏览器开发者工具（F12），查看 Console 标签页，寻找以下日志：

- `⚠️ 未设置Authorization头:` - 说明没有 token
- `⚠️ 检测到mock token，将被清除:` - 说明使用了测试 token
- `🧹 清除无效的认证信息` - 说明 token 格式无效
- `🔐 已设置Authorization头:` - 说明 token 正常设置（但后端仍报 401，可能是其他问题）

### 方案 3: 检查 LocalStorage

在浏览器控制台执行：

```javascript
console.log('auth-token:', localStorage.getItem('auth-token'))
console.log('refresh-token:', localStorage.getItem('refresh-token'))
console.log('user-info:', localStorage.getItem('user-info'))
```

如果 `auth-token` 为 `null` 或不是 JWT 格式（应该有3个部分，用 `.` 分隔），说明认证信息丢失或无效。

### 方案 4: 重新登录

清除所有认证信息，重新登录：

1. 在浏览器中手动清除 localStorage：
   - 打开开发者工具 → Application → Local Storage
   - 删除 `auth-token`、`refresh-token`、`user-info`

2. 刷新页面，重新登录

### 方案 5: 检查后端日志

查看完整的后端日志，确认：

1. 是否有 `🔐 认证检查开始` 日志
2. Authorization header 的值是什么（即使为 null）
3. 是否有其他相关错误（如 token 验证失败、用户不存在等）

```bash
# 查看实时日志
docker-compose logs -f backend | grep -E "auth_db|Authorization|认证"
```

### 方案 6: 手动测试 API

使用 curl 或 Postman 测试 API，确认后端正常工作：

```bash
# 1. 先登录获取 token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"your_username","password":"your_password"}'

# 2. 使用 token 调用实时行情 API
curl -X GET "http://localhost:8000/api/realtime/quote/AAPL?market_type=美股" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## 预防措施

### 1. 前端路由守卫

在路由配置中添加认证检查，防止未登录用户访问需要认证的页面：

```typescript
// frontend/src/router/index.ts
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  const requiresAuth = to.meta.requiresAuth

  if (requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else {
    next()
  }
})
```

### 2. 全局错误处理

前端的 401 错误处理已经实现（`frontend/src/api/request.ts:239-272`），会自动：
- 尝试刷新 token
- 刷新失败后清除认证信息
- 跳转到登录页

确保这个逻辑正常工作。

### 3. Token 自动刷新

前端已有 token 自动刷新机制（`frontend/src/stores/auth.ts:264-313`），在 token 过期前自动刷新。

检查自动刷新定时器是否正常启动：

```typescript
// 在登录成功后启动
const { setupTokenRefreshTimer } = await import('@/utils/auth')
setupTokenRefreshTimer()
```

## 调试步骤

1. **清除浏览器缓存和 localStorage**
2. **重新登录**
3. **打开开发者工具 → Console 标签页**
4. **触发实时行情请求**
5. **观察日志**：
   - 前端：`🔐 已设置Authorization头:` 或 `⚠️ 未设置Authorization头:`
   - 后端：`🔐 认证检查开始` 和 Authorization header 信息
6. **对比前后端日志**，找出不一致的地方

## 常见问题

### Q1: Token 格式应该是什么样的？

**A**: JWT token 应该是 3 部分组成，用 `.` 分隔：

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM...SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
```

### Q2: 为什么 token 会自动被清除？

**A**: Auth store 初始化时会检查 token 格式，以下情况会自动清除：
- Token 不是字符串
- Token 是 mock token（以 `mock-` 开头）
- Token 格式不正确（不是 JWT 格式）

### Q3: 如何启用后端详细日志？

**A**: 在 `.env` 文件中设置：

```env
DEBUG=True
LOG_LEVEL=DEBUG
```

或者通过 Web UI：系统设置 → 日志配置 → 设置日志级别为 DEBUG

## 相关文件

- 后端认证逻辑：`app/routers/auth_db.py`
- 后端实时行情 API：`app/routers/realtime.py`
- 前端 Auth Store：`frontend/src/stores/auth.ts`
- 前端请求拦截器：`frontend/src/api/request.ts`
- 前端实时行情 API：`frontend/src/api/realtime.ts`
