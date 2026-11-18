# 财富自由之路

个人财务工作台：记录收支、控制预算、追踪存款目标、查看资产与净值、管理心愿清单和投资持仓。

采用 React 18 + Vite + Recharts + 纯 CSS，FastAPI + SQLAlchemy + SQLite。仅支持人民币（CNY）和美元（USD），汇总统一折算为人民币。数据保存在本机，应用首次打开为空数据。

## Docker 启动

需要 Docker 与 Docker Compose：

```sh
docker compose up -d --build
```

打开 **http://localhost:8080**。默认只监听本机 `127.0.0.1`。数据库保存在 Compose 的 `fft_data` 命名卷，容器重建或重启后数据保留。

```sh
docker compose ps
docker compose logs --tail=100
docker compose down
```

`down` 保留数据卷；`down -v` 会删除数据。需要换端口时复制 `.env.example` 为 `.env` 并修改 `PORT`。无登录系统，局域网访问可设置 `BIND_ADDRESS=0.0.0.0`；公网访问应先自行配置访问控制。

## 本地开发

建议 Python 3.12、Node.js 22 或更高版本。

后端：

```sh
python3.12 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements-dev.txt
cd backend
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

也可以使用 `uv venv --python 3.12 backend/.venv` 创建虚拟环境。`DB_PATH` 可设置 SQLite 文件位置；Docker 中为 `/data/fft.db`。

另开终端启动前端：

```sh
cd frontend
npm ci
npm run dev -- --host 127.0.0.1
```

访问终端打印的地址（默认 http://127.0.0.1:5173）。Vite 将 `/api` 代理到 `http://127.0.0.1:8000`，可用 `VITE_API_PROXY_TARGET` 改变代理目标。API 文档位于 http://127.0.0.1:8000/docs。

## 功能与数据约定

- **总览**：净资产、本月收支与结余、预算使用、目标进度、投资盈亏和最近交易。
- **收支**：原币金额与 CNY 折算、月份/类型/分类筛选、分类与每日图表、每月周期规则。
- **预算**：按月份与支出分类设置人民币预算，超额时显示超支金额。
- **存款目标**：建立多个目标、记录多币种存入、查看贡献历史与剩余金额。
- **资产**：维护现金、活期、定期、房产等账户；投资市值独立汇总，避免双重计算。
- **心愿**：维护优先级和价格，购买后自动记入购物支出。
- **投资**：记录买卖与手续费，维护现价，查看浮动盈亏、已实现盈亏和交易历史。

收支记录、存款目标与资产账户分别维护；记账或记录目标存入不会自动改动账户余额。投资现价由用户更新，页面显示更新时间。买入费用计入平均成本，卖出费用扣减已实现收益；清仓后平均成本归零。

所有原币金额原样保存，报表使用当前缓存汇率折算成人民币；历史净值快照保留当时汇率计算结果，同一天更新一个点。业务日期按 `Asia/Shanghai` 处理。

汇率来自 [Frankfurter v1](https://frankfurter.dev/zh-tw/v1/)，每日缓存。网络失败时使用已有缓存并提示时效；没有某币种缓存时返回明确错误，不使用编造汇率。空项目与纯人民币数据可离线使用。可用 `RATES_URL` 指定兼容的汇率端点。

## 验证

后端单元与验收测试使用临时数据库和固定汇率，不修改日常数据：

```sh
cd backend
.venv/bin/python -m pytest -q
```

前端生产构建：

```sh
cd frontend
npm run build
```

浏览器测试依赖单独安装到项目虚拟环境：

```sh
python3.12 -m venv .venv-e2e
.venv-e2e/bin/python -m pip install -r requirements-e2e.txt
.venv-e2e/bin/python -m playwright install chromium
.venv-e2e/bin/python scripts/e2e.py
```

浏览器脚本自动启动独立前后端、使用固定汇率和临时数据库，结束后关闭进程；运行前须完成上述后端与前端依赖安装。截图与结果保存在 `output/e2e/`（不入 Git）。

构建镜像后，验证 Nginx、健康检查及数据库重启持久化：

```sh
docker compose build
python3 scripts/docker_smoke.py
# 已安装 Playwright 时，同时验收构建后页面的完整浏览器流程：
.venv-e2e/bin/python scripts/docker_smoke.py --browser
```

容器验收使用独立 Compose 项目和临时数据卷，结束后只移除该测试项目。`--browser` 仅为独立测试后端注入固定日期/汇率，前端直接使用生产构建镜像。实际验收结果与依赖审计限制见 `docs/ACCEPTANCE.md`。

## 数据备份

通过 SQLite backup API 创建一致性备份（包括 WAL 中已提交的数据）：

```sh
docker compose exec backend python -c 'import sqlite3; src=sqlite3.connect("/data/fft.db"); dst=sqlite3.connect("/tmp/fft-backup.db"); src.backup(dst); dst.close(); src.close()'
docker compose cp backend:/tmp/fft-backup.db ./fft-backup.db
```

备份文件包含个人财务数据，应自行妥善保存；数据库与运行日志已从 Git 中排除。

## 项目文档

- [施工方案](docs/CONSTRUCTION.md)
- [验收记录](docs/ACCEPTANCE.md)
- [项目技能与约束](AGENTS.md)
- [技能来源版本](.agents/skill-sources.json)
