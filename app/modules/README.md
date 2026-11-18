# 业务模块开发约定

每个业务模块（文章、分类、标签、认证、媒体等）在本目录下建立独立包，统一结构：

```text
app/modules/<module>/
├── __init__.py
├── models.py        # SQLAlchemy ORM 模型（继承 infrastructure.database.base.Base）
├── schemas.py       # Pydantic 请求 / 响应模型
├── repository.py    # 数据库操作，不做业务决策，不擅自 commit
└── service.py       # 业务规则与流程编排，统一控制事务
```

对应路由独立放在 API 层：

```text
app/api/v1/admin/<module>.py    # 管理端，挂载于 /api/v1/admin
app/api/v1/public/<module>.py   # 公开端，挂载于 /api/v1
```

并在 `app/api/v1/router.py`（V1 唯一聚合入口）中直接注册。

## 依赖方向

```text
Router → Service → Repository → Model
```

- Router：参数校验入口、认证依赖、调用 Service、返回响应；禁止直接写数据库查询。
- Service：业务规则、流程编排、事务控制（commit / rollback）。
- Repository：增删改查与持久化，不处理 HTTP，不做业务决策。
- Schema 与 Model 严格分离，禁止把 ORM 模型直接当作请求 / 响应模型。

## 其他规则

1. 业务代码属于哪个模块就放在哪个模块；跨模块复用的能力才进 `core` / `infrastructure`。
2. 禁止把所有业务逻辑堆到一个文件；也禁止为简单 CRUD 造无意义抽象。
3. 模块之间不得随意调用对方内部实现；确需协作时通过对方 Service 的公开接口。
4. 新增模块的 models 必须在 `alembic/env.py` 中导入，表结构变更一律走 Alembic 迁移，
   禁止 `Base.metadata.create_all()`。
5. JWT、密码哈希、OSS SDK 等依赖在对应模块开发时才加入 requirements.txt。