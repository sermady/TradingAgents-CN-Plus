# TradingAgents-CN Critical 修复部署检查清单

## 📋 部署前准备

### 1. 环境检查
- [ ] Python 版本 >= 3.11
- [ ] MongoDB 服务运行正常
- [ ] Redis 服务运行正常（如使用）
- [ ] 生产环境 `.env` 配置正确

### 2. 依赖安装
```bash
# 必需依赖
pip install bcrypt>=4.0.0

# 验证安装
python -c "import bcrypt; print('bcrypt:', bcrypt.__version__)"
```

### 3. 数据库备份 ⚠️
```bash
# MongoDB 备份（必需！）
mongodump --uri="mongodb://localhost:27017/tradingagents" --out=/backup/pre-security-fix-$(date +%Y%m%d)

# 验证备份
ls -lh /backup/pre-security-fix-*/
```

---

## 🚀 部署步骤

### 步骤 1：代码部署
```bash
# 1. 拉取最新代码
git pull origin main

# 2. 验证提交
# 确认以下提交存在：
# - 89c9d3a fix(security): 修复 WebSocket 硬编码用户 ID
# - 3fb9d61 fix(security): 替换 SHA-256 为 bcrypt
# - d3d8d91 fix(security): 清理日志中的敏感信息
# - 07ee3e6 fix(concurrency): 修复事件循环冲突
# - 302fa9b fix(concurrency): 完成 threading.Lock 替换

git log --oneline -5
```

### 步骤 2：配置文件检查
```bash
# 检查 JWT 配置
# 确保 .env 中有：
# JWT_SECRET=your-secure-secret-key-min-32-chars
# JWT_ALGORITHM=HS256
# JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

grep "JWT_" .env
```

### 步骤 3：数据库迁移
```bash
# 无需手动迁移脚本
# bcrypt 会自动处理旧密码升级
# 但需要确保 users 集合有以下索引：

python << 'EOF'
from pymongo import MongoClient
client = MongoClient("mongodb://localhost:27017/")
db = client["tradingagents"]

# 检查并创建索引
required_indexes = [
    ("users", [("username", 1)], True),  # 唯一索引
    ("users", [("email", 1)], False),
]

for coll_name, fields, unique in required_indexes:
    coll = db[coll_name]
    try:
        coll.create_index(fields, unique=unique)
        print(f"✅ 索引创建成功: {coll_name} {fields}")
    except Exception as e:
        print(f"⚠️ 索引已存在或出错: {e}")

print("数据库准备完成！")
EOF
```

### 步骤 4：服务重启
```bash
# 1. 优雅停止现有服务
# 如果是 systemd:
sudo systemctl stop tradingagents

# 如果是 docker:
docker-compose down

# 如果是直接运行，找到进程并终止:
pkill -f "python.*main.py" || true

# 2. 等待确保端口释放
sleep 3

# 3. 清理缓存（可选但建议）
redis-cli FLUSHDB || true

# 4. 启动服务
# 方式 A: 直接运行
python -m app.main &

# 方式 B: systemd
sudo systemctl start tradingagents

# 方式 C: docker
docker-compose up -d
```

---

## 🧪 部署验证测试

### 测试 1：WebSocket 权限修复验证
```bash
# 使用 wscat 或浏览器测试
# 预期：连接后 user_id 应正确显示在日志中

tail -f logs/app.log | grep -E "\[WS\].*user=" &

# 在浏览器控制台执行：
# new WebSocket('ws://localhost:8000/api/ws/notifications?token=YOUR_TOKEN')

# 验证日志中出现类似：
# ✅ [WS] 新连接: user=actual_username, ...
# 而不是：
# ✅ [WS] 新连接: user=admin, ...
```

### 测试 2：bcrypt 密码验证
```bash
# 测试 A：新用户注册（bcrypt）
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"test_new","password":"testpass123","email":"test@example.com"}'

# 验证数据库中 password_version = "bcrypt"
python << 'EOF'
from pymongo import MongoClient
client = MongoClient("mongodb://localhost:27017/")
db = client["tradingagents"]
user = db.users.find_one({"username": "test_new"})
if user:
    print(f"密码版本: {user.get('password_version', 'N/A')}")
    print(f"哈希前缀: {user['hashed_password'][:10]}")
    assert user.get('password_version') == 'bcrypt', "密码版本不是 bcrypt"
    assert user['hashed_password'].startswith('$2'), "哈希格式不正确"
    print("✅ 新用户密码使用 bcrypt")
EOF

# 测试 B：旧用户登录（自动迁移）
# 使用旧 SHA-256 密码登录，验证自动升级
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"old_user","password":"old_password"}'

# 验证数据库中 password_version 已更新为 "bcrypt"
python << 'EOF'
from pymongo import MongoClient
client = MongoClient("mongodb://localhost:27017/")
db = client["tradingagents"]
user = db.users.find_one({"username": "old_user"})
if user and user.get('password_version') == 'bcrypt':
    print("✅ 旧用户密码自动升级到 bcrypt")
EOF
```

