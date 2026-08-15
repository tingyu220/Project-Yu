# Yu Web

Yu 的 Interface Layer（Life Cockpit + Memory Universe）。这不是一个独立产品，而是 Yu 的「身体」。

## 依赖

- Node.js（Vite 6 + React 19 + TypeScript）
- 运行中的 Yu API（`python -m yu.api`，默认 127.0.0.1:8787）

## 开发

```bash
npm install
npm run dev     # http://localhost:5173，/api 自动代理到 Yu API
```

## 生产构建

```bash
npm run build   # 产物输出到 apps/web/dist
```

构建后，从仓库根目录运行 `python -m yu.api` 会同时托管 API 与前端（单进程）。

## 页面

- `/` —— Life Cockpit
- `/memory` —— Memory Universe

## 隐私 / 录屏

导航栏「Private / Demo」或 URL `?demo=true` 开启 Presentation Mode，隐藏私人记忆内容。