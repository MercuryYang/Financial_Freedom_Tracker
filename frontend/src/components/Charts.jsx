import { useId } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Legend,
} from "recharts";
import { ChartNoAxesCombined } from "lucide-react";
import { CHART_COLORS, money } from "../constants";
import { Empty } from "./UI";
const compactMoney = (v) =>
  Math.abs(v) >= 10000
    ? `${(v / 10000).toFixed(1)}万`
    : new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 0 }).format(v);
export function TrendChart({ data = [], height = 230, mini = false }) {
  const id = useId().replace(/:/g, "");
  if (!data.length)
    return (
      <div className="chart-empty" style={{ minHeight: height }}>
        <Empty
          compact
          icon={ChartNoAxesCombined}
          title="你的财富曲线，从这里开始"
          description="添加资产后，每次变动都会留下当天的记录。"
        />
      </div>
    );
  return (
    <>
      <div
        className="chart"
        style={{ height }}
        role="img"
        aria-label={`净资产趋势，共 ${data.length} 个记录，最新 ${money(data[data.length - 1]?.total_cny)}`}
      >
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={data}
            margin={{ top: 10, right: 12, left: mini ? -35 : 0, bottom: 0 }}
            accessibilityLayer
          >
            <defs>
              <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#3b8c75" stopOpacity={0.2} />
                <stop offset="100%" stopColor="#3b8c75" stopOpacity={0.01} />
              </linearGradient>
            </defs>
            <CartesianGrid
              strokeDasharray="3 5"
              vertical={false}
              stroke="#e4ebe7"
            />
            <XAxis
              dataKey="date"
              tickFormatter={(x) => x?.slice(5)}
              tick={{ fontSize: 11, fill: "#7a8780" }}
              tickLine={false}
              axisLine={false}
              minTickGap={20}
            />
            <YAxis
              hide={mini}
              tickFormatter={compactMoney}
              tick={{ fontSize: 11, fill: "#7a8780" }}
              tickLine={false}
              axisLine={false}
              width={60}
            />
            <Tooltip
              formatter={(v) => [money(v), "净资产"]}
              labelFormatter={(x) => x}
              contentStyle={{
                borderRadius: 10,
                border: "1px solid #e1e8e3",
                fontSize: 12,
              }}
            />
            <Area
              name="净资产"
              dataKey="total_cny"
              type="monotone"
              stroke="#267765"
              strokeWidth={2.5}
              fill={`url(#${id})`}
              isAnimationActive={false}
              dot={data.length < 3 ? { r: 4 } : false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      {!mini && (
        <details className="chart-data">
          <summary>查看趋势数据</summary>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>日期</th>
                  <th className="align-right">净资产</th>
                </tr>
              </thead>
              <tbody>
                {data.map((x) => (
                  <tr key={x.date}>
                    <td>{x.date}</td>
                    <td className="align-right">{money(x.total_cny)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </>
  );
}
export function DonutChart({ data = [], labels = {}, height = 230 }) {
  const filtered = data
    .filter((x) => Number(x.amount_cny) > 0)
    .map((x) => ({ ...x, name: labels[x.category] || x.name || x.category }));
  const total = filtered.reduce((s, x) => s + Number(x.amount_cny), 0);
  if (!filtered.length)
    return (
      <div style={{ minHeight: height }} className="chart-empty">
        <Empty
          compact
          title="暂无分布数据"
          description="记录金额后，这里会显示各类别占比。"
          icon={ChartNoAxesCombined}
        />
      </div>
    );
  return (
    <div className="donut-layout">
      <div
        className="donut-chart"
        style={{ height }}
        role="img"
        aria-label={filtered
          .map((x) => `${x.name} ${money(x.amount_cny)}`)
          .join("，")}
      >
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={filtered}
              dataKey="amount_cny"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius="62%"
              outerRadius="84%"
              paddingAngle={3}
              stroke="none"
              isAnimationActive={false}
            >
              {filtered.map((x, i) => (
                <Cell
                  key={x.category || i}
                  fill={CHART_COLORS[i % CHART_COLORS.length]}
                />
              ))}
            </Pie>
            <Tooltip
              formatter={(v) => money(v)}
              contentStyle={{ borderRadius: 10, fontSize: 12 }}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="donut-center">
          <small>合计</small>
          <strong>{compactMoney(total)}</strong>
          <small>CNY</small>
        </div>
      </div>
      <div className="chart-legend">
        {filtered.map((x, i) => (
          <div className="legend-row" key={x.category || i}>
            <span>
              <i
                style={{ background: CHART_COLORS[i % CHART_COLORS.length] }}
              />
              {x.name}
            </span>
            <strong>
              {money(x.amount_cny)}
              <small>{((x.amount_cny / total) * 100).toFixed(1)}%</small>
            </strong>
          </div>
        ))}
      </div>
    </div>
  );
}
export function DailyChart({ data = [] }) {
  if (!data.some((x) => x.income_cny || x.expense_cny))
    return (
      <div className="chart-empty" style={{ minHeight: 230 }}>
        <Empty
          compact
          title="暂无每日收支"
          description="记录收支后查看这个月的变化。"
          icon={ChartNoAxesCombined}
        />
      </div>
    );
  return (
    <div
      className="chart"
      style={{ height: 230 }}
      role="img"
      aria-label="本月每日收入与支出对比"
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          accessibilityLayer
          margin={{ top: 10, right: 8, bottom: 0, left: 0 }}
        >
          <CartesianGrid strokeDasharray="3 5" vertical={false} />
          <XAxis
            dataKey="date"
            tickFormatter={(x) => x?.slice(8)}
            tick={{ fontSize: 11 }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            tickFormatter={compactMoney}
            tick={{ fontSize: 11 }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip formatter={(v) => money(v)} />
          <Legend
            iconType="circle"
            iconSize={7}
            wrapperStyle={{ fontSize: 12 }}
          />
          <Bar
            name="收入"
            dataKey="income_cny"
            fill="#328571"
            radius={[3, 3, 0, 0]}
            isAnimationActive={false}
          />
          <Bar
            name="支出"
            dataKey="expense_cny"
            fill="#d99a71"
            radius={[3, 3, 0, 0]}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
export function ProfitChart({ data = [] }) {
  if (!data.length)
    return (
      <Empty
        compact
        title="暂无持仓盈亏"
        description="添加持仓并记录交易后，查看投资表现。"
      />
    );
  return (
    <div className="profit-bars">
      {data.map((x) => {
        const max = Math.max(...data.map((x) => Math.abs(x.pnl_cny || 0)), 1);
        return (
          <div key={x.id} className="profit-row">
            <div>
              <span>{x.name}</span>
              <strong
                className={(x.pnl_cny || 0) >= 0 ? "positive" : "negative"}
              >
                {money(x.pnl_cny || 0)}
              </strong>
            </div>
            <div className="profit-track">
              <span
                className={(x.pnl_cny || 0) < 0 ? "loss" : ""}
                style={{
                  width: `${Math.max(1, (Math.abs(x.pnl_cny || 0) / max) * 100)}%`,
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
