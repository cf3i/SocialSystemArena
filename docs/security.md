# Security

> 本文档回答：什么不能碰？什么要小心？

## 敏感信息清单

| 类型 | 示例 | 存储方式 | 禁止行为 |
| --- | --- | --- | --- |
| LLM API Key | pc-agent-loop 的 `mykey.py` 中配置的各模型 API key | 本地文件（`third_party/pc-agent-loop/mykey.py`，由子模块内部 `.gitignore` 排除；主仓库 `.gitignore` 亦已添加 `mykey.py` 规则） | 写入代码仓库 |
| OpenAI-compatible API Key | `OPENAI_API_KEY` 环境变量（claw-eval adapter 使用） | 环境变量 | 写入代码仓库、打印到日志 |
| Dispatch 日志配置 | `DISPATCH_LOG_FILE`、`DISPATCH_TRACE_ID` | 环境变量 | 泄漏到外部 |

## 受保护路径

- `third_party/pc-agent-loop/mykey.py`（API key 配置，不应提交）
- `.env`（当前不存在，若创建则不应提交）

## 认证与授权

- 认证方式：本项目无用户认证系统；LLM 调用通过 adapter 层传入 API key
- Token 生命周期：由外部 LLM 提供商管理
- 权限模型：当前无权限管理

## 安全变更规则

1. 涉及认证、权限、密钥的改动必须在 PR 中标注 `security-impact`。
2. 任何敏感值只允许通过环境注入，不得硬编码。
3. 发现泄漏后先轮转密钥，再修代码与文档。
