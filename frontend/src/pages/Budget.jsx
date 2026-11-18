import { useState } from "react";
import { CircleDollarSign, Pencil, ShieldCheck, Wallet } from "lucide-react";
import { get } from "../api/client";
import { useResource } from "../state";
import { EXPENSE, currentMonth, money } from "../constants";
import {
  Button,
  Card,
  FormModal,
  IconButton,
  Metric,
  MonthPicker,
  PageTitle,
  Progress,
  ResourceState,
  useActions,
} from "../components/UI";
export default function Budget() {
  const [month, setMonth] = useState(currentMonth()),
    [editing, setEditing] = useState(null);
  const actions = useActions();
  const resource = useResource(() => get("/budgets", { month }), [month]);
  const budgets = resource.data || [];
  const total = budgets.reduce((s, x) => s + (x.budget_cny || 0), 0),
    spent = budgets.reduce((s, x) => s + (x.spent_cny || 0), 0);
  return (
    <>
      <PageTitle
        title="预算管理"
        description="为每一类花费安排空间，让支出始终心中有数。"
        action={<MonthPicker value={month} onChange={setMonth} />}
      />
      <ResourceState resource={resource}>
        <div className="metrics-grid three">
          <Metric
            label="本月已设预算"
            value={total}
            icon={ShieldCheck}
            hint={`${budgets.filter((x) => x.budget_cny !== null).length} 个分类已设置`}
          />
          <Metric label="本月总支出" value={spent} icon={CircleDollarSign} />
          <Metric
            label="预算与总支出差额"
            value={total - spent}
            tone={total - spent < 0 ? "negative" : "positive"}
            icon={Wallet}
            hint="包含尚未设置预算的分类支出"
          />
        </div>
        <div className="info-strip">
          <ShieldCheck size={18} />
          <span>预算统一使用人民币，外币支出按最新缓存汇率折算。</span>
        </div>
        <div className="budget-grid">
          {budgets.map((b) => {
            const set = b.budget_cny !== null,
              ratio =
                set && b.budget_cny > 0
                  ? b.spent_cny / b.budget_cny
                  : b.spent_cny && set
                    ? 1
                    : 0;
            return (
              <Card
                key={b.category}
                className={b.over_budget ? "over-budget" : ""}
              >
                <div className="between">
                  <div className="budget-category">
                    <span className="category-dot" />
                    <h2>{EXPENSE[b.category] || b.category}</h2>
                  </div>
                  <IconButton
                    icon={Pencil}
                    label={`设置${EXPENSE[b.category]}预算`}
                    onClick={() => setEditing(b)}
                  />
                </div>
                <div className="budget-amount">
                  <strong>{money(b.spent_cny)}</strong>
                  <span>/ {set ? money(b.budget_cny) : "未设置预算"}</span>
                </div>
                <Progress
                  value={ratio}
                  tone={b.over_budget ? "danger" : ""}
                  label={`${EXPENSE[b.category]}预算使用进度`}
                />
                <div className="between text-small">
                  <span className={b.over_budget ? "negative" : "muted"}>
                    {b.over_budget
                      ? `已超支 ${money(b.spent_cny - b.budget_cny)}`
                      : set
                        ? `剩余 ${money(Math.max(0, b.budget_cny - b.spent_cny))}`
                        : "设置预算后可查看使用进度"}
                  </span>
                  {set ? (
                    <span className="muted">
                      已用{" "}
                      {b.budget_cny > 0
                        ? Math.round((b.spent_cny / b.budget_cny) * 100)
                        : b.spent_cny
                          ? 100
                          : 0}
                      %
                    </span>
                  ) : (
                    <button
                      className="text-button"
                      onClick={() => setEditing(b)}
                    >
                      设置预算
                    </button>
                  )}
                </div>
              </Card>
            );
          })}
        </div>
      </ResourceState>
      {editing && (
        <FormModal
          title={`设置${EXPENSE[editing.category]}预算`}
          description={`${month} · 留空金额可取消该分类预算。`}
          initial={{ amount_cny: editing.budget_cny ?? "" }}
          fields={[
            {
              name: "amount_cny",
              label: "月度预算（CNY）",
              type: "number",
              min: 0,
              step: 0.01,
              wide: true,
            },
          ]}
          onClose={() => setEditing(null)}
          onSubmit={(payload) =>
            actions.save(
              "/budgets",
              { ...payload, category: editing.category, month },
              "put",
              "预算已保存",
            )
          }
        />
      )}
    </>
  );
}
