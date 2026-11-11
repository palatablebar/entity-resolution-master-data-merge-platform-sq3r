# entresolv · 实体解析与主数据合并台

区域连锁药房「康和」的会员档案鉴定室：把 POS / 电商 / 客服三套系统导出的同一批会员记录，
按 blocking 键捞出可疑对、逐字段加权打分、并查集成簇，再按来源可靠性仲裁出黄金档案。

## 真实场景

**模拟客户**：区域连锁药房「康和」会员主数据治理组（5 人），门店 120 家，POS / 电商 / 客服三套系统，会员重复率约 23%。

**现有工作流**：运营用 Excel 手工比对手机号与姓名，逐条合并；合并后字段取谁全凭经验。
三个痛点：① 同一个人 3 条记录，营销发券重复；② 手机号格式（`+86 138-0000-0001`）与地址写法不一致，无法自动匹配；
③ 合并后字段选谁没依据，回滚靠手工改表。

**上下游**：上游三源系统导出 CSV/JSON → 本系统做「规范化 → blocking → 加权打分 → 聚类 → 黄金记录仲裁」→
下游营销发券与积分系统消费黄金档案（CSV 导出）。

**角色权限**

| 角色 | 枚举 | 主要页面 | 典型动作 |
|---|---|---|---|
| 主数据管理员 | `admin` | 全部 | 改规则权重/阈值、发起解析、复核、导出、看审计 |
| 数据管家 | `curator` | 候选/簇/黄金/规则/运行 | 复核候选、确认合并、发起解析、导出 |
| 营销运营 | `marketing` | 黄金档案/运行（只读） | 查看并导出黄金档案；不能复核、不能发起解析（403） |

## 核心功能

- **候选对复核**：并置左右记录，逐字段展示 Jaro-Winkler / 归一化精确 / Token Jaccard 相似度、权重与贡献；确认或拒绝写入审计。
- **实体簇**：auto 边并查集连通成簇，review 边只结成待复核簇；簇置信度取簇内最小边分。
- **黄金档案**：字段级 reliability 仲裁（来源权重 × 字段完整度 × 30 天半衰期时间衰减），保留来源引用、落选候选与冲突标记，可导出 CSV。
- **规则与阈值**：字段权重、来源可靠性、auto/review 阈值可视化编辑，保存即升版；运行会快照参数。
- **运行报告**：blocking 命中 / 剪枝 / 候选 / 判定分布 / 簇数 / 黄金记录 / 耗时；worker 真实执行，前端轮询进度。
- **审计与限流**：登录、复核、规则改动、运行、导出全部落审计；运行触发走 Redis 滑动窗口限流。

## 快速启动

```bash
cp .env.example .env
docker compose up -d --build
# 等待 5 个服务 healthy
docker compose ps
# 演示数据由 SEED_DEMO=true 在 backend 启动时自动跑一次；也可手动执行（幂等）
docker compose exec -T backend python -m scripts.seed_demo
```

访问：

- 前端 `http://localhost:18222`
- 后端直连 `http://localhost:19222/api/health`
- PostgreSQL `localhost:17722`（库名/用户 `entresolv`）

演示账号（密码均为 `Demo@2026`）：

| 邮箱 | 角色 |
|---|---|
| `admin@master.local` | admin · 主数据管理员 |
| `curator@master.local` | curator · 数据管家 |
| `marketing@master.local` | marketing · 营销运营（只读） |

## 本地开发

```bash
# 后端（需本机 PostgreSQL 16 + Redis 7，或直接用 compose 起的 db/redis）
cd backend && pip install -r requirements.txt
python -m scripts.init_db
uvicorn src.main:app --reload --port 8000

# 前端（Vite 已代理 /api → localhost:19222）
cd frontend && npm install && npm run dev
```

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | React 18 + TypeScript + Vite + Zustand + react-router-dom |
| 后端 | Python 3.11 + FastAPI + SQLAlchemy 2.0 + Pydantic v2 + PyJWT |
| 异步 | Celery 5 + Redis 7（worker 执行解析任务，beat 心跳） |
| 数据库 | PostgreSQL 16（单 public schema，Alembic 目录保留） |
| 网关 | Nginx 1.27（`/api/` 反代 backend + SPA 回落） |

