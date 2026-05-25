#!/usr/bin/env python3
"""生成 50+ 非敏感 synthetic 样本文件用于 Product Main Path Dogfood。

安全边界：
- 所有内容为 synthetic/fake，不涉及真实私人资料
- 不读取 .env / secrets / API key
- 不调用 LLM / 外部服务
- 输出到指定目录（默认 /tmp/mindforge-dogfood-samples）

使用方式：
  python scripts/generate_dogfood_samples.py [--target /tmp/mindforge-dogfood-samples] [--count 60]
"""

from __future__ import annotations

import argparse
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# 内容模板 — 全部为非敏感公开知识主题
# ---------------------------------------------------------------------------

MARKDOWN_TEMPLATES = [
    # 技术笔记
    {
        "filename": "python-async-io-notes.md",
        "content": """# Python AsyncIO 学习笔记

## 事件循环基础

asyncio 的核心是事件循环（event loop），它在一个线程中调度协程的执行。

```python
import asyncio

async def main():
    print("Hello, asyncio!")

asyncio.run(main())
```

## 关键概念

- **协程**: `async def` 定义的函数，返回协程对象
- **Task**: 将协程包装为 Task 后交给事件循环调度
- **Future**: 表示一个尚未完成的结果

## 常见模式

1. `asyncio.gather()` — 并发执行多个协程
2. `asyncio.create_task()` — 创建后台任务
3. `asyncio.wait_for()` — 设置超时

## 参考

- Python 官方文档: https://docs.python.org/3/library/asyncio.html
""",
    },
    {
        "filename": "git-rebase-workflow.md",
        "content": """# Git Rebase 工作流

## 为什么用 Rebase

保持提交历史线性、清晰，便于 code review 和 bisect。

## 基本操作

```bash
# 将最近 3 个 commit 合并
git rebase -i HEAD~3

# 将 feature 分支 rebase 到 main
git checkout feature
git rebase main
```

## 黄金法则

**不要 rebase 已经推送到公共仓库的提交。**

## 冲突解决

1. `git status` 查看冲突文件
2. 手动解决冲突
3. `git add <resolved-file>`
4. `git rebase --continue`

## Squash vs Merge

- Squash: 将多个 commit 压缩为一个，适合特性分支
- Merge: 保留完整历史，适合长期分支合并
""",
    },
    {
        "filename": "docker-compose-patterns.md",
        "content": """# Docker Compose 常见模式

## 开发环境模板

```yaml
version: "3.8"
services:
  app:
    build: .
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    depends_on:
      - db
      - redis

  db:
    image: postgres:16
    environment:
      POSTGRES_PASSWORD: dev-only-not-secret
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine

volumes:
  pgdata:
```

## 最佳实践

1. 使用命名卷保留数据
2. 开发时 mount 源码实现热重载
3. 通过 `depends_on` 控制启动顺序
4. 用 `.env` 文件管理环境变量（不提交到 git）
""",
    },
    {
        "filename": "sql-query-optimization.md",
        "content": """# SQL 查询优化技巧

## 索引策略

- 为 WHERE、JOIN、ORDER BY 列创建索引
- 复合索引遵循最左前缀原则
- 用 EXPLAIN ANALYZE 分析执行计划

## 常见反模式

1. SELECT * — 只取需要的列
2. 在 WHERE 中对列使用函数 — 导致索引失效
3. 隐式类型转换 — `WHERE varchar_col = 123`
4. 过多的 JOIN — 考虑拆分为多个查询

## N+1 问题

ORM 中最常见的性能问题：

```python
# 坏: N+1 查询
for user in users:
    print(user.profile.bio)  # 每次都查一次 profile

# 好: 预加载
users = User.query.options(joinedload(User.profile)).all()
```

## 参考

- PostgreSQL 文档: https://www.postgresql.org/docs/current/indexes.html
""",
    },
    {
        "filename": "react-hooks-cheatsheet.md",
        "content": """# React Hooks 速查表

## useState

```jsx
const [count, setCount] = useState(0);
setCount(prev => prev + 1);  // 函数式更新
```

## useEffect

```jsx
useEffect(() => {
    // 副作用逻辑
    const subscription = api.subscribe();
    return () => subscription.unsubscribe();  // 清理
}, [dependency]);
```

## useMemo / useCallback

```jsx
const sorted = useMemo(() => data.sort(), [data]);
const handleClick = useCallback(() => doThing(id), [id]);
```

## 自定义 Hook

```jsx
function useWindowSize() {
    const [size, setSize] = useState([0, 0]);
    useEffect(() => {
        const handler = () => setSize([window.innerWidth, window.innerHeight]);
        window.addEventListener("resize", handler);
        return () => window.removeEventListener("resize", handler);
    }, []);
    return size;
}
```
""",
    },
    {
        "filename": "linux-command-line-tips.md",
        "content": """# Linux 命令行实用技巧

## 文本处理

```bash
# 查找重复行
sort file.txt | uniq -d

# 统计词频
cat file.txt | tr ' ' '\\n' | sort | uniq -c | sort -nr | head -20

# 批量重命名
for f in *.txt; do mv "$f" "${f%.txt}.md"; done
```

## 系统诊断

```bash
# 磁盘使用
du -sh * | sort -hr | head -10

# 内存使用 Top 10
ps aux --sort=-%mem | head -11

# 网络连接统计
ss -s
```

## 进程管理

```bash
# 查找并终止进程
ps aux | grep process-name
kill -9 <pid>

# 后台任务
nohup long-running-command &
disown
```
""",
    },
    {
        "filename": "api-design-best-practices.md",
        "content": """# REST API 设计最佳实践

## URL 设计

- 使用名词而非动词: `/users` 而非 `/getUsers`
- 复数形式: `/articles` 而非 `/article`
- 层级关系: `/articles/123/comments`

## HTTP 方法语义

| 方法 | 语义 | 幂等 |
|------|------|------|
| GET | 获取资源 | 是 |
| POST | 创建资源 | 否 |
| PUT | 全量更新 | 是 |
| PATCH | 部分更新 | 否 |
| DELETE | 删除资源 | 是 |

## 状态码

- 200 OK — 成功
- 201 Created — 资源已创建
- 400 Bad Request — 请求参数错误
- 404 Not Found — 资源不存在
- 422 Unprocessable Entity — 参数校验失败
- 500 Internal Server Error — 服务器错误

## 分页

```json
{
    "data": [...],
    "meta": {
        "page": 1,
        "per_page": 20,
        "total": 150
    }
}
```
""",
    },
    {
        "filename": "testing-pyramid-explained.md",
        "content": """# 测试金字塔

## 三层结构

```
       /\\
      /E2E\\
     /------\\
    /  INTEG  \\
   /-----------\\
  /    UNIT     \\
 /---------------\\
```

## Unit Tests (底层)

- 数量最多，运行最快
- 测试单个函数/方法
- 不依赖外部系统
- 目标: 70-80% 覆盖率

## Integration Tests (中层)

- 测试模块间交互
- 可能涉及数据库、文件系统
- 数量中等

## E2E Tests (顶层)

- 测试完整用户流程
- 数量最少，运行最慢
- 检查核心业务路径

## 反模式

- 倒金字塔: 大量 E2E，少量 Unit
- 冰淇淋筒: 大量 E2E + 大量 Unit，没有 Integration
""",
    },
    {
        "filename": "kubernetes-pod-lifecycle.md",
        "content": """# Kubernetes Pod 生命周期

## 阶段

1. **Pending**: Pod 已创建，等待调度或镜像拉取
2. **Running**: 至少一个容器正在运行
3. **Succeeded**: 所有容器正常退出
4. **Failed**: 至少一个容器异常退出
5. **Unknown**: 无法获取 Pod 状态

## 容器探针

```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 15
  periodSeconds: 20

readinessProbe:
  httpGet:
    path: /ready
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 10
```

## 重启策略

- Always: 总是重启（默认）
- OnFailure: 失败时重启
- Never: 从不重启
""",
    },
    {
        "filename": "typescript-type-system-notes.md",
        "content": """# TypeScript 类型系统笔记

## 基础类型

```typescript
let x: number = 42;
let s: string = "hello";
let b: boolean = true;
let arr: number[] = [1, 2, 3];
let tuple: [string, number] = ["age", 30];
```

## 高级类型

### Union Types
```typescript
type Status = "pending" | "active" | "done";
```

### Generics
```typescript
function first<T>(arr: T[]): T | undefined {
    return arr[0];
}
```

### Conditional Types
```typescript
type IsString<T> = T extends string ? "yes" : "no";
```

## Utility Types

- `Partial<T>` — 所有属性可选
- `Required<T>` — 所有属性必选
- `Pick<T, K>` — 挑选属性
- `Omit<T, K>` — 排除属性
- `Record<K, V>` — 构造对象类型
""",
    },
    {
        "filename": "machine-learning-basics.md",
        "content": """# 机器学习基础概念

## 三大范式

### 监督学习 (Supervised Learning)
- 有标签数据
- 目标: 学习输入到输出的映射
- 例子: 分类、回归

### 无监督学习 (Unsupervised Learning)
- 无标签数据
- 目标: 发现数据中的模式
- 例子: 聚类、降维

### 强化学习 (Reinforcement Learning)
- 通过与环境交互学习
- 目标: 最大化累积奖励

## 常见算法

| 算法 | 类型 | 适用场景 |
|------|------|----------|
| 线性回归 | 回归 | 连续值预测 |
| 决策树 | 分类/回归 | 可解释性要求高 |
| SVM | 分类 | 高维数据 |
| K-Means | 聚类 | 无标签分组 |

## 过拟合 vs 欠拟合

- **过拟合**: 训练集表现好，测试集表现差 → 正则化、Dropout、更多数据
- **欠拟合**: 训练集表现也差 → 增加模型复杂度、更多特征
""",
    },
    {
        "filename": "vim-shortcuts-reference.md",
        "content": """# Vim 快捷键参考

## 模式切换

- `i` — 进入插入模式
- `Esc` — 回到普通模式
- `v` — 进入可视模式
- `:` — 进入命令模式

## 移动

- `h/j/k/l` — 左/下/上/右
- `w/b` — 下一个/上一个词
- `0/$` — 行首/行尾
- `gg/G` — 文件首/尾
- `Ctrl+d/u` — 下半页/上半页

## 编辑

- `dd` — 删除当前行
- `yy` — 复制当前行
- `p/P` — 粘贴到后/前
- `u/Ctrl+r` — 撤销/重做
- `ciw` — 修改当前词
- `.` — 重复上一次操作

## 搜索

- `/pattern` — 搜索
- `n/N` — 下一个/上一个匹配
- `:%s/old/new/g` — 全局替换
""",
    },
    {
        "filename": "networking-osi-model.md",
        "content": """# OSI 七层模型

| 层 | 名称 | 功能 | 协议示例 |
|----|------|------|----------|
| 7 | 应用层 | 用户接口 | HTTP, FTP, SMTP |
| 6 | 表示层 | 数据格式转换 | SSL/TLS, JPEG |
| 5 | 会话层 | 会话管理 | NetBIOS, RPC |
| 4 | 传输层 | 端到端传输 | TCP, UDP |
| 3 | 网络层 | 路由选择 | IP, ICMP |
| 2 | 数据链路层 | 帧传输 | Ethernet, PPP |
| 1 | 物理层 | 比特传输 | RJ45, Fiber |

## TCP vs UDP

| 特性 | TCP | UDP |
|------|-----|-----|
| 连接 | 面向连接 | 无连接 |
| 可靠性 | 可靠 | 不可靠 |
| 顺序 | 有序 | 无序 |
| 速度 | 较慢 | 较快 |
| 用途 | Web, Email | 视频流, DNS |

## 三次握手

1. Client → Server: SYN
2. Server → Client: SYN-ACK
3. Client → Server: ACK
""",
    },
    {
        "filename": "algorithm-complexity-cheatsheet.md",
        "content": """# 算法复杂度速查表

## 排序算法

| 算法 | 最好 | 平均 | 最坏 | 空间 | 稳定 |
|------|------|------|------|------|------|
| 快速排序 | n log n | n log n | n² | log n | 否 |
| 归并排序 | n log n | n log n | n log n | n | 是 |
| 堆排序 | n log n | n log n | n log n | 1 | 否 |
| 插入排序 | n | n² | n² | 1 | 是 |

## 数据结构操作

| 结构 | 查找 | 插入 | 删除 |
|------|------|------|------|
| 数组 | O(1) | O(n) | O(n) |
| 链表 | O(n) | O(1) | O(1) |
| 哈希表 | O(1)* | O(1)* | O(1)* |
| BST | O(log n)* | O(log n)* | O(log n)* |
| 堆 | O(1) min | O(log n) | O(log n) |

*平均情况

## 大 O 记号速记

- O(1) — 常数
- O(log n) — 对数（二分查找）
- O(n) — 线性（遍历）
- O(n log n) — 线性对数（高效排序）
- O(n²) — 平方（嵌套循环）
- O(2ⁿ) — 指数（暴力搜索）
""",
    },
    {
        "filename": "css-flexbox-guide.md",
        "content": """# CSS Flexbox 布局指南

## 容器属性

```css
.container {
    display: flex;
    flex-direction: row;          /* 主轴方向 */
    justify-content: space-between; /* 主轴对齐 */
    align-items: center;           /* 交叉轴对齐 */
    flex-wrap: wrap;               /* 换行 */
    gap: 16px;                     /* 间距 */
}
```

## 子元素属性

```css
.item {
    flex: 1;           /* flex-grow */
    flex: 2 1 200px;   /* grow shrink basis */
    align-self: flex-end; /* 单独覆盖 align-items */
    order: 1;          /* 排序（越小越前） */
}
```

## 常见布局模式

### 圣杯布局
```
header
| sidebar | main | sidebar |
footer
```

### 居中对齐
```css
.parent {
    display: flex;
    justify-content: center;
    align-items: center;
}
```
""",
    },
    {
        "filename": "web-security-owasp-top10.md",
        "content": """# OWASP Top 10 安全风险

## 2021 版本

1. **Broken Access Control** — 权限控制缺失
2. **Cryptographic Failures** — 加密实现错误
3. **Injection** — SQL/命令注入
4. **Insecure Design** — 设计阶段的安全缺陷
5. **Security Misconfiguration** — 安全配置错误
6. **Vulnerable Components** — 使用已知漏洞组件
7. **Auth Failures** — 认证机制缺陷
8. **Software & Data Integrity** — 软件供应链安全
9. **Logging & Monitoring** — 日志和监控不足
10. **SSRF** — 服务端请求伪造

## 防御措施

- 输入校验（白名单优于黑名单）
- 参数化查询
- 最小权限原则
- 定期依赖扫描
- HTTPS 强制启用
- CSP 头部配置
""",
    },
    {
        "filename": "data-structures-overview.md",
        "content": """# 常用数据结构概览

## 线性结构

### 数组
- 连续内存，O(1) 随机访问
- 插入/删除 O(n)

### 链表
- 非连续内存，O(n) 随机访问
- 插入/删除 O(1)（已知位置）

### 栈 (Stack)
- LIFO (后进先出)
- push / pop / peek
- 应用: 函数调用栈、撤销操作

### 队列 (Queue)
- FIFO (先进先出)
- enqueue / dequeue
- 应用: 任务调度、消息队列

## 树形结构

### 二叉搜索树 (BST)
- 左子树 < 根 < 右子树
- 平均 O(log n) 操作

### 堆 (Heap)
- 完全二叉树
- 最大堆/最小堆
- 优先队列实现

### Trie (前缀树)
- 字符串高效存储和查找
- 自动补全、拼写检查

## 图

- 顶点 + 边
- 有向/无向
- 表示: 邻接矩阵 / 邻接表
""",
    },
    {
        "filename": "postgresql-index-types.md",
        "content": """# PostgreSQL 索引类型

## B-Tree (默认)

```sql
CREATE INDEX idx_users_email ON users(email);
```

适用于: 等值查询、范围查询、ORDER BY

## Hash

```sql
CREATE INDEX idx_users_id_hash ON users USING hash(id);
```

仅适用于等值查询 (=)，不支持范围查询。

## GIN (Generalized Inverted Index)

```sql
CREATE INDEX idx_docs_content ON docs USING gin(to_tsvector('english', content));
```

适用于: 全文搜索、数组包含、JSONB 查询

## GiST (Generalized Search Tree)

适用于: 几何数据、范围类型、全文搜索

## BRIN (Block Range INdex)

```sql
CREATE INDEX idx_events_ts ON events USING brin(created_at);
```

适用于: 非常大的表、物理有序的数据

## 部分索引

```sql
CREATE INDEX idx_active_users ON users(email) WHERE active = true;
```

只为满足条件的行创建索引，节省空间。
""",
    },
    {
        "filename": "design-patterns-go.md",
        "content": """# Go 设计模式

## 创建型

### Functional Options
```go
type Server struct {
    timeout time.Duration
    maxConn int
}

type Option func(*Server)

func WithTimeout(d time.Duration) Option {
    return func(s *Server) { s.timeout = d }
}

func NewServer(opts ...Option) *Server {
    s := &Server{timeout: 30 * time.Second}
    for _, o := range opts { o(s) }
    return s
}
```

## 行为型

### 基于 Channel 的 Pipeline
```go
func gen(nums ...int) <-chan int {
    out := make(chan int)
    go func() {
        for _, n := range nums { out <- n }
        close(out)
    }()
    return out
}
```

## 结构性

### 接口组合
```go
type Reader interface { Read([]byte) (int, error) }
type Writer interface { Write([]byte) (int, error) }
type ReadWriter interface {
    Reader
    Writer
}
```
""",
    },
    {
        "filename": "redis-data-types-use-cases.md",
        "content": """# Redis 数据类型和使用场景

## String

```redis
SET cache:user:123 '{"name":"Alice"}' EX 3600
GET cache:user:123
INCR page:view:article-456
```

场景: 缓存、计数器、分布式锁

## Hash

```redis
HSET user:123 name Alice age 30 email alice@example.com
HGET user:123 name
HGETALL user:123
```

场景: 对象存储、用户 profile

## List

```redis
LPUSH queue:tasks "task1" "task2"
RPOP queue:tasks
LRANGE queue:tasks 0 -1
```

场景: 消息队列、最新动态列表

## Set

```redis
SADD tags:article:1 "python" "redis" "database"
SINTER tags:article:1 tags:article:2
```

场景: 标签、共同好友、去重

## Sorted Set

```redis
ZADD leaderboard 100 player1 200 player2
ZREVRANGE leaderboard 0 9 WITHSCORES
```

场景: 排行榜、延迟队列、范围查询
""",
    },
    {
        "filename": "ci-cd-pipeline-design.md",
        "content": """# CI/CD Pipeline 设计

## Pipeline 阶段

```
Code Push → Build → Test → Scan → Deploy Staging → E2E → Deploy Prod
```

## 常见工具

| 阶段 | 工具 |
|------|------|
| 代码检查 | ESLint, Ruff, golangci-lint |
| 构建 | Docker, Webpack, Go build |
| 单元测试 | Jest, pytest, go test |
| 安全扫描 | Trivy, Snyk, Bandit |
| 部署 | Kubernetes, Helm, Terraform |

## GitHub Actions 示例

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci
      - run: npm test
      - run: npm run lint
```

## 最佳实践

1. 快速失败 — lint 和类型检查放在最前面
2. 并行执行独立任务
3. 缓存依赖加速构建
4. 保持 pipeline 在 10 分钟内
""",
    },
    {
        "filename": "functional-programming-concepts.md",
        "content": """# 函数式编程核心概念

## 纯函数 (Pure Functions)

- 相同输入始终返回相同输出
- 无副作用
- 易于测试和推理

```javascript
// 纯函数
const add = (a, b) => a + b;

// 不纯（有副作用）
let total = 0;
const addToTotal = (x) => { total += x; };
```

## 不可变性 (Immutability)

不修改现有数据，而是创建新数据。

## 高阶函数 (Higher-Order Functions)

接收函数作为参数或返回函数的函数。

```javascript
const multiply = (factor) => (x) => x * factor;
const double = multiply(2);
double(5); // 10
```

## 函数组合 (Composition)

```javascript
const compose = (f, g) => (x) => f(g(x));
const addOne = (x) => x + 1;
const doubleAndAddOne = compose(addOne, double);
```

## Map / Filter / Reduce

```javascript
[1, 2, 3, 4].map(x => x * 2);        // [2, 4, 6, 8]
[1, 2, 3, 4].filter(x => x % 2 === 0); // [2, 4]
[1, 2, 3, 4].reduce((a, b) => a + b, 0); // 10
```
""",
    },
    {
        "filename": "regular-expressions-cookbook.md",
        "content": """# 正则表达式实用配方

## 基础元字符

| 符号 | 含义 |
|------|------|
| `.` | 任意字符（除换行） |
| `*` | 0 次或多次 |
| `+` | 1 次或多次 |
| `?` | 0 次或 1 次 |
| `{n,m}` | n 到 m 次 |
| `^` | 行首 |
| `$` | 行尾 |
| `\\b` | 单词边界 |

## 常用模式

```python
# Email
r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}"

# URL
r"https?://[^\\s]+"

# 中国手机号
r"1[3-9]\\d{9}"

# IPv4
r"\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}\\.\\d{1,3}"

# 日期 (YYYY-MM-DD)
r"\\d{4}-\\d{2}-\\d{2}"
```

## 捕获组

```python
import re
pattern = r"(\\w+)@(\\w+\\.\\w+)"
m = re.search(pattern, "user@example.com")
m.group(1)  # "user"
m.group(2)  # "example.com"
```
""",
    },
    {
        "filename": "monitoring-observability-pillars.md",
        "content": """# 可观测性三大支柱

## Metrics (指标)

- 聚合数值数据
- 时间序列存储
- 示例: QPS, P99 延迟, 错误率

工具: Prometheus, Datadog, Grafana

## Logging (日志)

- 离散事件记录
- 结构化日志 (JSON)
- 日志级别: DEBUG, INFO, WARN, ERROR

工具: ELK Stack, Loki, CloudWatch

## Tracing (链路追踪)

- 请求跨服务传播追踪
- 识别延迟瓶颈
- Span + Trace 模型

工具: Jaeger, Zipkin, OpenTelemetry

## RED 方法论

- **Rate**: 每秒请求数
- **Errors**: 错误率
- **Duration**: 请求延迟分布

## USE 方法论 (资源视角)

- **Utilization**: 资源利用率
- **Saturation**: 资源饱和度
- **Errors**: 错误数
""",
    },
    {
        "filename": "python-decorators-explained.md",
        "content": """# Python 装饰器详解

## 基础装饰器

```python
def timer(func):
    import time
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        print(f"{func.__name__} took {elapsed:.4f}s")
        return result
    return wrapper

@timer
def slow_function():
    time.sleep(0.1)
```

## 带参数的装饰器

```python
def retry(max_attempts=3, delay=1):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    if attempt == max_attempts - 1:
                        raise
                    time.sleep(delay)
        return wrapper
    return decorator

@retry(max_attempts=5, delay=0.5)
def flaky_api_call():
    ...
```

## 常用内置装饰器

- `@staticmethod` — 静态方法
- `@classmethod` — 类方法
- `@property` — 属性访问器
- `@functools.lru_cache` — 缓存返回值
- `@functools.wraps` — 保留元数据
""",
    },
    {
        "filename": "http-status-codes-reference.md",
        "content": """# HTTP 状态码参考

## 2xx Success

- 200 OK — 请求成功
- 201 Created — 资源创建成功
- 204 No Content — 成功但无返回内容

## 3xx Redirection

- 301 Moved Permanently — 永久重定向
- 302 Found — 临时重定向
- 304 Not Modified — 资源未修改（缓存）

## 4xx Client Error

- 400 Bad Request — 请求语法错误
- 401 Unauthorized — 需要认证
- 403 Forbidden — 无权限
- 404 Not Found — 资源不存在
- 405 Method Not Allowed — HTTP 方法不正确
- 409 Conflict — 资源冲突
- 422 Unprocessable Entity — 参数校验失败
- 429 Too Many Requests — 请求频率过高

## 5xx Server Error

- 500 Internal Server Error — 服务器内部错误
- 502 Bad Gateway — 网关错误
- 503 Service Unavailable — 服务暂不可用
- 504 Gateway Timeout — 网关超时
""",
    },
    {
        "filename": "containerization-vs-virtualization.md",
        "content": """# 容器 vs 虚拟化

## 虚拟机

- 每个 VM 有完整 Guest OS
- Hypervisor 抽象硬件
- 强隔离，资源开销大
- 启动时间: 分钟级

## 容器

- 共享 Host OS 内核
- 使用 namespace + cgroup 隔离
- 轻量级，快速启动
- 启动时间: 秒级

## 对比

| 特性 | VM | Container |
|------|-----|-----------|
| 隔离级别 | 硬件级 | 进程级 |
| 资源开销 | GB 级 | MB 级 |
| 启动速度 | 分钟 | 秒 |
| 密度 | 低 | 高 |
| 跨平台 | 是 | 同 OS 内核 |

## 使用场景

- 容器: 微服务、CI/CD、开发环境
- VM: 多租户、不同 OS 需求、强安全隔离
""",
    },
    {
        "filename": "graphql-vs-rest-comparison.md",
        "content": """# GraphQL vs REST

## REST

### 优点
- 成熟、工具链丰富
- HTTP 缓存原生支持
- 简单易懂

### 缺点
- 过度获取 (over-fetching)
- 获取不足 (under-fetching)
- 版本管理复杂

## GraphQL

### 优点
- 精确获取所需数据
- 单一端点
- 强类型 Schema
- 实时订阅

### 缺点
- 缓存复杂
- 学习曲线
- 查询性能不可预测
- 文件上传支持弱

## 选择建议

- 多个客户端、灵活查询需求 → GraphQL
- 简单 CRUD、需要 HTTP 缓存 → REST
- 不一定要二选一，可以共存
""",
    },
    {
        "filename": "microservices-architecture-patterns.md",
        "content": """# 微服务架构模式

## 通信模式

### 同步 (Request-Response)
- REST / gRPC
- 简单直接，但会级联延迟

### 异步 (Event-Driven)
- Message Queue / Event Bus
- 解耦，但增加复杂度

## 数据管理

- **Database per Service**: 每个服务独立数据库
- **SAGA**: 分布式事务的补偿模式
- **CQRS**: 读写分离

## 常见模式

### API Gateway
统一入口，处理认证、限流、路由

### Service Discovery
服务注册与发现 (Consul, Eureka, K8s DNS)

### Circuit Breaker
防止级联故障 (熔断器)

### Bulkhead
资源隔离，防止一个服务耗尽所有资源

## 反模式

- 过早拆分 → 先单体验证业务
- 分布式单体 → 服务紧耦合，共享数据库
""",
    },
    {
        "filename": "python-concurrency-models.md",
        "content": """# Python 并发模型

## 多线程 (threading)

```python
import threading

def worker(name):
    print(f"Worker {name}")

threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
for t in threads: t.start()
for t in threads: t.join()
```

受 GIL 限制，适合 I/O 密集型任务。

## 多进程 (multiprocessing)

```python
from multiprocessing import Pool

with Pool(4) as pool:
    results = pool.map(process_item, items)
```

绕过 GIL，适合 CPU 密集型。开销大于线程。

## 协程 (asyncio)

```python
import asyncio

async def fetch(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()

results = asyncio.run(asyncio.gather(*[fetch(u) for u in urls]))
```

单线程事件循环，适合高并发 I/O。

## 选择指南

| 场景 | 推荐 |
|------|------|
| I/O 密集 | asyncio / threading |
| CPU 密集 | multiprocessing |
| 简单并发 HTTP | asyncio + aiohttp |
| 已有多线程代码 | concurrent.futures |
""",
    },
    {
        "filename": "javascript-event-loop-explained.md",
        "content": """# JavaScript Event Loop 详解

## 核心概念

JavaScript 是单线程的，通过 Event Loop 实现异步。

```
Call Stack → Task Queue (macrotask) / Microtask Queue
```

## 执行顺序

1. 执行 Call Stack 中的同步代码
2. 清空 Microtask Queue (Promise, queueMicrotask)
3. 从 Task Queue 取一个 macrotask 执行
4. 重复

## Macrotask vs Microtask

### Macrotask (宏任务)
- setTimeout, setInterval
- I/O
- UI Rendering

### Microtask (微任务)
- Promise.then/catch/finally
- queueMicrotask
- MutationObserver

## 示例

```javascript
console.log("1");
setTimeout(() => console.log("2"), 0);
Promise.resolve().then(() => console.log("3"));
console.log("4");

// 输出: 1, 4, 3, 2
```

解释: 同步代码先执行 → microtask 队列优先于 macrotask
""",
    },
    {
        "filename": "terraform-iac-basics.md",
        "content": """# Terraform IaC 基础

## 核心概念

- **Provider**: 云平台插件 (AWS, GCP, Azure)
- **Resource**: 基础设施组件
- **Data Source**: 读取已有资源
- **State**: 基础设施当前状态
- **Module**: 可复用的配置单元

## 基本示例

```hcl
provider "aws" {
  region = "us-east-1"
}

resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "t3.micro"

  tags = {
    Name = "web-server"
  }
}
```

## 常用命令

```bash
terraform init       # 初始化
terraform plan       # 预览变更
terraform apply      # 应用变更
terraform destroy    # 销毁资源
terraform fmt        # 格式化代码
```

## 最佳实践

- 使用 remote state 避免冲突
- 敏感变量标记 `sensitive = true`
- 模块化复用
- 版本固定 provider
""",
    },
    {
        "filename": "caching-strategies-comparison.md",
        "content": """# 缓存策略对比

## Cache-Aside (旁路缓存)

```
App → Cache (miss) → DB → Cache → App
```

- 应用负责缓存读写
- 缓存未命中时查 DB 并回填
- 最常见模式

## Read-Through

```
App → Cache → DB (miss) → Cache → App
```

- 缓存层负责查 DB
- 应用只需与缓存交互

## Write-Through

```
App → Cache → DB
```

- 同步写缓存和 DB
- 数据一致性强，写入延迟高

## Write-Behind (Write-Back)

```
App → Cache → (async) → DB
```

- 先写缓存，异步写 DB
- 高性能，有数据丢失风险

## 缓存失效策略

| 策略 | 说明 |
|------|------|
| TTL | 设置过期时间 |
| LRU | 淘汰最近最少使用 |
| LFU | 淘汰最少频率使用 |
| Write Invalidate | 写时失效相关缓存 |
""",
    },
    {
        "filename": "code-review-checklist.md",
        "content": """# Code Review 检查清单

## 正确性

- [ ] 逻辑是否正确
- [ ] 边界条件是否处理
- [ ] 错误处理是否完善
- [ ] 并发安全

## 可维护性

- [ ] 命名是否清晰、符合惯例
- [ ] 函数是否单一职责
- [ ] 是否有不必要的抽象
- [ ] 是否有重复代码

## 安全性

- [ ] 输入是否已校验
- [ ] SQL 是否参数化
- [ ] XSS 防护
- [ ] 敏感信息不输出到日志

## 性能

- [ ] 是否有 N+1 查询
- [ ] 大数据量是否分页
- [ ] 循环中是否有昂贵操作

## 测试

- [ ] 是否有适当测试
- [ ] 是否覆盖边界情况
- [ ] 测试是否独立可重复

## Review 礼仪

- 区分 blocking 和 suggestion
- 提问比指责好 ("这里 N+1 查询了吗?" vs "你这里写错了")
- 及时 review（24h 内）
""",
    },
    {
        "filename": "distributed-consensus-basics.md",
        "content": """# 分布式共识基础

## CAP 定理

分布式系统最多同时满足三项中的两项：
- **C**onsistency (一致性)
- **A**vailability (可用性)
- **P**artition Tolerance (分区容忍)

实际系统中 P 不可避免 → 在 C 和 A 之间取舍。

## 常见算法

### Paxos
- 经典共识算法
- 难以理解和实现
- 多数派投票

### Raft
- 易于理解的 Paxos 替代
- Leader-Follower 模型
- etcd, Consul 使用

### Zab
- ZooKeeper 使用的协议
- 类似 Raft

## 应用场景

- Leader 选举
- 分布式锁
- 配置管理
- 服务发现
""",
    },
    {
        "filename": "css-grid-layout-guide.md",
        "content": """# CSS Grid 布局指南

## 基础示例

```css
.container {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    grid-template-rows: auto;
    gap: 20px;
}
```

## Grid 容器属性

```css
.container {
    grid-template-columns: 200px 1fr 1fr;  /* 三列 */
    grid-template-rows: 100px auto 100px;   /* 三行 */
    grid-template-areas:
        "header header header"
        "sidebar main main"
        "footer footer footer";
    justify-items: center;   /* 水平对齐 */
    align-items: center;     /* 垂直对齐 */
}
```

## Grid 子元素属性

```css
.item {
    grid-column: 1 / 3;         /* 跨两列 */
    grid-row: 2;                 /* 第二行 */
    grid-area: header;           /* 使用命名区域 */
    justify-self: start;         /* 覆盖单个水平对齐 */
}
```

## Grid vs Flexbox

- Grid: 二维布局（行+列）
- Flexbox: 一维布局（行或列）
- 可以组合使用
""",
    },
    {
        "filename": "database-transaction-isolation.md",
        "content": """# 数据库事务隔离级别

## 四种隔离级别

| 级别 | 脏读 | 不可重复读 | 幻读 |
|------|------|------------|------|
| Read Uncommitted | ✓ | ✓ | ✓ |
| Read Committed | ✗ | ✓ | ✓ |
| Repeatable Read | ✗ | ✗ | ✓ |
| Serializable | ✗ | ✗ | ✗ |

(✓ = 可能发生, ✗ = 已防止)

## 并发问题解释

- **脏读**: 读到未提交的事务数据
- **不可重复读**: 同一事务内两次读同一行结果不同
- **幻读**: 同一事务内两次查询结果集不同（多了/少了行）

## PostgreSQL 默认

Repeatable Read，但使用 Snapshot Isolation，实际防止幻读。

## 实践建议

```sql
-- 设置隔离级别
SET TRANSACTION ISOLATION LEVEL READ COMMITTED;
BEGIN;
-- ... operations
COMMIT;
```

- 默认 Read Committed 足矣大多数场景
- 金融/库存扣减考虑 Serializable
""",
    },
    {
        "filename": "semantic-versioning-guide.md",
        "content": """# 语义化版本 (SemVer)

## 版本格式

```
MAJOR.MINOR.PATCH
  1  .  2  .  3
```

- **MAJOR**: 不兼容的 API 变更
- **MINOR**: 向后兼容的新功能
- **PATCH**: 向后兼容的 bug 修复

## 预发布和构建

```
1.0.0-alpha.1
1.0.0-beta.2
1.0.0-rc.1
1.0.0+build.20250101
```

## 版本范围

| 范围 | 含义 |
|------|------|
| `^1.2.3` | >=1.2.3, <2.0.0 |
| `~1.2.3` | >=1.2.3, <1.3.0 |
| `>=1.0 <2.0` | 自定义范围 |
| `*` | 任意版本 |

## 实践规则

1. 初始开发用 `0.y.z`
2. `1.0.0` 定义公开 API
3. Patch 改动不引入新功能
4. 破坏性改动必须提升 MAJOR
5. 标记为 deprecated 的功能在下个 MAJOR 移除
""",
    },
    {
        "filename": "SOLID-principles-with-examples.md",
        "content": """# SOLID 原则

## S — Single Responsibility (单一职责)

一个类只负责一件事。

```python
# 坏
class Report:
    def generate(self): ...
    def save_to_db(self): ...
    def send_email(self): ...

# 好
class ReportGenerator: ...
class ReportRepository: ...
class ReportMailer: ...
```

## O — Open/Closed (开闭原则)

对扩展开放，对修改关闭。

## L — Liskov Substitution

子类必须可以替换父类，不破坏程序正确性。

## I — Interface Segregation

不强迫 client 依赖它不需要的接口。

```python
# 坏
class Worker(Protocol):
    def work(self): ...
    def eat(self): ...

# 好
class Workable(Protocol):
    def work(self): ...
class Eatable(Protocol):
    def eat(self): ...
```

## D — Dependency Inversion

高层模块不应依赖低层模块。两者都应依赖抽象。

```python
# 坏
class Service:
    def __init__(self):
        self.db = MySQLDatabase()  # 依赖具体类

# 好
class Service:
    def __init__(self, db: Database):  # 依赖抽象
        self.db = db
```
""",
    },
    {
        "filename": "shell-scripting-best-practices.md",
        "content": """# Shell 脚本最佳实践

## 脚本头部

```bash
#!/usr/bin/env bash
set -euo pipefail
```

- `-e`: 任何命令失败立即退出
- `-u`: 使用未定义变量报错
- `-o pipefail`: 管道中任何命令失败都算失败

## 变量使用

```bash
# 始终用双引号包裹
name="$1"
echo "Hello, $name"

# 默认值
port="${PORT:-8080}"

# 目录处理
script_dir="$(cd "$(dirname "$0")" && pwd)"
```

## 错误处理

```bash
cleanup() {
    rm -rf "$TMPDIR"
}
trap cleanup EXIT

if ! command -v jq &>/dev/null; then
    echo "需要安装 jq"
    exit 1
fi
```

## 函数

```bash
log_info() { echo "[INFO] $*"; }
log_error() { echo "[ERROR] $*" >&2; }
```
""",
    },
]

