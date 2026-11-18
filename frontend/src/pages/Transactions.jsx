import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  ArrowDownLeft,
  ArrowUpRight,
  CalendarClock,
  Pause,
  Play,
  Plus,
  Wallet,
} from "lucide-react";
import dayjs from "dayjs";
import { get, errorText } from "../api/client";
import { useApp, useResource } from "../state";
import {
  INCOME,
  EXPENSE,
  options,
  currentMonth,
  today,
  categoryName,
  dateText,
} from "../constants";
import {
  AddButton,
  Button,
  Card,
  Empty,
  FormModal,
  Metric,
  Money,
  MonthPicker,
  PageTitle,
  ResourceState,
  RowActions,
  TransactionTable,
  amountField,
  currencyField,
  noteField,
  useActions,
} from "../components/UI";
import { DailyChart, DonutChart } from "../components/Charts";
const transactionFields =
  (recurring = false) =>
  (values) => [
    {
      name: "type",
      label: "收支类型",
      type: "select",
      options: [
        { value: "expense", label: "支出" },
        { value: "income", label: "收入" },
      ],
      required: true,
      onChange: (value) => ({
        category: value === "income" ? "salary" : "food",
      }),
    },
    amountField(),
    currencyField,
    {
      name: "category",
      label: "分类",
      type: "select",
      required: true,
      options: options(values.type === "income" ? INCOME : EXPENSE),
    },
    recurring
      ? {
          name: "day_of_month",
          label: "每月几号",
          type: "number",
          min: 1,
          max: 31,
          step: 1,
          required: true,
          hint: "遇到较短的月份，将在该月最后一天记录。",
        }
      : { name: "tx_date", label: "日期", type: "date", required: true },
    ...(recurring
      ? [{ name: "active", label: "启用周期规则", type: "checkbox" }]
      : []),
    noteField,
  ];
