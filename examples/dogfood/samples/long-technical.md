---
title: PostgreSQL 查询优化与执行计划分析
date: 2026-05-18
tags: [dogfood, real-llm, postgresql, database, performance]
---

# PostgreSQL 查询优化与执行计划分析

## 背景

在生产环境中，PostgreSQL 查询性能直接影响到应用的响应时间和用户体验。理解和优化查询执行计划是后端工程师的必备技能。

## 执行计划基础

PostgreSQL 使用基于成本的优化器（Cost-Based Optimizer, CBO）来选择最优查询计划。可以通过 `EXPLAIN` 和 `EXPLAIN ANALYZE` 命令查看查询计划：

```sql
EXPLAIN ANALYZE
SELECT u.name, COUNT(o.id) as order_count
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
WHERE u.created_at > '2025-01-01'
GROUP BY u.id, u.name
ORDER BY order_count DESC
LIMIT 20;
```

## 常见优化策略

### 1. 索引优化

对于高频查询字段建立合适的索引是最直接的优化手段。需要考虑：

- B-tree 索引适用于等值和范围查询
- GIN 索引适用于全文搜索和数组包含查询
- 复合索引列顺序应与查询条件顺序一致
- 避免在低基数列上建立索引

### 2. 查询重写

有时候索引无法解决的性能问题，需要从查询本身入手：

- 用 `EXISTS` 替代 `IN` 子查询（当子查询结果集较大时）
- 避免 `SELECT *`，只选择需要的列
- 合理使用 `JOIN` 而非子查询
- 注意 `LIMIT` 与 `ORDER BY` 的配合使用

### 3. 表分区

对于大表（超过千万行），考虑使用表分区：

```sql
CREATE TABLE orders (
    id SERIAL,
    user_id INTEGER,
    created_at TIMESTAMP,
    amount DECIMAL
) PARTITION BY RANGE (created_at);
```

### 4. 连接池与查询缓存

使用 PgBouncer 等连接池工具减少连接开销，合理配置 shared_buffers 和 effective_cache_size。

## 监控指标

需要持续关注的关键指标包括：慢查询日志、索引命中率、连接数、锁等待时间、vacuum 频率。

## 总结

PostgreSQL 优化是一个系统工程，需要从索引设计、查询结构、硬件配置等多个维度综合考虑。建立完善的监控体系是持续优化的基础。
