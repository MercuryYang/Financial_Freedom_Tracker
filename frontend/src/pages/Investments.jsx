import { useEffect, useState } from "react";
import {
  Check,
  LineChart,
  Plus,
  RefreshCw,
  TrendingUp,
  Wallet,
} from "lucide-react";
import { get, errorText } from "../api/client";
import { useApp, useResource } from "../state";
import {
  INVESTMENTS,
  options,
  money,
  number,
  percent,
  dateText,
  today,
} from "../constants";
import {
  AddButton,
  Button,
  Card,
  Empty,
  FormModal,
  Metric,
  Money,
  PageTitle,
  ResourceState,
  RowActions,
  currencyField,
  noteField,
  useActions,
} from "../components/UI";
import { DonutChart, ProfitChart } from "../components/Charts";
function PriceEditor({ holding }) {
  const [price, setPrice] = useState(holding.current_price),
    [busy, setBusy] = useState(false);
  const { notify } = useApp();
  const actions = useActions();
  useEffect(() => setPrice(holding.current_price), [holding.current_price]);
  return (
    <form
      className="inline-price"
      onSubmit={async (e) => {
        e.preventDefault();
        setBusy(true);
        try {
          await actions.save(
            `/investments/${holding.id}`,
            { current_price: Number(price) },
            "put",
            "现价已更新",
          );
        } catch (e) {
          notify(errorText(e), "error");
        } finally {
          setBusy(false);
        }
      }}
    >
      <input
        aria-label={`${holding.name}现价`}
        type="number"
        min="0"
        step="any"
        required
        value={price}
        onChange={(e) => setPrice(e.target.value)}
      />
      <button
        className="icon-button"
        aria-label={`保存${holding.name}现价`}
        title="保存现价"
        disabled={busy || Number(price) === Number(holding.current_price)}
      >
        <Check size={15} />
      </button>
    </form>
  );
}
export default function Investments() {
  const [editing, setEditing] = useState(null),
    [trade, setTrade] = useState(null),
    [tradeFilter, setTradeFilter] = useState("");
  const actions = useActions();
  const resource = useResource(
    () =>
      Promise.all([
        get("/investments/holdings"),
        get("/investments/summary"),
        get("/investments/trades", { holding_id: tradeFilter || undefined }),
      ]).then(([holdings, summary, trades]) => ({ holdings, summary, trades })),
    [tradeFilter],
  );
  const { holdings = [], summary = {}, trades = [] } = resource.data || {};
  useEffect(() => {
    if (
      resource.data &&
      tradeFilter &&
      !holdings.some((h) => String(h.id) === String(tradeFilter))
    )
      setTradeFilter("");
  }, [resource.data, tradeFilter]);
  return (
    <>
      <PageTitle
        title="投资 Tracker"
        description="关注长期积累，也看清每一笔投资的表现。"
        action={
          <>
            <Button variant="secondary" onClick={() => setEditing({})}>
              <Plus size={17} />
              添加标的
            </Button>
            <AddButton
              disabled={!holdings.length}
              onClick={() =>
                setTrade({ holding_id: holdings[0]?.id, action: "buy" })
              }
            >
              记录买卖
            </AddButton>
          </>
        }
      />
      <ResourceState resource={resource}>
        <div className="metrics-grid four">
          <Metric
            label="组合总市值"
            value={summary.market_value_cny || 0}
            icon={Wallet}
          />
          <Metric
            label="持仓总成本"
            value={summary.total_cost_cny ?? summary.cost_cny ?? 0}
            icon={LineChart}
          />
          <Metric
            label="浮动盈亏"
            value={summary.unrealized_pnl_cny || 0}
            tone={summary.unrealized_pnl_cny < 0 ? "negative" : "positive"}
            icon={TrendingUp}
          />
          <Metric
            label="累计已实现盈亏"
            value={
              summary.realized_pnl_all_cny ?? summary.realized_pnl_cny ?? 0
            }
            tone={
              (summary.realized_pnl_all_cny ?? summary.realized_pnl_cny ?? 0) <
              0
                ? "negative"
                : "positive"
            }
            icon={Check}
          />
        </div>
        <div className="info-strip">
          <RefreshCw size={16} />
          <span>
            现价由你手动维护。修改现价后，组合估值与总净资产会同步更新。
          </span>
        </div>
        <Card
          title="我的持仓"
          sub={`${holdings.length} 个投资标的`}
          className="table-card"
        >
          {holdings.length ? (
            <div className="table-scroll">
              <table className="holdings-table">
                <thead>
                  <tr>
                    <th>投资标的</th>
                    <th className="align-right">持有数量</th>
                    <th className="align-right">平均成本</th>
                    <th>现价 / 更新日期</th>
                    <th className="align-right">市值</th>
                    <th className="align-right">浮动盈亏</th>
                    <th className="align-right">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {holdings.map((h) => (
                    <tr key={h.id}>
                      <td>
                        <strong>{h.name}</strong>
                        <small className="cell-sub">
                          {h.symbol}{" "}
                          <span className="tag">
                            {INVESTMENTS[h.asset_type] || h.asset_type}
                          </span>
                        </small>
                      </td>
                      <td className="align-right tabular">
                        {number(h.quantity)}
                      </td>
                      <td className="align-right">
                        {money(h.avg_cost, h.currency)}
                      </td>
                      <td>
                        <PriceEditor holding={h} />
                        <small className="cell-sub">
                          {h.currency} · {dateText(h.updated_at)}
                        </small>
                      </td>
                      <td className="align-right">
                        <Money
                          value={h.market_value}
                          currency={h.currency}
                          cny={h.market_value_cny}
                        />
                      </td>
                      <td
                        className={`align-right ${(h.pnl || 0) >= 0 ? "positive" : "negative"}`}
                      >
                        <Money
                          value={h.pnl}
                          currency={h.currency}
                          cny={h.pnl_cny}
                        />
                        <small className="cell-sub">
                          {h.pnl > 0 ? "+" : ""}
                          {percent(h.pnl_rate)}
                        </small>
                      </td>
                      <td>
                        <div className="holding-actions">
                          <button
                            className="text-button"
                            onClick={() =>
                              setTrade({ holding_id: h.id, action: "buy" })
                            }
                          >
                            买卖
                          </button>
                          <RowActions
                            onEdit={() => setEditing(h)}
                            onDelete={() =>
                              actions.remove(
                                `/investments/${h.id}`,
                                h.name,
                                "请先卖出全部持仓。删除标的后交易历史会保留。",
                              )
                            }
                            label={h.name}
                          />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <Empty
              icon={TrendingUp}
              title="建立你的投资组合"
              description="添加一个标的，再记录买入交易。成本、盈亏与资产占比会自动计算。"
              action={
                <AddButton variant="secondary" onClick={() => setEditing({})}>
                  添加投资标的
                </AddButton>
              }
            />
          )}
        </Card>
        <div className="two-columns charts-row">
          <Card title="组合分布">
            <DonutChart
              data={holdings
                .filter((x) => x.market_value_cny > 0)
                .map((x) => ({
                  category: String(x.id),
                  name: x.name,
                  amount_cny: x.market_value_cny,
                }))}
            />
          </Card>
          <Card title="持仓盈亏" sub="按人民币折算，比较每一份投资">
            <ProfitChart data={holdings} />
          </Card>
        </div>
        <Card
          title="交易历史"
          className="table-card"
          action={
            <label>
              <span className="sr-only">筛选投资标的</span>
              <select
                value={tradeFilter}
                onChange={(e) => setTradeFilter(e.target.value)}
              >
                <option value="">全部标的</option>
                {holdings.map((h) => (
                  <option key={h.id} value={h.id}>
                    {h.name}
                  </option>
                ))}
              </select>
            </label>
          }
        >
          {trades.length ? (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>日期</th>
                    <th>标的</th>
                    <th>方向</th>
                    <th className="align-right">数量</th>
                    <th className="align-right">成交价</th>
                    <th className="align-right">费用</th>
                    <th className="align-right">已实现盈亏</th>
                  </tr>
                </thead>
                <tbody>
                  {trades.map((t) => {
                    const h = holdings.find((h) => h.id === t.holding_id) || {};
                    const currency = t.currency || h.currency || "CNY";
                    return (
                      <tr key={t.id}>
                        <td>{dateText(t.trade_date)}</td>
                        <td>
                          <strong>
                            {t.name || h.name || t.symbol || "已删除标的"}
                          </strong>
                          <small className="cell-sub">
                            {t.note || t.symbol || h.symbol}
                          </small>
                        </td>
                        <td>
                          <span
                            className={`tag ${t.action === "buy" ? "green" : "orange"}`}
                          >
                            {t.action === "buy" ? "买入" : "卖出"}
                          </span>
                        </td>
                        <td className="align-right tabular">
                          {number(t.quantity)}
                        </td>
                        <td className="align-right">
                          {money(t.price, currency)}
                        </td>
                        <td className="align-right">
                          {money(t.fee, currency)}
                        </td>
                        <td
                          className={`align-right ${t.realized_pnl < 0 ? "negative" : "positive"}`}
                        >
                          {t.action === "sell"
                            ? money(t.realized_pnl, currency)
                            : "—"}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <Empty
              compact
              title="暂无交易记录"
              description="记录买入和卖出后，在这里回顾每一笔交易。"
            />
          )}
        </Card>
      </ResourceState>
      {editing && (
        <FormModal
          title={editing.id ? "编辑投资标的" : "添加投资标的"}
          description={
            editing.id
              ? "持有数量与成本通过买卖交易更新。"
              : "添加后记录买入交易，系统会自动计算平均成本。"
          }
          initial={
            editing.id
              ? editing
              : {
                  name: "",
                  symbol: "",
                  asset_type: "stock",
                  currency: "CNY",
                  current_price: "",
                }
          }
          fields={
            editing.id
              ? [
                  { name: "name", label: "名称", required: true },
                  {
                    name: "current_price",
                    label: "当前价格",
                    type: "number",
                    min: 0,
                    step: "any",
                    required: true,
                  },
                ]
              : [
                  {
                    name: "name",
                    label: "名称",
                    required: true,
                    placeholder: "例如：沪深 300 ETF",
                  },
                  {
                    name: "symbol",
                    label: "代码",
                    required: true,
                    placeholder: "例如：510300",
                  },
                  {
                    name: "asset_type",
                    label: "投资类型",
                    type: "select",
                    required: true,
                    options: options(INVESTMENTS),
                  },
                  currencyField,
                  {
                    name: "current_price",
                    label: "当前价格",
                    type: "number",
                    min: 0,
                    step: "any",
                    required: true,
                    wide: true,
                  },
                ]
          }
          onClose={() => setEditing(null)}
          onSubmit={(payload) =>
            actions.save(
              editing.id
                ? `/investments/${editing.id}`
                : "/investments/holdings",
              payload,
              editing.id ? "put" : "post",
              "投资标的已保存",
            )
          }
        />
      )}
      {trade && (
        <FormModal
          title="记录投资买卖"
          initial={{
            ...trade,
            quantity: "",
            price: "",
            fee: 0,
            trade_date: today(),
            note: "",
          }}
          fields={(v) => [
            {
              name: "holding_id",
              label: "投资标的",
              type: "select",
              required: true,
              wide: true,
              options: holdings.map((h) => ({
                value: h.id,
                label: `${h.name} (${h.symbol}) · ${h.currency}`,
              })),
            },
            {
              name: "action",
              label: "交易方向",
              type: "select",
              required: true,
              options: [
                { value: "buy", label: "买入" },
                { value: "sell", label: "卖出" },
              ],
            },
            {
              name: "quantity",
              label: "成交数量",
              type: "number",
              min: 0.000001,
              step: "any",
              required: true,
              max:
                v.action === "sell"
                  ? holdings.find((h) => String(h.id) === String(v.holding_id))
                      ?.quantity
                  : undefined,
            },
            {
              name: "price",
              label: "成交价格（标的原币）",
              type: "number",
              min: 0.000001,
              step: "any",
              required: true,
            },
            {
              name: "fee",
              label: "交易费用（标的原币）",
              type: "number",
              min: 0,
              step: 0.01,
              required: true,
            },
            {
              name: "trade_date",
              label: "交易日期",
              type: "date",
              required: true,
            },
            noteField,
          ]}
          onClose={() => setTrade(null)}
          onSubmit={(payload) =>
            actions.save(
              "/investments/trades",
              { ...payload, holding_id: Number(payload.holding_id) },
              "post",
              "交易已记录，持仓已更新",
            )
          }
        />
      )}
    </>
  );
}