export default function Transactions() {
  const [params] = useSearchParams();
  const [month, setMonth] = useState(currentMonth()),
    [type, setType] = useState(""),
    [category, setCategory] = useState(""),
    [source, setSource] = useState(""),
    [tab, setTab] = useState("records"),
    [editing, setEditing] = useState(
      params.get("new") ? { kind: "transaction" } : null,
    );
  const actions = useActions();
  const { notify } = useApp();
  const resource = useResource(
    () =>
      Promise.all([
        get("/transactions", {
          month,
          type: type || undefined,
          category: category || undefined,
          source: source || undefined,
          limit: 500,
        }),
        get("/transactions/summary", { month }),
        get("/recurring"),
      ]).then(([records, summary, rules]) => ({ records, summary, rules })),
    [month, type, category, source],
  );
  const { records = [], summary = {}, rules = [] } = resource.data || {};
  const openRule = () => setEditing({ kind: "rule" });
  const isRule = editing?.kind === "rule";
  const initial = editing?.item || {
    type: "expense",
    amount: "",
    currency: "CNY",
    category: "food",
    tx_date: today(),
    day_of_month: dayjs().date(),
    active: true,
    note: "",
  };
  return (
    <>
      <PageTitle
        title="收支记录"
        description="记下生活的每一笔，了解钱从哪里来、到哪里去。"
        action={
          <>
            <MonthPicker value={month} onChange={setMonth} />
            <AddButton onClick={() => setEditing({ kind: "transaction" })}>
              记一笔
            </AddButton>
          </>
        }
      />
      <ResourceState resource={resource}>
        <div className="metrics-grid three">
          <Metric
            label="本月收入"
            value={summary.income_cny || 0}
            icon={ArrowDownLeft}
            tone="positive"
          />
          <Metric
            label="本月支出"
            value={summary.expense_cny || 0}
            icon={ArrowUpRight}
          />
          <Metric
            label="本月结余"
            value={summary.net_cny || 0}
            icon={Wallet}
            tone={summary.net_cny < 0 ? "negative" : ""}
          />
        </div>
        <div className="two-columns charts-row">
          <Card title="支出去向">
            <DonutChart data={summary.by_category || []} labels={EXPENSE} />
          </Card>
          <Card title="每日收支">
            <DailyChart data={summary.by_day || []} />
          </Card>
        </div>
        <Card className="table-card">
          <div className="table-toolbar">
            <div className="tabs" aria-label="收支视图">
              <button
                className={tab === "records" ? "active" : ""}
                onClick={() => setTab("records")}
              >
                收支明细
              </button>
              <button
                className={tab === "rules" ? "active" : ""}
                onClick={() => setTab("rules")}
              >
                <CalendarClock size={16} />
                周期规则 <span>{rules.length}</span>
              </button>
            </div>
            {tab === "rules" ? (
              <AddButton variant="secondary small" onClick={openRule}>
                新增规则
              </AddButton>
            ) : (
              <span className="muted text-small">{records.length} 笔记录</span>
            )}
          </div>
          {tab === "records" ? (
            <>
              <div className="filters">
                <label>
                  <span className="sr-only">筛选收支类型</span>
                  <select
                    value={type}
                    onChange={(e) => {
                      setType(e.target.value);
                      setCategory("");
                    }}
                  >
                    <option value="">全部收支</option>
                    <option value="income">收入</option>
                    <option value="expense">支出</option>
                  </select>
                </label>
                <label>
                  <span className="sr-only">筛选分类</span>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                  >
                    <option value="">全部分类</option>
                    {options(
                      type === "income"
                        ? INCOME
                        : type === "expense"
                          ? EXPENSE
                          : { ...INCOME, ...EXPENSE },
                    ).map((x) => (
                      <option key={x.value} value={x.value}>
                        {x.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span className="sr-only">筛选来源</span>
                  <select
                    value={source}
                    onChange={(e) => setSource(e.target.value)}
                  >
                    <option value="">全部来源</option>
                    <option value="manual">手动记录</option>
                    <option value="recurring">周期记录</option>
                    <option value="dream">心愿购买</option>
                  </select>
                </label>
                {(type || category || source) && (
                  <button
                    className="text-button"
                    onClick={() => {
                      setType("");
                      setCategory("");
                      setSource("");
                    }}
                  >
                    清除筛选
                  </button>
                )}
              </div>
              {records.length ? (
                <TransactionTable
                  items={records}
                  onEdit={(item) => setEditing({ kind: "transaction", item })}
                  onDelete={(item) =>
                    actions.remove(`/transactions/${item.id}`, "这笔收支")
                  }
                />
              ) : (
                <Empty
                  title="这个月还没有符合条件的记录"
                  description="添加一笔收支，或者切换月份和筛选条件。"
                  action={
                    <AddButton
                      variant="secondary"
                      onClick={() => setEditing({ kind: "transaction" })}
                    >
                      记录收支
                    </AddButton>
                  }
                />
              )}
            </>
          ) : rules.length ? (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>周期规则</th>
                    <th>发生时间</th>
                    <th>状态</th>
                    <th className="align-right">金额</th>
                    <th className="align-right">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {rules.map((r) => (
                    <tr key={r.id}>
                      <td>
                        <strong>{categoryName(r)}</strong>
                        <small className="cell-sub">
                          {r.note || "按月自动记录"}
                        </small>
                      </td>
                      <td>
                        每月 {r.day_of_month} 日
                        <small className="cell-sub">
                          最近生成：{dateText(r.last_generated)}
                        </small>
                      </td>
                      <td>
                        <button
                          className={`status-switch ${r.active ? "enabled" : ""}`}
                          onClick={() =>
                            actions
                              .save(
                                `/recurring/${r.id}`,
                                { active: !r.active },
                                "put",
                                r.active ? "已暂停规则" : "已启用规则",
                              )
                              .catch((e) => notify(errorText(e), "error"))
                          }
                        >
                          {r.active ? <Pause size={12} /> : <Play size={12} />}
                          {r.active ? "启用中" : "已暂停"}
                        </button>
                      </td>
                      <td className="align-right">
                        <Money
                          value={r.amount}
                          currency={r.currency}
                          sign={r.type === "income" ? "+" : "−"}
                        />
                      </td>
                      <td>
                        <RowActions
                          onEdit={() => setEditing({ kind: "rule", item: r })}
                          onDelete={() =>
                            actions.remove(
                              `/recurring/${r.id}`,
                              "这条周期规则",
                              "删除规则后，已生成的历史收支会保留。",
                            )
                          }
                          label="周期规则"
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <Empty
              icon={CalendarClock}
              title="让固定收支自动记账"
              description="设置工资、房租等月度规则，打开应用时自动补记。"
              action={
                <AddButton variant="secondary" onClick={openRule}>
                  新增周期规则
                </AddButton>
              }
            />
          )}
        </Card>
      </ResourceState>
      {editing && (
        <FormModal
          title={`${editing.item ? "编辑" : "新增"}${isRule ? "周期规则" : "收支记录"}`}
          description={
            isRule
              ? "从本月起补齐到期记录；暂停后再次启用时，会补记暂停期间的到期记录。"
              : undefined
          }
          initial={initial}
          fields={transactionFields(isRule)}
          onClose={() => setEditing(null)}
          onSubmit={(payload) =>
            actions.save(
              `/${isRule ? "recurring" : "transactions"}${editing.item ? `/${editing.item.id}` : ""}`,
              payload,
              editing.item ? "put" : "post",
              isRule ? "周期规则已保存" : "收支已保存",
            )
          }
        />
      )}
    </>
  );
}