# TXT 纯文本样本
TXT_TEMPLATES = [
    {
        "filename": "meeting-notes-2026-03-15.txt",
        "content": """会议记录: 技术架构评审 2026-03-15

参与者: 技术团队成员 (化名)

议题:
1. API 网关选型 — 讨论 Nginx vs Envoy vs Traefik
   结论: 推荐 Envoy，社区活跃，原生支持 gRPC
2. 数据库迁移方案 — 从 PostgreSQL 14 升级到 16
   时间线: Q2 完成测试环境迁移，Q3 生产环境
3. 监控告警改进 — PagerDuty 告警疲劳
   行动: 每周 review 告警规则，合并低频告警
4. 代码审查流程 — 当前 MR 平均 review 时间 2.3 天
   目标: 1 天内 review，可考虑 code owner 机制

待办:
- [ ] 编写 Envoy POC demo
- [ ] 评估 PostgreSQL 16 新特性对业务的收益
- [ ] 整理当前告警规则清单
""",
    },
    {
        "filename": "reading-notes-kernel-design.txt",
        "content": """阅读摘录: 《操作系统设计与实现》

第三章: 进程管理

进程是程序的执行实例。每个进程有自己的地址空间、文件描述符表、
信号处理器等资源。

关键概念:
- PCB (Process Control Block): 内核维护的进程元数据结构
- 上下文切换: 保存当前进程状态，恢复下一个进程状态
  开销包括: 寄存器保存/恢复、TLB flush、cache miss
- fork() 使用 COW (Copy-on-Write) 优化
- 调度器目标: 吞吐量、响应时间、公平性

调度算法对比:
- Round Robin: 简单公平，但上下文切换开销大
- CFS (Linux): 红黑树维护 vruntime，O(log n)
- EEVDF: CFS 的改进替代，更早截止优先

思考题: 为什么 vfork() 被引入又逐步被废弃? (提示: COW 成熟)
""",
    },
    {
        "filename": "terminal-log-2026-04-01.txt",
        "content": """命令行操作日志 — 环境配置记录

$ python --version
Python 3.12.3

$ pip install fastapi uvicorn pydantic
Successfully installed fastapi-0.115.0 uvicorn-0.30.0 pydantic-2.9.0

$ git clone https://github.com/encode/httpx.git /tmp/httpx-src
Cloning into '/tmp/httpx-src'...
done.

$ cd /tmp/httpx-src && python -m pytest tests/ -q --tb=short
2345 passed, 12 skipped in 45.23s

$ docker ps --format "table {{.Names}}\\t{{.Status}}\\t{{.Ports}}"
NAMES          STATUS          PORTS
web-app        Up 3 hours      0.0.0.0:8000->8000/tcp
postgres-dev   Up 3 hours      0.0.0.0:5432->5432/tcp
redis-cache    Up 3 hours      0.0.0.0:6379->6379/tcp

$ du -sh /var/lib/docker/
15G     /var/lib/docker/

$ find . -name "*.pyc" -delete && find . -name "__pycache__" -type d -delete
(清除了 127 个缓存目录)
""",
    },
    {
        "filename": "learning-track-web-performance.txt",
        "content": """学习追踪: Web 性能优化

学习来源: web.dev, MDN, 实战项目

核心 Web 指标 (Core Web Vitals):

LCP (Largest Contentful Paint) — 最大内容绘制
  目标: < 2.5s
  优化: 预加载关键资源、CDN、压缩

INP (Interaction to Next Paint) — 交互延迟
  替代 FID 成为新标准 (2024.3)
  目标: < 200ms
  优化: 拆分长任务、使用 Web Worker

CLS (Cumulative Layout Shift) — 累积布局偏移
  目标: < 0.1
  优化: 设置图片尺寸、避免动态插入内容

性能预算:
- JS bundle < 200KB (gzip)
- 首屏图片 < 100KB
- TTFB < 800ms

已实践:
- React.lazy + Suspense code splitting
- 图片 WebP + srcset 响应式
- CSS font-display: swap
""",
    },
    {
        "filename": "script-output-example.txt",
        "content": """=== Build Output Log ===

[2026-04-15 10:30:00] Starting build process...
[2026-04-15 10:30:01] Cleaning previous artifacts...
[2026-04-15 10:30:03] Installing dependencies...
[2026-04-15 10:30:45] Dependencies installed successfully.
[2026-04-15 10:30:46] Running type checker...
[2026-04-15 10:31:12] Type check passed. (26s)
[2026-04-15 10:31:13] Running linter...
[2026-04-15 10:31:20] Lint passed. (7s)
[2026-04-15 10:31:21] Running tests...
[2026-04-15 10:32:45] Tests passed: 1234 passed, 0 failed, 3 skipped. (84s)
[2026-04-15 10:32:46] Building production bundle...
[2026-04-15 10:33:30] Bundle built: dist/main.js (245KB gzip)
[2026-04-15 10:33:31] Build completed successfully.

=== Stats ===
Total time: 3m31s
Dependencies: 234 packages
Test coverage: 87.3%
Bundle size: 245KB gzip / 980KB raw
""",
    },
    {
        "filename": "code-snippet-collection.txt",
        "content": """=== 实用代码片段收集 ===

# Python: 安全的字典取值
value = data.get("key", default)

# Python: 列表推导式过滤非空
items = [x.strip() for x in raw if x.strip()]

# Bash: 递归搜索替换
grep -rl "old_text" ./src/ | xargs sed -i '' 's/old_text/new_text/g'

# Git: 查看某文件的修改历史
git log -p -- path/to/file

# Git: 撤销最后一次 commit (保留修改)
git reset --soft HEAD~1

# Docker: 清理无用的镜像和卷
docker system prune -af --volumes

# SQL: 查找重复记录
SELECT email, COUNT(*) FROM users GROUP BY email HAVING COUNT(*) > 1;

# JavaScript: 数组去重
const unique = [...new Set(array)];

# JavaScript: 防抖函数
const debounce = (fn, ms) => {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), ms);
    };
};
""",
    },
    {
        "filename": "dataset-example.csv",
        "content": """language,year,rating,users_millions,ecosystem_score
Python,2024,9.2,28.3,95
JavaScript,2024,9.0,27.5,93
TypeScript,2024,8.8,16.2,91
Go,2024,8.5,8.1,88
Rust,2024,9.1,3.7,85
Java,2024,8.0,18.9,82
Kotlin,2024,7.8,4.5,79
Swift,2024,7.5,3.2,76
C#,2024,7.7,8.5,80
Ruby,2024,7.2,2.1,72
PHP,2024,6.8,9.3,70
Scala,2024,7.0,1.5,68
""",
    },
    {
        "filename": "project-ideas-brainstorm.txt",
        "content": """个人项目想法清单 (非保密)

1. CLI 工具 — 管理本地代码片段的 TUI 应用
   技术栈: Python + Textual/rich
   痛点: 笔记软件对代码片段支持差

2. 阅读进度追踪器
   技术栈: Next.js + SQLite
   功能: OCR 扫描书页 → 自动记录页码 → 统计阅读速度

3. 家庭网络设备监控面板
   技术栈: Go + HTMX + Prometheus
   功能: 设备在线状态、流量统计、DHCP 租约管理

4. 食谱管理与食材库存联动
   技术栈: Python FastAPI + React
   功能: 根据已有食材推荐可做菜品

5. 技术文章收藏的去重和摘要
   技术栈: Python + SQLite + 确定性文本相似度
   功能: 识别重复收藏的同一篇文章的不同 URL

优先级: 1 > 5 > 3
预估工作量: 1 号 2-3 周末完成 MVP
""",
    },
    {
        "filename": "api-response-example.json",
        "content": """{
    "status": "success",
    "data": {
        "articles": [
            {
                "id": "art_001",
                "title": "Understanding AsyncIO in Python",
                "author": "Jane Doe",
                "published_at": "2026-01-15T08:00:00Z",
                "tags": ["python", "async", "tutorial"],
                "reading_time_minutes": 12,
                "likes": 342
            },
            {
                "id": "art_002",
                "title": "Docker Best Practices 2026",
                "author": "John Smith",
                "published_at": "2026-02-20T14:30:00Z",
                "tags": ["docker", "devops", "best-practices"],
                "reading_time_minutes": 8,
                "likes": 215
            }
        ],
        "total": 2,
        "page": 1,
        "per_page": 20
    },
    "meta": {
        "request_id": "req_abc123",
        "elapsed_ms": 45
    }
}""",
    },
    {
        "filename": "git-commands-cheatsheet.txt",
        "content": """Git 命令速查 (个人整理)

基础:
  git init                    初始化仓库
  git clone <url>             克隆仓库
  git status                  查看状态
  git add <file>              暂存文件
  git commit -m "msg"         提交
  git push origin main        推送
  git pull --ff-only          拉取 (仅快进)

分支:
  git branch -a               列出所有分支
  git checkout -b feat/x      创建并切换分支
  git merge --no-ff feat/x    合并分支
  git branch -d feat/x        删除本地分支
  git push origin --delete feat/x  删除远程分支

历史:
  git log --oneline --graph   图形化日志
  git log -p <file>           文件变更历史
  git blame <file>            逐行追踪
  git reflog                  操作历史

撤销:
  git restore <file>          撤销工作区修改
  git restore --staged <file> 取消暂存
  git revert <commit>         安全撤销某次提交
  git reset --soft HEAD~1     撤销提交(保留修改)

暂存:
  git stash                   暂存当前修改
  git stash pop                恢复最近暂存
  git stash list               列出暂存列表
""",
    },
]

