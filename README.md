# AKiL Blog Backend

个人网站与博客的后端服务。模块化单体（Modular Monolith）+ 分层架构，单一 FastAPI 应用、单一部署单元。

## 技术栈

FastAPI · Pydantic 2 · pydantic-settings · SQLAlchemy 2（同步）· MySQL 8 + PyMySQL · Alembic · PyJWT + Argon2 · 阿里云 OSS · Ruff · Pytest + HTTPX · Uvicorn

> Python 要求 3.12+；当前本机暂用 3.10.4 开发（代码保持 3.10 兼容），升级后重建 venv 即可。

## 环境准备

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt        # 运行时依赖
pip install -r requirements-dev.txt    # 开发依赖（已继承运行时依赖）
```

复制环境配置并按本机 MySQL 修改（`.env` 已被 Git 忽略，不要提交真实密码）。
`JWT_SECRET_KEY` 为必填项，请生成随机值：

```bash
cp .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

本地 MySQL 中创建数据库：

```sql
CREATE DATABASE akil_blog DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 图片上传 / 阿里云 OSS

图片采用 Nuxt 前端直传 OSS：后端只签发短期预签名 PUT URL，不中转文件。
将 `.env.example` 中的 `OSS_BUCKET`、`OSS_ENDPOINT`、`OSS_REGION`、
`OSS_ACCESS_KEY_ID`、`OSS_ACCESS_KEY_SECRET`、`OSS_PUBLIC_BASE_URL` 填完整后，
`POST /api/v1/admin/media/upload-signature` 才可用；缺失时返回 503，不会伪造成功。

- AccessKey 只放后端环境变量，不能进入前端。
- 建议使用最小权限 RAM 用户，仅授予 `OSS_UPLOAD_PREFIX` 前缀的 `PutObject`。
- Bucket 不开放公共写权限；`OSS_PUBLIC_BASE_URL` 指向图片自定义域名/CDN。
- OSS Bucket 需配置 CORS，允许前端域名的 `PUT`、`GET`、`HEAD`，允许
  `Content-Type` 请求头，并暴露 `ETag`。详见 `API.md`。

## 启动

```bash
uvicorn app.main:app --reload
```

- 健康检查：<http://127.0.0.1:8000/api/v1/health>（不依赖 MySQL）
- Swagger 文档：<http://127.0.0.1:8000/docs>

## 数据库迁移（Alembic）

表结构变更统一走 Alembic，禁止 `create_all()` 自动建表。

```bash
alembic revision --autogenerate -m "描述"   # 生成迁移脚本
alembic upgrade head                        # 应用迁移
alembic downgrade -1                        # 回退一步
alembic current                             # 查看当前版本
```

新增业务模块后，需在 `alembic/env.py` 中导入该模块的 models，autogenerate 才能发现新表。

## 管理员初始化与认证

单管理员模式，无公开注册。执行迁移建表后初始化一次：

```bash
python -m scripts.init_admin
```

账号密码交互式输入（也可在 `.env` 配置 `ADMIN_USERNAME` / `ADMIN_PASSWORD` 走非交互模式）。
密码使用 Argon2 哈希存储；重复初始化会被拒绝。

登录获取 JWT：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/admin/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "你的密码"}'
```

管理端接口携带 `Authorization: Bearer <access_token>`。新增文章：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/admin/articles \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"title": "文章标题", "content_markdown": "# 正文", "status": "published"}'
```

`status` 为 `draft`（默认，允许空正文）或 `published`（要求非空正文）；
`slug` 可省略，自动从标题生成（纯中文标题用哈希兜底），重复时自动加序号。

## 代码检查与测试

```bash
ruff check .     # 代码检查
ruff format .    # 格式化
pytest           # 测试
```

## 目录结构

```text
app/
├── main.py                  # 应用入口
├── api/v1/                  # 路由层：health + admin / public 分组
├── modules/                 # 业务模块（开发约定见 modules/README.md）
├── core/                    # 配置、日志等公共基础能力
└── infrastructure/database/ # Engine、Session、DeclarativeBase
alembic/                     # 数据库迁移
tests/                       # Pytest 测试
scripts/                     # 运维 / 工具脚本
```

分层依赖方向：`Router → Service → Repository → Model`，Schema 与 Model 严格分离。
详见 [app/modules/README.md](app/modules/README.md)。

## 当前状态

已完成：工程基础设施、管理员登录认证（JWT + Argon2）、文章新增 / 查询 / 修改 / 物理删除、
管理端与公开端文章列表和详情、OSS 图片直传授权（Media 模块）。

尚未开发：文章搜索、分类、标签、OSS 文件管理后台、孤立图片清理、服务器部署。