### 测试 3：日志脱敏验证
```bash
# 检查日志中没有敏感信息
grep -E "(JWT_SECRET|api_key|password)" logs/app.log | head -10

# 预期：无匹配或显示已脱敏（如：sk-***123）

# 验证 WebSocket 日志没有硬编码 admin
grep "user=admin" logs/app.log | grep -v "用户不存在"
# 预期：无匹配（除了可能的旧日志）
```

### 测试 4：事件循环稳定性
```bash
# 测试财务数据获取（可能触发事件循环冲突的场景）
curl -X POST http://localhost:8000/api/analysis/simple \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"ticker":"000001","analysis_depth":"快速"}'

# 检查日志中没有 RuntimeError
grep "event loop already running" logs/app.log
# 预期：无匹配

# 检查日志中没有 asyncio.run 错误
grep "asyncio.run" logs/app.log | grep -i error
# 预期：无匹配
```

### 测试 5：并发性能测试
```bash
# 测试 AKShare 实时行情获取（高并发）
python << 'EOF'
import asyncio
import aiohttp

async def test_concurrent_quotes():
    async with aiohttp.ClientSession() as session:
        tasks = []
        for code in ['000001', '000002', '000333', '600000']:
            task = session.get(
                f'http://localhost:8000/api/stocks/{code}/realtime',
                headers={'Authorization': 'Bearer YOUR_TOKEN'}
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        success = sum(1 for r in results if not isinstance(r, Exception))
        print(f"并发请求: {len(tasks)}, 成功: {success}")
        
        # 验证没有异常
        errors = [r for r in results if isinstance(r, Exception)]
        if errors:
            print(f"❌ 错误: {errors}")
        else:
            print("✅ 并发测试通过")

asyncio.run(test_concurrent_quotes())
EOF
```

---

## 🔄 回滚预案

### 如果出现问题，回滚步骤：

#### 回滚 A：WebSocket 修复（如有问题）
```bash
# 回滚到修复前版本
git revert 89c9d3a

# 或手动修改：
# 将 websocket_notifications.py 中的 user_id 解析代码改回硬编码
git checkout 89c9d3a~1 -- app/routers/websocket_notifications.py
```

#### 回滚 B：bcrypt 密码（如有问题）
```bash
# 注意：bcrypt 修复难以直接回滚，因为数据库已更新
# 建议方案：

# 1. 紧急恢复 SHA-256 验证（临时）
# 修改 user_service.py，在 verify_password 中优先使用 SHA-256

# 2. 更安全的方案：降级到兼容模式
# 保持 bcrypt hash_password，但 verify_password 同时支持两种格式
# （当前已实现）

# 3. 如果必须完全回滚，需要从备份恢复数据库
mongorestore --uri="mongodb://localhost:27017/tradingagents" /backup/pre-security-fix-YYYYMMDD/
```

#### 回滚 C：完全回滚所有修复
```bash
# 找到部署前的提交
git log --oneline --before="2026-01-31" -5

# 硬回滚（危险！会丢失数据）
git reset --hard DEPLOY_COMMIT_HASH

# 或软回滚（保留更改）
git revert 89c9d3a 3fb9d61 d3d8d91 07ee3e6 302fa9b
```

---

## 📊 部署后监控

### 关键指标检查（部署后 1 小时内）

```bash
# 1. 检查错误率
tail -1000 logs/app.log | grep -E "(ERROR|Exception)" | wc -l
# 预期：正常范围（< 10）

# 2. 检查 WebSocket 连接数
curl http://localhost:8000/api/ws/stats
# 预期：正常统计，无异常高的连接数

# 3. 检查认证成功率
tail -1000 logs/app.log | grep "authenticate_user" | grep "成功" | wc -l
tail -1000 logs/app.log | grep "authenticate_user" | grep "失败" | wc -l
# 计算成功率，预期 > 95%

# 4. 检查 bcrypt 自动迁移日志
tail -1000 logs/app.log | grep "密码已成功升级到 bcrypt" | wc -l
# 显示升级的密码数量
```

### 告警规则
如果出现以下情况，立即回滚：
- 认证失败率 > 20%
- WebSocket 连接异常增长（> 1000）
- 出现大量 `RuntimeError: This event loop is already running`
- 服务频繁崩溃重启

---

## ✅ 部署完成确认

所有检查项完成后：
- [ ] 所有功能测试通过
- [ ] 错误率在正常范围
- [ ] 监控系统无异常告警
- [ ] 用户反馈正常

**部署日期**: _______________  
**部署人员**: _______________  
**验证人员**: _______________

---

## 🆘 紧急联系方式

如果部署出现问题：
1. 立即回滚到备份
2. 联系开发团队
3. 查看日志：`tail -f logs/app.log | grep -i error`
4. 检查服务状态：`systemctl status tradingagents` 或 `docker ps`
