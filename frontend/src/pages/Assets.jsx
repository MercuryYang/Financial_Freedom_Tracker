import { useState } from "react";
import { Building2, Landmark, Wallet } from "lucide-react";
import { get } from "../api/client";
import { useResource } from "../state";
import { ASSETS, options, money, dateText } from "../constants";
import {
  AddButton,
  Card,
  Empty,
  FormModal,
  Metric,
  Money,
  PageTitle,
  ResourceState,
  RowActions,
  currencyField,
  useActions,
} from "../components/UI";
import { DonutChart, TrendChart } from "../components/Charts";
export default function Assets() {
  const [editing, setEditing] = useState(null);
  const actions = useActions();
  const resource = useResource(() =>
    Promise.all([get("/assets"), get("/networth/history", { limit: 90 })]).then(
      ([assets, history]) => ({ assets, history }),
    ),
  );
  const { assets = {}, history = [] } = resource.data || {};
  const accounts = assets.accounts || [];
  return (
    <>
      <PageTitle
        title="资产分布"
        description="看清每一份积累，记录财富成长的轨迹。"
        action={<AddButton onClick={() => setEditing({})}>添加账户</AddButton>}
      />
      <ResourceState resource={resource}>
        <div className="metrics-grid three">
          <Metric
            label="总净资产"
            value={assets.total_cny || 0}
            icon={Landmark}
          />
          <Metric
            label="资产账户余额"
            value={
              (assets.total_cny || 0) - (assets.investment_portfolio_cny || 0)
            }
            icon={Wallet}
            hint={`${accounts.length} 个资产账户`}
          />
          <Metric
            label="投资组合市值"
            value={assets.investment_portfolio_cny || 0}
            icon={Building2}
            hint="自动纳入净资产，避免重复计算"
          />
        </div>
        <div className="two-columns charts-row">
          <Card title="资产组成" sub="所有金额统一折算为人民币">
            <DonutChart data={assets.by_category || []} labels={ASSETS} />
          </Card>
          <Card title="净资产趋势" sub="最近 90 个快照 · 同一天的变更合并记录">
            <TrendChart data={history} />
          </Card>
        </div>
        <div className="section-heading">
          <h2>
            我的账户 <span>{accounts.length}</span>
          </h2>
          <span className="muted text-small">更新余额，留下今天的资产快照</span>
        </div>
        {accounts.length ? (
          <div className="account-grid">
            {accounts.map((a) => (
              <Card key={a.id} className="account-card">
                <div className="between">
                  <span className="account-symbol">
                    <Wallet size={20} />
                  </span>
                  <span className="tag">{a.currency}</span>
                </div>
                <h3>{a.name}</h3>
                <span className="muted text-small">
                  {ASSETS[a.category] || a.category}
                </span>
                <div className="account-balance">
                  <Money
                    value={a.balance}
                    currency={a.currency}
                    cny={a.balance_cny}
                  />
                </div>
                <div className="account-footer">
                  <span className="muted text-small">
                    更新于 {dateText(a.updated_at)}
                  </span>
                  <RowActions
                    onEdit={() => setEditing(a)}
                    onDelete={() => actions.remove(`/assets/${a.id}`, a.name)}
                    label={a.name}
                  />
                </div>
              </Card>
            ))}
          </div>
        ) : (
          <Card>
            <Empty
              icon={Landmark}
              title="给你的资产建立一份清单"
              description="从现金、银行卡或定期存款开始，逐步拼出完整的资产版图。"
              action={
                <AddButton variant="secondary" onClick={() => setEditing({})}>
                  添加第一个账户
                </AddButton>
              }
            />
          </Card>
        )}
      </ResourceState>
      {editing && (
        <FormModal
          title={editing.id ? "编辑资产账户" : "添加资产账户"}
          description="投资持仓请在「投资 Tracker」记录，系统会自动合并。"
          initial={
            editing.id
              ? editing
              : { name: "", category: "checking", currency: "CNY", balance: "" }
          }
          fields={[
            {
              name: "name",
              label: "账户名称",
              required: true,
              wide: true,
              placeholder: "例如：招商银行储蓄卡",
            },
            {
              name: "category",
              label: "资产类别",
              type: "select",
              required: true,
              options: options(
                Object.fromEntries(
                  Object.entries(ASSETS).filter(
                    ([key]) => key !== "investment_portfolio",
                  ),
                ),
              ),
            },
            currencyField,
            {
              name: "balance",
              label: "账户余额",
              type: "number",
              min: 0,
              step: 0.01,
              required: true,
              wide: true,
            },
          ]}
          onClose={() => setEditing(null)}
          onSubmit={(payload) =>
            actions.save(
              `/assets${editing.id ? `/${editing.id}` : ""}`,
              payload,
              editing.id ? "put" : "post",
              "资产账户已保存",
            )
          }
        />
      )}
    </>
  );
}
