# AKiL Blog Backend — API 对接契约

供 Nuxt 前端（后台编辑页、公开博客）对接使用。文章 CRUD 已基于真实 MySQL 联调验证通过；
OSS 部分因当前没有真实凭证，仅完成签名逻辑、缺失配置处理与 Mock 测试，尚未做真实上传联调。

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

## 3. 管理端文章列表

`GET /api/v1/admin/articles`（需要 Bearer 认证）

查询参数：

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| page | integer | 否 | `1` | 页码，最小 `1` |
| page_size | integer | 否 | `10` | 每页条数，范围 `1–100` |
| status | string | 否 | 不筛选 | `"draft"` / `"published"`；其他值返回 422 |

排序：`created_at` 倒序，同一时间按 `id` 倒序，保证分页结果稳定。

成功 `200`：

```json
{
  "items": [
    {
      "id": 3,
      "title": "草稿示例",
      "slug": "draft-example",
      "summary": null,
      "status": "draft",
      "created_at": "2026-11-17T15:10:00",
      "updated_at": "2026-11-17T15:10:00",
      "published_at": null
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 10,
  "total_pages": 1
}
```

说明：

- `items` 不包含 `content_markdown`，列表页不要依赖完整正文。
- 传入超过末页的 `page` 时返回空 `items`，`total` 等分页元信息不变。
- 无文章时 `total = 0`、`total_pages = 0`。

## 4. 管理端文章详情

`GET /api/v1/admin/articles/{id}`（需要 Bearer 认证）

路径参数：`id` 为整数文章 ID。

成功 `200`（草稿和已发布文章均可查看）：

```json
{
  "id": 3,
  "title": "草稿示例",
  "slug": "draft-example",
  "summary": null,
  "status": "draft",
  "created_at": "2026-11-17T15:10:00",
  "updated_at": "2026-11-17T15:10:00",
  "published_at": null,
  "content_markdown": "# 标题\n\nMarkdown 原文"
}
```

文章不存在 `404`：

```json
{ "detail": "文章不存在" }
```

## 5. 图片上传授权（OSS 直传）

`POST /api/v1/admin/media/upload-signature`（需要 Bearer 认证）

前端先校验图片，再获取短期预签名 URL；图片文件本身直接 `PUT` 到 OSS，不经过 FastAPI。

请求体：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| filename | string | 是 | 1–255 字符。仅作为元数据，不用于生成 Object Key |
| content_type | string | 是 | 仅支持 `image/png`、`image/jpeg`、`image/webp`、`image/gif` |
| size | integer | 是 | 图片字节数，必须大于 0，最大 10MB（`OSS_MAX_IMAGE_SIZE_BYTES` 可配置） |

```json
{
  "filename": "screenshot.png",
  "content_type": "image/png",
  "size": 245760
}
```

成功 `200`：

```json
{
  "upload_url": "https://your-bucket.oss-cn-hangzhou.aliyuncs.com/articles/2026/11/5f0c...e1.png?OSSAccessKeyId=...&Expires=...&Signature=...",
  "method": "PUT",
  "headers": { "Content-Type": "image/png" },
  "object_key": "articles/2026/11/5f0c...e1.png",
  "public_url": "https://img.example.com/articles/2026/11/5f0c...e1.png",
  "expires_in": 300
}
```

### 前端上传流程

1. 校验文件 MIME 与大小，不满足时直接提示，不请求后端。
2. 携带 JWT 调用本接口。
3. 使用返回的 `upload_url`、`method`、`headers` 直接上传文件；不要给 OSS 请求附加 FastAPI 的 Bearer token。
4. 上传成功后，在当前光标处插入 `![图片说明](public_url)`；失败时不插入任何链接，保留重试入口。
5. 需要上传进度时使用 `XMLHttpRequest.upload.onprogress`（原生 `fetch` 不提供上传进度）。

```js
const signature = await $fetch('/api/v1/admin/media/upload-signature', {
  method: 'POST',
  headers: { Authorization: `Bearer ${token}` },
  body: { filename: file.name, content_type: file.type, size: file.size }
})

await new Promise((resolve, reject) => {
  const xhr = new XMLHttpRequest()
  xhr.open(signature.method, signature.upload_url)
  Object.entries(signature.headers).forEach(([key, value]) => xhr.setRequestHeader(key, value))
  xhr.upload.onprogress = (event) => {
    if (event.lengthComputable) progress.value = event.loaded / event.total
  }
  xhr.onload = () => (xhr.status >= 200 && xhr.status < 300 ? resolve() : reject(xhr))
  xhr.onerror = () => reject(new Error('OSS 上传失败'))
  xhr.send(file)
})
```

说明：

- Object Key 由后端使用日期路径 + UUID 生成，扩展名来自 `content_type`，不信任原始文件名，避免重名与路径穿越。
- 正文只保存 `public_url`，不保存临时签名 URL。
- `upload_url` 默认 5 分钟过期；过期后应重新申请，不要复用。
- 缺少任一 OSS 配置时返回 `503`，不会返回伪造签名或伪造上传成功。
- 当前交付状态：签名与校验逻辑已通过 Mock OSS 自动化测试；配置真实凭证后仍需完成一次真实浏览器直传联调。

### OSS 配置与权限要求

- Bucket、Endpoint、Region、AccessKey、图片访问域名全部通过环境变量配置，见 `.env.example`。
- 建议 Bucket 不开放公共写权限；RAM 用户仅授予 `articles/*` 前缀的 `PutObject` 权限。
- 图片长期访问依赖 `OSS_PUBLIC_BASE_URL`：可配置 OSS 自定义域名或 CDN；如果 Bucket 为私有读，需要额外配置 CDN 回源/签名读策略，否则浏览器无法长期显示图片。
- OSS Bucket 必须配置 CORS，否则浏览器直传会被拦截。开发与生产建议：
  - 来源：`http://localhost:3000`、实际前端域名
  - 方法：`PUT`、`GET`、`HEAD`
  - 允许请求头：`Content-Type`
  - 暴露响应头：`ETag`
  - 缓存时间：按需设置
