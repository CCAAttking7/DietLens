# 真实模型联调

## 配置

模型通过 `DIETLENS_MODEL` 配置选择，不固定绑定 DeepSeek。任一套餐可用、支持 Chat Completions 的文本模型均可通过相同适配器尝试接入；各模型兼容性须单独实测。

同济平台本次用户提供的入口为 `https://agi.tongji.edu.cn/v1`。其文档 curl 示例使用 `https://llmapi.tongji.edu.cn/v1`，不要未经验证自动切换或重定向携带密钥的请求。

在项目根目录的本地 `.env` 中填写：

```dotenv
DIETLENS_API_KEY=在本地填写
DIETLENS_MODEL_BASE_URL=https://agi.tongji.edu.cn/v1
DIETLENS_MODEL=DeepSeek-V4.1-Flash
DIETLENS_MODEL_TIMEOUT=10
DIETLENS_MODEL_JSON_MODE=false
# 仅在校园网/VPN可达、但本机DNS被代理改写时设置
DIETLENS_MODEL_RESOLVE_IP=10.67.0.251
```

`.env` 不进入版本控制，环境变量优先于文件，配置对象的 repr 隐藏密钥。可用 `--env-file` 选择独立文件。JSON mode 为 false 时不发送 `response_format`，通过提示词要求 JSON 后在本地按 Schema 验证；服务支持 JSON mode 时可设为 true。JSON mode 的有效 JSON 保证不替代 Schema 校验，参见 [OpenAI 官方结构化输出文档](https://developers.openai.com/api/docs/guides/structured-outputs)。

通过真实 `/v1/models` 已核验当前 Key 可见的其他文本模型为 `MiniMax-M3.1-Flash`、`GLM-5.3`、`MiMo-V2.6-Pro`、`GLM-5.3-Flash`、`Qwen3.8-Flash-Next`、`MiMo-V2.6-Flash`、`Qwen3.8-27B`；还可见 `Qwen3-Embedding`、`Qwen3-Reranker`。可见列表不保证每个模型都已完成生成兼容性测试。

用户提供的平台说明还列出其他文本模型，如 `MiniMax-M3.1-Flash`、`GLM-5.3`、`MiMo-V2.6-Pro`、`GLM-5.3-Flash`、`Qwen3.8-Flash-Next`、`MiMo-V2.6-Flash`、`Qwen3.8-27B`、`Qwen3.8-Max`、`Kimi-K3`，只需替换 Model ID。以上 ID 来自用户提供的套餐说明，尚未逐一验证访问权限与响应兼容性。语音、OCR、向量和重排的协议及业务工具后续单独接入。

## 单次联通检查

```bash
.venv/bin/python scripts/check_model.py
```

此命令会发送一条明确标注为合成数据的午餐情境，并将任务、调用额度与事件保存在 `data/model_checks.db`。不采纳行动、不保存执行反馈。输出 `ok: true` 才表示此次真实响应通过结构校验；降级明确返回 `ok: false` 和非零退出码。

## 交互闭环

```bash
.venv/bin/python cli.py --model
```

按提示建立演示档案，再提供情境文字。模型只提取餐次与选项，用户核对后才进入确定性候选生成；用户选择采纳后形成待反馈行动；反馈 `unknown` 不计为完成或失败。暂不反馈时会打印任务 ID，可用同一数据库恢复：

```bash
.venv/bin/python cli.py --resume TASK_ID
```

模型调用失败时显示原因并进入手动输入。调用预算耗尽也可手动继续。每次网络调用前先持久化额度预留和 `model.called`，网络等待不占 SQLite 写锁。成功或失败记录 `model.result`，通过 call_id 关联；不保存原始请求/响应。服务未返回 token 用量时保留未知，不填零；当前未计算实际货币费用。

HTTP 超时不自动重试，避免在计费结果不明时重复请求；当前本地默认超时为 10 秒。鉴权失败、权限限制、限流、网络故障及响应不完整使用独立错误码。HTTPS 重定向不会自动转发密钥。传输超时覆盖连接和 socket 读操作，尚非独立可取消的整体墙钟期限。情境解析超时后，Harness 会从用户原话确定性提取餐次和可选餐食，仍需用户核对。

## 本次真实调用结果

2026-10-31 已完成真实 DeepSeek 调用闭环，任务 ID `60d04ac0-d168-414e-8d0b-a364320576dd`，联调数据库 `data/synthetic_loop.db`。情境由用户选定为合成测试：午餐、鸡肉饭/番茄面、预算 30 元、无已知过敏，反馈为 `unknown`。

本次真实响应通过 Schema 校验，平台报告输入 358 token、输出 225 token。提取情境后生成饮品微行动，采纳后不计完成，提交 unknown 后回顾为 `adopted=1`、`completed=0`、`feedback_coverage=0.0`。关闭数据库后重新打开并重放相同反馈/回顾，结果一致，无重复行动。

网络根因是本机代理将域名解析为 `198.18.0.94`，经代理出口收到平台 HTTP 403“当前网络环境不支持”。按用户提供的校方说明，使用内网 `10.67.0.251/252` 并保留 `agi.tongji.edu.cn` 的 Host、SNI 与 TLS 证书校验后，模型列表接口均返回 200。

新增 `DIETLENS_MODEL_RESOLVE_IP` 是仅在该 Provider 内生效的 TCP 地址覆盖，启用时此 Provider 不走环境代理；不会修改系统 hosts、DNS、路由或代理设置。配置为空时保持正常 DNS 和环境代理行为。此配置要求当前机器确实能访问校园内网，不能替代校园 VPN。

`Qwen3.8-Max`、`Kimi-K3`、语音及 OCR 未出现在此次当前 Key 的模型列表中。尚未逐一对其他可见模型发起生成请求。

后续已验证 MiniMax 的独立情境路由及 JSON mode，配置与结果见 `docs/model-routing.md`。新版 CLI 的档案预览、确认和分项授权见 `docs/profile-workflow.md`；旧演示档案未包含的确认信息需要用户重新核对。
