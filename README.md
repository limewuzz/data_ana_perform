# 偏好数据标注工作台

本目录当前按“文档 / 后端 / 前端”三层组织，日常开发建议只关注下面这些入口：

## 目录结构

- `backend/`: FastAPI 后端，包含 API、模型调用、审核、统计、导出与测试
- `frontend/`: React + Vite 前端工作台
- `.trae/documents/`: 当前对话过程中补充的前端 PRD 与技术架构文档
- `偏好数据标注工作台_PRD_v1.0.md`: 原始 PRD Markdown
- `偏好数据标注工作台_PRD_v1.0.docx`: 原始 PRD Word 文档

## 常用命令

### 后端

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
export APP_JWT_SECRET='change-me'
uvicorn app.main:app --reload
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

## 测试

### 后端

```bash
cd backend
python3 -m pytest -q
```

### 前端

```bash
cd frontend
npm test
npm run check
npm run build
```

## 整理约定

- 缓存、构建产物和联调数据库不保留在根目录
- 业务数据暂时仍保留在 `backend/app.db` 与 `backend/exports/`
- 如果后续要继续“收口”，建议下一步把 PRD 文档统一收到 `docs/`，但这一步我先不动，避免影响你当前习惯和已有引用
