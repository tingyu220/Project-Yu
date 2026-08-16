# 发送动效科技感优化实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 放慢 Yu 发送信息后的状态切换，并加入低调、可读、支持 reduced-motion 的科技感动效。

**Architecture:** 保持现有 `useConversation` 状态机和 React 组件边界，仅调整状态停留时序与 Framer Motion/CSS 表现。业务请求、API 协议和页面结构不变；动效只服务于状态反馈和回复出现的因果关系。

**Tech Stack:** React 19、TypeScript、Framer Motion、现有 CSS token、Vite。

## Global Constraints

- 不新增前端依赖。
- 不修改后端 API 和数据结构。
- 保留 `prefers-reduced-motion` 下的低动效路径。
- 不改变 `/` 与 `/memory` 的路由和既有交互。
- 不提交或推送 Git，除非用户明确确认。

---

### Task 1: 调整发送状态节奏

**Files:**
- Modify: `apps/web/src/lib/useConversation.ts`

**Interfaces:**
- 保持 `ConversationApi` 接口不变。
- 保持 `submit(text: string): void` 不变。

- [ ] 将记忆检索阶段的停留从 `900ms` 调整到 `1200ms`，让 `remembering` 有明确的视觉停留。
- [ ] 将回复完成后的 `answering` 状态停留从 `1400ms` 调整到 `1800ms`。
- [ ] 将时间值提取为文件顶部的命名常量，避免散落魔法数字。
- [ ] reduced-motion 时保持直接完成，不额外制造等待。

### Task 2: 增强核心状态动效

**Files:**
- Modify: `apps/web/src/components/Core.tsx`
- Modify: `apps/web/src/index.css`

**Interfaces:**
- 不改变 `Core` 的 props 和 `CAPTIONS`。
- 复用现有 `.core--<state>` 状态类。

- [ ] 为核心区域增加低亮度的脉冲/扫描层，只在非 idle 的处理状态出现。
- [ ] 使用现有 CSS 变量与颜色体系，避免大面积渐变、强发光或遮挡文字。
- [ ] 通过 `opacity`、`transform` 和伪元素完成动效，避免布局抖动。
- [ ] 在 `prefers-reduced-motion: reduce` 下关闭循环动画并保留静态状态提示。

### Task 3: 放慢消息入场与布局过渡

**Files:**
- Modify: `apps/web/src/components/MessageList.tsx`
- Modify: `apps/web/src/pages/Cockpit.tsx`
- Modify: `apps/web/src/index.css`

**Interfaces:**
- 不改变消息数组结构和 `MessageListProps`。
- 保持用户消息、Yu 消息、busy 状态的现有渲染顺序。

- [ ] 将消息入场时长调整为用户消息 `0.38s`、Yu 回复 `0.55s`，加入轻微位移和淡入。
- [ ] 将 Cockpit 对话布局进入时长调整为约 `0.7s`，保持 reduced-motion 下无位移。
- [ ] 为 busy 状态增加与核心一致的扫描/呼吸提示，不影响输入框禁用逻辑。
- [ ] 验证窄屏下动画不引起横向溢出或内容遮挡。

### Task 4: 构建与浏览器验证

**Files:**
- Verify: `apps/web/src/lib/useConversation.ts`
- Verify: `apps/web/src/components/Core.tsx`
- Verify: `apps/web/src/components/MessageList.tsx`
- Verify: `apps/web/src/pages/Cockpit.tsx`
- Verify: `apps/web/src/index.css`

- [ ] 运行 `npm run typecheck`，确认 TypeScript 无错误。
- [ ] 运行 `npm run build`，确认生产构建成功。
- [ ] 在已运行的前端中发送一条消息，观察状态切换是否明显放慢、回复入场是否平滑。
- [ ] 使用浏览器读取页面 DOM 和控制台日志，确认无新的前端错误。
- [ ] 检查 `prefers-reduced-motion` 路径，确认动画关闭后仍能正常完成发送流程。