# HTML 样本
HTML_TEMPLATES = [
    {
        "filename": "wikipedia-python-excerpt.html",
        "content": """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>Python (programming language) — Wikipedia Excerpt</title>
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: auto; padding: 20px; }
        h1 { border-bottom: 1px solid #ccc; }
    </style>
</head>
<body>
    <h1>Python (programming language)</h1>
    <p>Python is a high-level, general-purpose programming language. Its design philosophy
    emphasizes code readability with the use of significant indentation.</p>
    <p>Python is dynamically typed and garbage-collected. It supports multiple programming
    paradigms, including structured, object-oriented, and functional programming.</p>
    <h2>History</h2>
    <p>Python was created by Guido van Rossum and was first released on February 20, 1991.
    The name "Python" comes from the BBC comedy series "Monty Python's Flying Circus."</p>
</body>
</html>""",
    },
    {
        "filename": "simple-doc-export.html",
        "content": """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>内部文档 — 示例</title>
    <style>
        body { font-family: Georgia, serif; line-height: 1.8; max-width: 700px; margin: 2em auto; }
        code { background: #f0f0f0; padding: 2px 4px; border-radius: 3px; }
    </style>
</head>
<body>
    <h1>项目环境初始化指南</h1>
    <p>本文档描述从零开始搭建开发环境的标准步骤。</p>
    <h2>前置条件</h2>
    <ul>
        <li>Python 3.12+</li>
        <li>Node.js 20+</li>
        <li>Docker Desktop</li>
    </ul>
    <h2>安装步骤</h2>
    <ol>
        <li>克隆仓库: <code>git clone repo-url</code></li>
        <li>创建虚拟环境: <code>python -m venv .venv</code></li>
        <li>激活虚拟环境: <code>source .venv/bin/activate</code></li>
        <li>安装依赖: <code>pip install -e ".[dev]"</code></li>
    </ol>
    <p>Note: All credentials use dev-only values. No production secrets.</p>
</body>
</html>""",
    },
    {
        "filename": "blog-post-excerpt.html",
        "content": """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>On the Future of Software Engineering</title></head>
<body>
    <article>
        <h1>On the Future of Software Engineering</h1>
        <time datetime="2026-01-10">January 10, 2026</time>
        <p>The field of software engineering continues to evolve. While AI-assisted coding
        tools have become mainstream, the fundamental skills of system design, debugging,
        and understanding tradeoffs remain critical.</p>
        <blockquote>
            "The best engineers don't just write code — they understand the problem space
            deeply enough to know when not to write code."
        </blockquote>
        <p>Key trends shaping the industry:</p>
        <ul>
            <li>Shift from writing code to reviewing AI-generated code</li>
            <li>Increased focus on system reliability and observability</li>
            <li>Growing importance of security by design</li>
        </ul>
    </article>
</body>
</html>""",
    },
    {
        "filename": "api-docs-snippet.html",
        "content": """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>API Reference — Example</title></head>
<body>
    <h1>Users API v2</h1>
    <section>
        <h2>GET /api/v2/users</h2>
        <p>Returns a paginated list of users.</p>
        <h3>Query Parameters</h3>
        <table>
            <tr><th>Name</th><th>Type</th><th>Description</th></tr>
            <tr><td>page</td><td>integer</td><td>Page number (default: 1)</td></tr>
            <tr><td>per_page</td><td>integer</td><td>Items per page (default: 20, max: 100)</td></tr>
            <tr><td>status</td><td>string</td><td>Filter by status: active, inactive, all</td></tr>
        </table>
    </section>
    <section>
        <h2>POST /api/v2/users</h2>
        <p>Create a new user.</p>
        <h3>Request Body (JSON)</h3>
        <pre><code>{
    "name": "string (required)",
    "email": "string (required, unique)",
    "role": "string (default: 'member')"
}</code></pre>
    </section>
</body>
</html>""",
    },
    {
        "filename": "changelog-example.html",
        "content": """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>CHANGELOG — Example Project v2.1.0</title></head>
<body>
    <h1>Changelog</h1>
    <h2>v2.1.0 (2026-03-01)</h2>
    <h3>Added</h3>
    <ul>
        <li>Export to OPML format support</li>
        <li>Dark mode toggle in settings</li>
    </ul>
    <h3>Fixed</h3>
    <ul>
        <li>Memory leak in WebSocket connection handler</li>
        <li>Search returning duplicate results for CJK queries</li>
    </ul>
    <h2>v2.0.0 (2026-01-15)</h2>
    <h3>Breaking Changes</h3>
    <ul>
        <li>API v2 replaces v1 (v1 deprecated, removed in v3.0)</li>
        <li>Config format changed from INI to YAML</li>
    </ul>
</body>
</html>""",
    },
    {
        "filename": "readme-template.html",
        "content": """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>example-lib — README</title></head>
<body>
    <h1>example-lib</h1>
    <p>A minimal example library for demonstration purposes.</p>
    <h2>Installation</h2>
    <pre>pip install example-lib</pre>
    <h2>Quick Start</h2>
    <pre><code>from example_lib import Calculator
calc = Calculator()
result = calc.add(2, 3)  # returns 5</code></pre>
    <h2>License</h2>
    <p>MIT — see LICENSE file for details.</p>
</body>
</html>""",
    },
]