- 前端不得持有或打包 AccessKey；AccessKey 只存在后端环境变量中。

## 6. 修改文章

`PATCH /api/v1/admin/articles/{id}`（需要 Bearer 认证）

支持部分字段更新。请求中未出现的字段保持不变；`summary` 显式传 `null` 可清空摘要，其他字段传 `null` 返回 422。

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| title | string | 否 | 1–200 字符，纯空白非法 |
| slug | string | 否 | 规则同新增；修改后仍需全局唯一 |
| summary | string \| null | 否 | ≤500 字符；`null` 表示清空 |
| content_markdown | string | 否 | Markdown 原文 |
| status | string | 否 | `"draft"` / `"published"` |

状态与发布时间规则：

- 草稿首次发布：生成 `published_at`。
- 已发布文章普通修改：保留原 `published_at`。
- 已发布改回草稿：清空 `published_at`。
- 已发布状态（含更新后仍为已发布）要求正文非空白，否则 422。
- `updated_at` 在成功修改后更新。

请求示例（发布草稿）：

```json
{
  "title": "更新后的标题",
  "summary": "新的摘要",
  "content_markdown": "# 更新后的正文",
  "status": "published"
}
```

成功 `200`：返回与管理端详情相同的完整文章对象，包含 `content_markdown` 和最新的 `published_at`、`updated_at`。

错误：

- `404`：文章不存在。
- `409`：slug 与其他文章冲突。
- `422`：空请求体、空白标题、非法 slug、非法状态、发布空正文等。

## 7. 删除文章

`DELETE /api/v1/admin/articles/{id}`（需要 Bearer 认证）

- 当前为数据库物理删除，不可恢复。
- 成功返回 `204 No Content`，响应体为空。
- 文章不存在返回 `404`。
- 删除后管理端列表/详情、公开端列表/详情均不再返回该文章。
- 不会自动删除文章中引用的 OSS 图片，避免误删其他文章仍在使用的资源。

前端必须二次确认并明确提示“删除不可恢复”；公开博客页面不提供删除入口。

## 8. 公开文章列表

`GET /api/v1/articles`（无需认证）

查询参数：

| 参数 | 类型 | 必填 | 默认 | 说明 |
|---|---|---|---|---|
| page | integer | 否 | `1` | 页码，最小 `1` |
| page_size | integer | 否 | `10` | 每页条数，范围 `1–100` |

- 仅返回 `status = "published"` 的文章，草稿不会出现在结果中。
- 排序：`published_at` 倒序，同一时间按 `id` 倒序。
- 响应结构与管理端列表一致，但 `items` 使用公开端字段。

成功 `200`：

```json
{
  "items": [
    {
      "id": 2,
      "title": "已发布示例",
      "slug": "published-example",
      "summary": "摘要",
      "published_at": "2026-11-17T15:00:00"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 10,
  "total_pages": 1
}
```

说明：列表不返回 `content_markdown`、`status`、`created_at`、`updated_at`。

## 9. 公开文章详情

`GET /api/v1/articles/{slug}`（无需认证）

路径参数：`slug` 为文章唯一 slug。

- 只允许访问已发布文章；草稿、未知 slug 均返回相同 `404`，不泄露草稿是否存在。
- 成功 `200` 返回渲染所需的完整 Markdown 原文。

```json
{
  "id": 2,
  "title": "已发布示例",
  "slug": "published-example",
  "summary": "摘要",
  "published_at": "2026-11-17T15:00:00",
  "content_markdown": "# 标题\n\n正文 Markdown 原文",
  "created_at": "2026-11-17T14:58:07",
  "updated_at": "2026-11-17T15:00:00"
}
```

不存在或未发布 `404`：

```json
{ "detail": "文章不存在" }
```

## 10. 健康检查

`GET /api/v1/health`（无需认证，不依赖数据库）

```json
{ "status": "ok", "app_name": "AKiL Blog", "environment": "development" }
```

## 错误码

| HTTP | 场景 | 响应体 |
|---|---|---|
| 401 | 未携带 token / token 无效或过期 / 登录失败 | `{ "detail": "错误说明" }`，带 `WWW-Authenticate: Bearer` 头 |
| 404 | 管理端文章 ID 不存在 / 公开端 slug 不存在或文章未发布 | `{ "detail": "文章不存在" }` |
| 409 | slug 已存在 | `{ "detail": "slug 已存在: xxx" }` |
| 422 | 业务校验失败（发布空正文、空白标题、slug 格式非法、图片类型/大小非法、空更新请求） | `{ "detail": "错误说明" }` |
| 422 | 请求体或查询参数校验失败（缺字段、超长、status 非法、page/page_size 越界等，FastAPI 标准格式） | `{ "detail": [{ "loc": ["body", "title"], "msg": "...", "type": "..." }] }` |
| 503 | OSS 配置不完整或配置格式错误，无法签发上传 URL | `{ "detail": "OSS 配置不完整，缺少: OSS_BUCKET, ..." }` |

前端注意：422 存在两种响应体结构（字符串 detail 与数组 detail），建议统一容错处理。

## 本次未提供

文章搜索、分类、标签、OSS 文件管理后台、孤立图片自动清理、服务器部署。

前端工程若不在当前工作区，需按本文件独立完成：编辑器三入口（粘贴/拖拽/工具栏）复用同一上传方法；后台编辑复用现有 Markdown 编辑器；删除需二次确认。