## 目录

```
backend/
  src/{config,constants,models,schemas,services,controllers,routes,middlewares,utils,algorithms,migrations}
  scripts/{init_db.py,seed_demo.py}
worker/            # 复用 backend 的模型/算法/服务，消费 Celery 任务
frontend/src/{api,stores,types,components/common,components/layout,hooks,pages,router,utils,constants,styles}
```

## 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `COMPOSE_PROJECT_NAME` | `entresolv` | 容器名前缀 |
| `FRONTEND_PORT` / `BACKEND_PORT` / `DB_PORT` | 18222 / 19222 / 17722 | 宿主端口 |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | `entresolv` / `entresolv` / `entresolv_pw_2026` | 数据库 |
| `JWT_SECRET` | 示例值 | JWT 签名密钥（生产必须替换） |
| `REDIS_URL` | `redis://redis:6379/0` | Celery broker/result + 限流 |
| `SEED_DEMO` | `true` | backend 启动时跑一次幂等 seed |
| `EVIDENCE_DIR` | `/data/evidence` | 命名卷挂载点（证据导出预留） |
| `AUTO_THRESHOLD` / `REVIEW_THRESHOLD` | 0.92 / 0.75 | 默认阈值（规则落库后以规则为准） |

## Docker 说明

- 5 个服务：`frontend`(Nginx) / `backend`(FastAPI) / `worker`(Celery) / `db`(PostgreSQL 16) / `redis`(7)，全部带 healthcheck。
- `backend`、`worker` 依赖 `db`/`redis` 的 `service_healthy`；`frontend` 依赖 `backend` healthy。
- 命名卷：`db_data`、`redis_data`、`evidence_data`（backend/worker 共享）。
- backend 镜像启动时先 `python -m scripts.init_db` 建表（create_all 起步），再起 uvicorn；`SEED_DEMO=true` 时 lifespan 内跑一次幂等 seed，失败只记 WARNING 不阻塞健康检查。

## 算法口径

**算法 1：blocking + 加权相似度**

- blocking 键（三路取并集）：手机归一化后后 4 位 / 姓名首字 + 去后缀城市 / 邮箱域名。
- 弱对剪枝：手机后 4 位相同、邮箱归一化相同、姓名 Jaro-Winkler ≥ 0.82 三选一，其余计入 `pruned_pairs`。
- 字段相似度：姓名 Jaro-Winkler（自实现，含 0.7 以上前缀加权）；手机、邮箱归一化精确；地址分词（中文 2-gram + 拉丁词）Token Jaccard。
- 总分 = Σ(权重 × 相似度) / Σ(可用字段权重)；缺失字段不按 0 分算。阈值 auto ≥ 0.92 / review ≥ 0.75 / else reject。

**算法 2：并查集聚类 + golden record 仲裁**

- 只把 auto 边并查集连通；review 边在未被 auto 簇覆盖的记录上再求连通分量，得到待复核簇。
- `reliability = 来源权重（POS 0.9 / 电商 0.8 / 客服 0.6）× 字段完整度 × 0.5^(距来源更新天数 / 30)`。
- 每个字段取 reliability 最高来源，记录引用、数值理由与落选候选；不同取值记入冲突字段并写审计。

## 共享枚举出现位置

1. 角色枚举 `admin/curator/marketing`：`backend/src/constants/roles.py`、`frontend/src/constants/roles.ts`、`backend/scripts/seed_demo.py`、README 账号表。
2. 解析枚举（来源系统 / 判定 / 状态 / 簇状态 / 黄金状态 / 运行状态）：`backend/src/constants/enums.py`、`frontend/src/constants/resolution.ts`、`frontend/src/types/models.ts`、API schema 序列化处。

## 测试产物

测试脚本、截图、日志与 `TESTING.md` 位于 `batch-20261110/test-artifacts/gb-549/`，不在源码目录内。

## License

MIT