def generate_samples(target_dir: Path, total_count: int = 60) -> list[Path]:
    """生成所有样本文件，返回创建的文件路径列表。"""
    created: list[Path] = []

    # 按类型比例分配
    md_count = min(len(MARKDOWN_TEMPLATES), int(total_count * 0.55))  # ~55% Markdown
    txt_count = min(len(TXT_TEMPLATES), int(total_count * 0.20))  # ~20% TXT
    html_count = min(len(HTML_TEMPLATES), int(total_count * 0.15))  # ~15% HTML

    subdirs = {
        "markdown": target_dir / "notes",
        "txt": target_dir / "logs",
        "html": target_dir / "web-exports",
    }

    for subdir in subdirs.values():
        subdir.mkdir(parents=True, exist_ok=True)

    # Markdown 笔记
    random.seed(42)
    selected_md = random.sample(MARKDOWN_TEMPLATES, md_count) if md_count < len(MARKDOWN_TEMPLATES) else MARKDOWN_TEMPLATES
    for tmpl in selected_md:
        path = subdirs["markdown"] / tmpl["filename"]
        path.write_text(tmpl["content"], encoding="utf-8")
        created.append(path)

    # TXT 纯文本
    selected_txt = random.sample(TXT_TEMPLATES, txt_count) if txt_count < len(TXT_TEMPLATES) else TXT_TEMPLATES
    for tmpl in selected_txt:
        path = subdirs["txt"] / tmpl["filename"]
        path.write_text(tmpl["content"], encoding="utf-8")
        created.append(path)

    # HTML 文件
    selected_html = random.sample(HTML_TEMPLATES, html_count) if html_count < len(HTML_TEMPLATES) else HTML_TEMPLATES
    for tmpl in selected_html:
        path = subdirs["html"] / tmpl["filename"]
        path.write_text(tmpl["content"], encoding="utf-8")
        created.append(path)

    # 额外混合目录 — 模拟真实文件组织
    mixed = target_dir / "mixed-project"
    mixed.mkdir(parents=True, exist_ok=True)
    (mixed / "README.md").write_text("# Mixed Project\n\nA sample project directory with various file types.\n", encoding="utf-8")
    (mixed / "TODO.txt").write_text("TODO:\n- Add unit tests\n- Update documentation\n- Performance profiling\n", encoding="utf-8")
    (mixed / "style.css").write_text("body { margin: 0; font-family: system-ui; }\n", encoding="utf-8")
    created.extend([mixed / "README.md", mixed / "TODO.txt", mixed / "style.css"])

    return created


