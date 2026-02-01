// MongoDB 初始化脚本
// 在容器首次启动时自动执行

db = db.getSiblingDB('tradingagents');

// 创建应用用户
db.createUser({
  user: 'tradingagents',
  pwd: 'tradingagents123',
  roles: [
    { role: 'readWrite', db: 'tradingagents' },
    { role: 'dbAdmin', db: 'tradingagents' }
  ]
});

// 创建集合（如果不存在）
db.createCollection('historical_data');
db.createCollection('stock_daily_quotes');
db.createCollection('stock_info');
db.createCollection('users');
db.createCollection('analysis_reports');

// 创建索引
db.historical_data.createIndex({ "symbol": 1, "date": 1 }, { unique: true });
db.historical_data.createIndex({ "symbol": 1 });
db.historical_data.createIndex({ "date": -1 });

db.stock_daily_quotes.createIndex({ "symbol": 1, "date": 1 }, { unique: true });
db.stock_daily_quotes.createIndex({ "symbol": 1 });

db.stock_info.createIndex({ "symbol": 1 }, { unique: true });
db.stock_info.createIndex({ "name": 1 });

print('MongoDB 初始化完成！');
