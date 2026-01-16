# API 文档索引

> XMMCG 项目的完整 API 文档已整合成单一文件

## 📘 综合文档

### [COMPREHENSIVE_API.md](./COMPREHENSIVE_API.md) ⭐ **推荐使用**

**包含内容**:
- 用户认证 API (8 个端点)
- 虚拟货币 API (4 个端点)
- 歌曲管理 API (6 个端点)
- 错误处理指南
- 安全特性说明
- 前端集成示例（JavaScript/Vue 3）
- 常见问题解答
- 技术栈信息
- 部署检查清单

**文件大小**: ~400KB  
**更新时间**: 2026-01-16  
**覆盖范围**: 100% API 端点

---

## 📋 原始文档（已弃用，仅供参考）

### [API_DOCS.md](./backend/xmmcg/API_DOCS.md)
- 用户认证 API 文档
- 已被整合到 COMPREHENSIVE_API.md

### [TOKEN_API_GUIDE.md](./backend/xmmcg/TOKEN_API_GUIDE.md)
- 虚拟货币系统 API 文档
- 已被整合到 COMPREHENSIVE_API.md

### [SONG_API_GUIDE.md](./SONG_API_GUIDE.md)
- 歌曲管理 API 文档
- 已被整合到 COMPREHENSIVE_API.md

---

## 🚀 快速开始

### 对于前端开发者
1. 打开 [COMPREHENSIVE_API.md](./COMPREHENSIVE_API.md)
2. 查看"前端集成"章节
3. 复制 API 服务代码模板
4. 根据项目需要调整

### 对于后端开发者
1. 打开 [COMPREHENSIVE_API.md](./COMPREHENSIVE_API.md)
2. 查看相应的 API 端点说明
3. 参考错误处理和安全特性章节

### 对于项目经理/产品经理
1. 阅读"概述"章节了解核心功能
2. 查看"API 端点总结"表格
3. 了解数据流和集成要点

---

## 📊 API 端点总览

### 用户认证 (8 个端点)
| 功能 | 端点 | 方法 | 认证 |
|------|------|------|------|
| 注册 | `/api/users/register/` | POST | ❌ |
| 登录 | `/api/users/login/` | POST | ❌ |
| 登出 | `/api/users/logout/` | POST | ✅ |
| 获取当前用户 | `/api/users/me/` | GET | ✅ |
| 更新个人信息 | `/api/users/profile/` | PUT/PATCH | ✅ |
| 修改密码 | `/api/users/change-password/` | POST | ✅ |
| 检查用户名 | `/api/users/check-username/` | POST | ❌ |
| 检查邮箱 | `/api/users/check-email/` | POST | ❌ |

### 虚拟货币 (4 个端点)
| 功能 | 端点 | 方法 | 认证 |
|------|------|------|------|
| 获取余额 | `/api/users/token/` | GET | ✅ |
| 设置余额 | `/api/users/token/update/` | POST | ✅ |
| 增加 Token | `/api/users/token/add/` | POST | ✅ |
| 扣除 Token | `/api/users/token/deduct/` | POST | ✅ |

### 歌曲管理 (6 个端点)
| 功能 | 端点 | 方法 | 认证 |
|------|------|------|------|
| 上传歌曲 | `/api/songs/` | POST | ✅ |
| 获取用户歌曲 | `/api/songs/me/` | GET | ✅ |
| 更新歌曲信息 | `/api/songs/me/` | PUT | ✅ |
| 删除歌曲 | `/api/songs/me/` | DELETE | ✅ |
| 列表 | `/api/songs/` | GET | ❌ |
| 详情 | `/api/songs/{id}/` | GET | ❌ |

**总计**: 18 个 API 端点

---

## ✨ 文档特点

✅ **完整性** - 涵盖所有 API 端点和功能  
✅ **实用性** - 包含实际代码示例和 cURL 命令  
✅ **易用性** - 清晰的目录结构和导航链接  
✅ **专业性** - 遵循 OpenAPI 规范思想  
✅ **多语言** - 支持 JavaScript/Vue 的集成示例  
✅ **安全性** - 详细的安全特性说明  
✅ **易维护** - 单一文件便于版本控制  

---

## 📝 使用建议

### 开发阶段
- 使用 COMPREHENSIVE_API.md 作为主要参考
- 在 Git 中追踪文档变化
- 每次 API 变更都更新文档

### 测试阶段
- 使用 Postman 导入 API 描述
- 运行提供的 cURL 示例进行测试
- 验证所有错误场景

### 生产部署
- 导出 API 文档为 PDF 保存
- 在 API Gateway 中注册端点
- 配置速率限制和监控

### 团队协作
- 在团队 Wiki 中链接到此文档
- 在代码审查中引用相关章节
- 定期更新文档反映代码变更

---

## 🔄 文档同步

当 API 发生变更时，请按照以下步骤更新文档：

1. 在 COMPREHENSIVE_API.md 中更新相应章节
2. 更新对应的状态码和响应示例
3. 如需要，更新前端集成代码示例
4. 提交 Git commit 时附带文档变更说明
5. 通知团队成员已更新文档

---

## 📖 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0 | 2026-01-16 | 初始综合版本，整合三个分散的文档 |

---

## 🎯 后续工作

- [ ] 导出为 PDF 格式以便离线查看
- [ ] 生成 OpenAPI/Swagger 规范文件
- [ ] 创建 Postman Collection 用于测试
- [ ] 录制 API 使用教程视频
- [ ] 添加更多的错误场景示例
- [ ] 集成 API 监控和日志说明
- [ ] 创建多语言版本

---

## 💡 相关资源

- [QUICK_START.md](./backend/xmmcg/QUICK_START.md) - 快速启动指南
- [TEST_RESULTS.md](./TEST_RESULTS.md) - 测试结果报告
- [requirements.txt](./backend/xmmcg/requirements.txt) - 项目依赖

---

**建议**: 将此文档链接添加到项目 README 中，便于新开发者快速了解 API。

例如在 README.md 中添加：
```markdown
## API 文档

请查看 [COMPREHENSIVE_API.md](./COMPREHENSIVE_API.md) 获取完整的 API 文档。

**快速链接**:
- [用户认证 API](#用户认证-api)
- [虚拟货币 API](#虚拟货币-api)
- [歌曲管理 API](#歌曲管理-api)
```

---

**最后更新**: 2026-01-16  
**维护者**: GitHub Copilot
