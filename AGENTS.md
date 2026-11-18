# 项目技能与约束

项目方案见 `docs/CONSTRUCTION.md`。技能用于辅助完成当前任务；用户指令及项目的产品、技术栈约束优先于技能的通用建议。

## 技能选择

本项目的技能位于 `.agents/skills/`，使用时读取对应 `SKILL.md`，按任务选用：

| 技能 | 用途 |
| --- | --- |
| `ui-ux-pro-max` | 页面布局、设计系统、图表、表单、响应式与可访问性 |
| `frontend-design` | 视觉品味（taste）、排版、颜色、层级与界面细节打磨 |
| `webapp-testing` | Playwright 浏览器交互、端到端流程、截图与控制台检查；支持同时启动前后端 |

安装来源及固定版本记录在 `.agents/skill-sources.json`。

## 设计适配

- 遵循当前方案：React 18 + Vite + Recharts，使用纯 CSS 与 CSS variables；后端为 FastAPI + SQLite。
- 币种仅支持人民币（CNY）和美元（USD），汇总统一折算为人民币。
- 不因技能示例添加 Tailwind、组件框架或升级 React。UI/UX 技能的 React 数据含较新 API，检索使用 `--stack react` 并注明 `React 18`，仅采用兼容建议。
- 中文财务仪表盘优先保证金额易读、信息层级和图表可读性；遵循方案中的浅色主题与财务语义色，并以文字或符号辅助表达状态。
- 自动生成的 `--design-system` 仅作候选建议；检查匹配度，不直接采用与方案不符的营销页结构、深色默认或缺少中文支持的字体。
- 将设计建议落实到已有产品页面与组件；动效和装饰应服务于操作反馈及信息理解。

UI/UX 搜索示例（从项目根目录执行，其他工作目录使用绝对路径）：

```sh
python3 .agents/skills/ui-ux-pro-max/scripts/search.py "error summary validation" --domain ux
python3 .agents/skills/ui-ux-pro-max/scripts/search.py "net worth trend" --domain chart
```

## 浏览器验证

- 应用实现后，以 `docs/CONSTRUCTION.md` 第 11 节的场景作为端到端验收依据，使用隔离测试数据。
- 功能验证与视觉检查分别进行；UI 变更检查桌面和移动端，以及相关空状态、加载态与错误态。
- `webapp-testing` 的 Python 脚本需要测试环境安装 `playwright` 及浏览器。技能安装不等于运行依赖安装；先检查项目测试环境，再按需配置，不修改全局 Python 环境。
- 只报告实际完成的测试及证据。当前安装验证不代表应用验收通过。
