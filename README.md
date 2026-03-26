# Java Backend Resume Screener MVP

一个面向 `Java后端工程师` 岗位的简历初筛 MVP 后端。

当前版本提供：

- 岗位筛选规则查看与更新
- 简历上传
- 本地简历解析
- 规则评分与面试建议
- 筛选结果列表与详情
- 人工复核结果保存
- LLM 简历结构化提取，失败时回退到规则抽取

## Quick Start

要求本机安装 `Python 3.8+`。

```powershell
py -3.8 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -3.8 -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

如需启用 LLM 提取，请配置环境变量：

```powershell
$env:LLM_API_KEY="your-key"
$env:LLM_BASE_URL="https://api.openai.com"
$env:LLM_MODEL="gpt-4o-mini"
```

服务默认地址：

- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`

## API Overview

- `GET /api/v1/job-rule`
- `PUT /api/v1/job-rule`
- `POST /api/v1/resumes/upload`
- `POST /api/v1/screenings/run`
- `POST /api/v1/screenings/rerun-all`
- `GET /api/v1/screenings/tasks/{task_id}`
- `GET /api/v1/screenings/results`
- `GET /api/v1/screenings/results/{screening_id}`
- `POST /api/v1/screenings/results/{screening_id}/review`
- `GET /api/v1/resumes/{resume_id}`
- `POST /api/v1/resumes/{resume_id}/retry`
- `POST /api/v1/resumes/retry-all`

## Notes

- 数据使用本地 JSON 文件存储，适合快速验证 MVP。
- 简历解析优先支持 `.txt`，同时兼容 `.pdf/.docx` 的基础文本抽取。
- 当前评分为可解释规则评分，后续可平滑替换为 `规则 + LLM 抽取`。
- 当前默认优先走 LLM 抽取，若未配置或调用失败，会自动回退到规则抽取。

## Quick Demo

1. 启动服务
2. 上传 [sample_resume_java.txt](/D:/OpenClaw_sandbox/cv-reviewer-ai-backend/data/sample_resume_java.txt)
3. 调用 `POST /api/v1/screenings/run`
4. 查看 `GET /api/v1/screenings/results`