def main():
    parser = argparse.ArgumentParser(description="生成 dogfood 非敏感 synthetic 样本文件")
    parser.add_argument("--target", default="/tmp/mindforge-dogfood-samples", help="输出目录")
    parser.add_argument("--count", type=int, default=60, help="目标文件数 (默认 60)")
    args = parser.parse_args()

    target = Path(args.target)
    if target.exists():
        # 清理旧样本
        import shutil

        shutil.rmtree(target)

    target.mkdir(parents=True, exist_ok=True)

    created = generate_samples(target, args.count)

    print(f"生成完成: {len(created)} 个文件")
    print(f"输出目录: {target}")

    # 按类型统计
    by_ext: dict[str, int] = {}
    for p in created:
        ext = p.suffix or "(no ext)"
        by_ext[ext] = by_ext.get(ext, 0) + 1

    for ext, cnt in sorted(by_ext.items()):
        print(f"  {ext}: {cnt}")

    # 写入 manifest
    manifest_path = target / "MANIFEST.txt"
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(f"Dogfood Sample Manifest\n")
        f.write(f"Generated: {datetime.now(timezone.utc).isoformat()}\n")
        f.write(f"Total files: {len(created)}\n\n")
        for p in sorted(created):
            f.write(f"  {p.relative_to(target)}\n")
    print(f"Manifest: {manifest_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
