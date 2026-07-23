# Stage H Agent (WIP — H0 + H1 + H2)

评论洞察 Agent：DeepSeek 大模型 + 白名单工具 → 阶段 G FastAPI。

## 已完成

### H0
- `HttpApiAdapter` + `python -m agent.scripts.ping_kpi`

### H1
- 四取数工具 + `openai_tools()` / `run_tool()`
- `python -m agent.scripts.tools_smoke`
- 非法 `aspect` → `invalid_args`

### H2
- DeepSeek + orchestrator + `POST /api/agent/chat`

### H5
- 大屏「智能问答」抽屉

### H6（方案 A）
- `get_sentiment_trend` / `get_alerts` / `search_review_samples`
- 经 `HttpApiAdapter` 调 Stage G `/api/trend|alerts|samples`（501 → `not_available_in_smoke`）
- 自测：`python -m agent.scripts.placeholders_smoke`

## 环境变量

复制 `agent/.env.example` → `agent/.env`，填入：

```env
LLM_API_KEY=sk-...
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
```

**勿提交 `.env`。** 若 Key 曾出现在聊天记录中，建议在 DeepSeek 控制台轮换。

## 自测（仓库根）

```bat
set PYTHONPATH=%CD%
backend\start.bat
.venv\Scripts\python.exe -m agent.scripts.ping_kpi
.venv\Scripts\python.exe -m agent.scripts.tools_smoke
.venv\Scripts\python.exe -m agent.scripts.chat_smoke
```

HTTP：

```bat
curl.exe -s -X POST http://127.0.0.1:8080/api/agent/chat -H "Content-Type: application/json" --data-binary "@req.json"
```

## 下一步

**H3** 联调剧本文档；**H4** 周报；**H5** 大屏问答 UI。
