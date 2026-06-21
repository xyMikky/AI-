# RunningHub API 错误码对照表

> 来源：RunningHub 官方文档 | 更新：2026-04-08
> 生图报错时，对照本表查找原因并采取对应措施。

---

## 错误码速查


| 错误码      | 英文名称                          | 中文含义        | 处理建议                                     |
| -------- | ----------------------------- | ----------- | ---------------------------------------- |
| **1000** | Unknown error                 | 未知错误        | 先怀疑 1012（模型响应异常）或 1005（内部错误），稍后重试        |
| 1001     | Invalid URL                   | 请求链接无效      | 检查调用的 API Endpoint 是否正确                  |
| 1002     | Invalid API Key               | API Key 无效  | 检查 config/.env 中的 RH_API_KEY 是否配置正确或已被禁用 |
| 1003     | Rate limit exceeded           | 请求频率超限      | 触发接口限流，降低并发频率，等待后重试                      |
| 1004     | Task not found                | 任务不存在或已过期   | 确认 task_id 是否正确，或任务是否已超过保存有效期            |
| 1005     | Internal server error         | 系统内部错误      | 平台内部异常，稍后重试                              |
| 1006     | Task execution timed out      | 任务执行超时      | 任务执行超时，尝试重新提交；考虑降低分辨率（2k→1k）减少处理时间       |
| 1007     | Invalid parameters            | 请求参数校验失败    | 检查输入的参数格式、类型或文件有效性                       |
| 1008     | File size limit exceeded      | 文件大小超出限制    | 压缩参考图后重试；避免传入超高分辨率原图                     |
| 1009     | HTTP method not supported     | 请求方法不支持     | 确认使用的是 GET、POST 或其他指定的请求方式               |
| 1010     | Service unavailable           | 服务暂不可用      | 系统维护或临时故障，稍后重试                           |
| 1011     | Model is currently busy       | 模型负载较高      | 当前模型资源紧张，等待 30-60s 后重试                   |
| 1012     | Model response exception      | 模型响应异常      | 模型输出不稳定，重试；若持续失败，简化 Prompt               |
| 1013     | File processing failed        | 文件处理失败      | 检查输入文件的链接是否可访问或文件是否损坏                    |
| 1014     | Access Denied                 | 权限不足        | 标准模型 API 仅限企业级共享 API Key 调用              |
| 1015     | Generation failed             | 生成失败        | 任务处理过程中出现异常，尝试重新提交                       |
| **1501** | Content security audit failed | 内容安全审查未通过   | 提示词或图片违反安全策略，修改 Prompt 措辞（去除敏感词）或更换参考图   |
| 1504     | Model timed out               | 模型响应超时      | 稍后重试；降低分辨率或减少参考图数量                       |
| 1506     | Voice ID duplicate            | 音频克隆 ID 重复  | 更换唯一的 voiceId                            |
| 1516     | External download failed      | 外部文件下载失败    | 无法从 URL 下载资源，检查链接或重试                     |
| 1517     | Upload failed                 | 文件上传失败      | 上传文件异常，重试；检查网络连接                         |
| 1518     | Base64 decode failed          | Base64 解码失败 | 检查 Base64 字符串格式是否标准                      |
| 1519     | Content processing exception  | 内容处理异常      | 处理输入内容时发生非预期错误，重试                        |
| 1520     | Concurrency limit reached     | 账号并发达到上限    | 等待已有任务完成后再发起新请求；避免同时发起超过账号并发上限的任务        |


---

## 生图报错诊断流程

```
生图报错
 ↓
查本表找错误码
 ├─ 1000（Unknown）→ 先怀疑 1012（模型响应异常）或 1005（内部错误），重试即可
 ├─ 1501（内容安全）→ 检查 Prompt 是否含敏感词；检查图片内容
 ├─ 1003/1520（限流/并发）→ 等待后重试，降低并发数
 ├─ 1006/1504（超时）→ 降低分辨率（2k→1k），减少参考图数量
 ├─ 1011（模型繁忙）→ 等待 30-60s 后重试
 └─ 其他 → 按对应处理建议操作
```

## 生图常见问题备注

- 1000 错误通常为平台侧暂时性故障，直接重试即可解决

