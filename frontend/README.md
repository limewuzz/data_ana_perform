# Frontend Workbench

React 18 + TypeScript + Vite 前端工作台，用于连接偏好数据标注后端，覆盖登录、任务管理、标注、审核、质量看板、导出和系统设置。

## 页面

- `/login`: 登录 / 注册
- `/`: 工作台首页
- `/tasks`: 任务管理与批量导入
- `/annotate`: 标注工作区
- `/review`: 审核工作台
- `/dashboard`: 质量看板
- `/exports`: 导出中心
- `/settings/models`: 模型配置
- `/settings/users`: 用户设置

## 开发启动

```bash
cd frontend
npm install
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

如果后端跑在其他端口，改掉 `VITE_API_BASE_URL` 即可。

## 脚本

```bash
npm test
npm run check
npm run build
```

## 依赖说明

- `@tanstack/react-query`: 接口请求与缓存
- `zustand`: 会话状态持久化
- `recharts`: 看板图表
- `@dnd-kit/*`: 标注排序交互
- `sonner`: 轻提示

## 联调提示

- 后端默认地址在 `src/lib/api.ts`，未传入 `VITE_API_BASE_URL` 时回退到 `http://127.0.0.1:8000`
- 开发时如果 Vite 端口不是 `4173`，需要确认后端 CORS 已允许当前端口
