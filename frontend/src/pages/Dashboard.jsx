import { Link } from "react-router-dom";
import {
  ArrowDownLeft,
  ArrowUpRight,
  Landmark,
  Plus,
  Target,
  Wallet,
  TrendingUp,
} from "lucide-react";
import { get } from "../api/client";
import { useResource } from "../state";
import { money, EXPENSE, percent } from "../constants";
import {
  Card,
  Empty,
  Metric,
  MoreLink,
  PageTitle,
  Progress,
  ResourceState,
  TransactionTable,
} from "../components/UI";
import { TrendChart } from "../components/Charts";
export default function Dashboard() {
  const resource = useResource(() => get("/dashboard"));
  const d = resource.data || {};
  const month = d.month || {},
    net = d.net_worth || {},
    invest = d.investments || {};
  const goals = (d.goals || [])
      .filter((x) => x.status !== "abandoned")
      .slice(0, 3),
    budgets = (d.budgets || [])
      .filter((x) => x.budget_cny !== null)
      .slice(0, 4);
  return (
    <>
      <PageTitle
        title="财务总览"
        description="把当下看清楚，让未来更从容。"
        action={
          <Link className="button" to="/transactions?new=1">
            <Plus size={17} />
            记一笔
          </Link>
        }
      />
      <ResourceState resource={resource}>
        <div className="overview-top">
          <Card className="wealth-card">
            <div className="wealth-label">
              <span>
                <Landmark size={18} />
                总净资产
              </span>
              <span className="tag">人民币 · CNY</span>
            </div>
            <div className="wealth-amount">{money(net.total_cny || 0)}</div>
            <div className="wealth-caption">
              资产账户 + 投资组合市值 <MoreLink to="/assets">管理资产</MoreLink>
            </div>
            <TrendChart data={net.trend || []} height={175} mini />
          </Card>
          <div className="month-summary">
            <div className="section-label">本月收支</div>
            <Metric
              label="本月收入"
              value={month.income_cny || 0}
              icon={ArrowDownLeft}
              tone="positive"
            />
            <Metric
              label="本月支出"
              value={month.expense_cny || 0}
              icon={ArrowUpRight}
            />
            <Metric
              label="本月结余"
              value={month.net_cny || 0}
              icon={Wallet}
              tone={(month.net_cny || 0) < 0 ? "negative" : ""}
            />
          </div>
        </div>
        <div className="dashboard-middle">
          <Card
            title="存款目标"
            sub="把想要的生活，变成可见的进度"
            action={<MoreLink to="/goals" />}
          >
            {goals.length ? (
              <div className="goal-preview">
                {goals.map((g) => (
                  <div key={g.id}>
                    <div className="between">
                      <span className="item-title">{g.name}</span>
                      <strong>{percent(g.progress)}</strong>
                    </div>
                    <Progress value={g.progress} label={g.name} />
                    <div className="between muted text-small">
                      <span>已存 {money(g.contributed_cny)}</span>
                      <span>目标 {money(g.target_cny)}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <Empty
                compact
                icon={Target}
                title="给储蓄一个具体的方向"
                description="旅行、应急金，或是一个更远的目标。"
                action={
                  <Link className="button secondary small" to="/goals?new=1">
                    <Plus size={15} />
                    设定目标
                  </Link>
                }
              />
            )}
          </Card>
          <Card
            title="本月预算"
            sub="花得有数，留得有余"
            action={<MoreLink to="/budget" />}
          >
            {budgets.length ? (
              <div className="budget-preview">
                {budgets.map((b) => (
                  <div key={b.category}>
                    <div className="between">
                      <span>{EXPENSE[b.category] || b.category}</span>
                      <span className={b.over_budget ? "negative" : ""}>
                        {money(b.spent_cny)}{" "}
                        <small className="muted">/ {money(b.budget_cny)}</small>
                      </span>
                    </div>
                    <Progress
                      value={
                        b.budget_cny
                          ? b.spent_cny / b.budget_cny
                          : b.spent_cny
                            ? 1
                            : 0
                      }
                      tone={b.over_budget ? "danger" : ""}
                    />
                    {b.over_budget && (
                      <small className="negative">
                        已超支 {money(b.spent_cny - b.budget_cny)}
                      </small>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <Empty
                compact
                title="给支出留一条边界"
                description="按类别设置预算，及时了解花费进度。"
                action={
                  <Link className="button secondary small" to="/budget">
                    设置预算
                  </Link>
                }
              />
            )}
          </Card>
          <Card
            title="投资概况"
            action={<TrendingUp size={19} className="muted" />}
          >
            <div className="investment-preview">
              <p>组合总市值</p>
              <strong>{money(invest.market_value_cny || 0)}</strong>
              <div className="investment-stat">
                <span>浮动盈亏</span>
                <b
                  className={
                    (invest.unrealized_pnl_cny || 0) >= 0
                      ? "positive"
                      : "negative"
                  }
                >
                  {(invest.unrealized_pnl_cny || 0) > 0 ? "+" : ""}
                  {money(invest.unrealized_pnl_cny || 0)}
                </b>
              </div>
              <div className="investment-stat">
                <span>累计已实现</span>
                <b
                  className={
                    (invest.realized_pnl_cny || 0) >= 0
                      ? "positive"
                      : "negative"
                  }
                >
                  {money(
                    invest.realized_pnl_cny ?? invest.realized_pnl_all_cny ?? 0,
                  )}
                </b>
              </div>
              <Link className="button secondary full-width" to="/investments">
                查看投资组合
                <ArrowUpRight size={16} />
              </Link>
            </div>
          </Card>
        </div>
        <Card
          title="最近交易"
          sub="每一笔收支，都有迹可循"
          action={<MoreLink to="/transactions" />}
          className="table-card"
        >
          {d.recent_transactions?.length ? (
            <TransactionTable
              items={d.recent_transactions.slice(0, 5)}
              compact
            />
          ) : (
            <Empty
              title="从第一笔收支开始"
              description="记录今天的收入或支出，慢慢建立自己的财务全貌。"
              action={
                <Link className="button secondary" to="/transactions?new=1">
                  <Plus size={16} />
                  记录收支
                </Link>
              }
            />
          )}
        </Card>
      </ResourceState>
    </>
  );
}
