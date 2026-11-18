# AKiL Blog Backend — API 对接契约

供 Nuxt 前端（Markdown 编辑页）对接使用。基于真实 MySQL 联调验证通过。

- Base URL：`http://127.0.0.1:8000/api/v1`（开发环境）
- 数据格式：请求与响应均为 `application/json; charset=utf-8`
- 在线文档：`/docs`（Swagger）、`/openapi.json`

## 认证方式

除登录和健康检查外，管理端接口均需携带 JWT：

```http
Authorization: Bearer <access_token>
```

- token 有效期 24 小时（`JWT_EXPIRE_MINUTES=1440`），无刷新接口；收到 401 时前端应跳转重新登录。
- 单管理员模式，无注册接口。

## 1. 管理员登录

`POST /api/v1/admin/auth/login`（无需认证）

请求体：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| username | string | 是 | 1–50 字符 |
| password | string | 是 | 1–128 字符 |

```json
{ "username": "admin", "password": "你的密码" }
```

成功 `200`：

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

失败 `401`：

```json
{ "detail": "用户名或密码错误" }
```

## 2. 新增文章

`POST /api/v1/admin/articles`（需要 Bearer 认证）

请求体：

| 字段 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| title | string | 是 | — | 1–200 字符，纯空白视为非法 |
| slug | string | 否 | 自动生成 | ≤200 字符，仅小写字母 / 数字 / 连字符，不能以连字符开头结尾；全局唯一 |
| summary | string | 否 | null | ≤500 字符 |
| content_markdown | string | 否 | `""` | Markdown 原文，后端原样存储，不生成 HTML |
| status | string | 否 | `"draft"` | 仅 `"draft"` / `"published"` |

草稿与发布的区别：

- `draft`：允许正文为空；`published_at` 为 `null`。
- `published`：要求有效标题且正文非空白，否则 422；创建即记录 `published_at`。

slug 规则：

- 手动指定时原样校验（自动转小写、去首尾空白），重复返回 409。
- 未指定时从标题提取 ASCII 字母数字生成；纯中文标题生成 `post-<12位哈希>`，保证非空且 URL 安全；与已有 slug 冲突时自动追加 `-2`、`-3` 序号。

请求示例（直接发布）：

```json
{
  "title": "我的第一篇文章",
  "slug": "my-first-post",
  "summary": "摘要可选",
  "content_markdown": "# 标题\n\n正文 Markdown 原文",
  "status": "published"
}
```

成功 `201`：

```json
{
  "id": 2,
  "title": "我的第一篇文章",
  "slug": "my-first-post",
  "summary": "摘要可选",
  "status": "published",
  "created_at": "2026-11-17T14:58:07",
  "updated_at": "2026-11-17T14:58:07",
  "published_at": "2026-11-17T14:58:07"
}
```

说明：

- 响应不回传 `content_markdown`（前端本地已有原文）。
- 时间字段为 UTC、ISO 8601 格式；MySQL DATETIME 不带时区后缀，前端按 UTC 解析。
- 草稿响应中 `published_at` 为 `null`。

## 3. 健康检查

`GET /api/v1/health`（无需认证，不依赖数据库）

```json
{ "status": "ok", "app_name": "AKiL Blog", "environment": "development" }
```

## 错误码

| HTTP | 场景 | 响应体 |
|---|---|---|
| 401 | 未携带 token / token 无效或过期 / 登录失败 | `{ "detail": "错误说明" }`，带 `WWW-Authenticate: Bearer` 头 |
| 409 | slug 已存在 | `{ "detail": "slug 已存在: xxx" }` |
| 422 | 业务校验失败（发布空正文、空白标题、slug 格式非法） | `{ "detail": "错误说明" }` |
| 422 | 请求体字段校验失败（缺字段、超长、status 非法值等，FastAPI 标准格式） | `{ "detail": [{ "loc": ["body", "title"], "msg": "...", "type": "..." }] }` |

前端注意：422 存在两种响应体结构（字符串 detail 与数组 detail），建议统一容错处理。

## 本次未提供

文章修改 / 删除 / 列表 / 详情查询、分类、标签、媒体上传、公开端文章接口。