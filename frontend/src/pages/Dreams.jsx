import { useState } from "react";
import {
  Check,
  ExternalLink,
  Heart,
  ShoppingBag,
  Sparkles,
} from "lucide-react";
import { get } from "../api/client";
import { useApp, useResource } from "../state";
import { PRIORITY, options, money, dateText } from "../constants";
import {
  AddButton,
  Button,
  Card,
  Empty,
  FormModal,
  Money,
  PageTitle,
  ResourceState,
  RowActions,
  amountField,
  currencyField,
  noteField,
  useActions,
} from "../components/UI";
export default function Dreams() {
  const [editing, setEditing] = useState(null),
    [purchase, setPurchase] = useState(null),
    [status, setStatus] = useState("pending");
  const actions = useActions();
  const { rates } = useApp();
  const resource = useResource(() =>
    Promise.all([get("/dreams"), get("/transactions/summary")]).then(
      ([items, summary]) => ({ items, summary }),
    ),
  );
  const { items = [], summary = {} } = resource.data || {};
  const priorities = { high: 0, medium: 1, low: 2 };
  const filtered = items
    .filter((x) => x.status === status)
    .sort((a, b) => priorities[a.priority] - priorities[b.priority]);
  return (
    <>
      <PageTitle
        title="Dream 清单"
        description="把心动放进计划，让每一次拥有都更有底气。"
        action={<AddButton onClick={() => setEditing({})}>添加心愿</AddButton>}
      />
      <div className="dream-intro">
        <span className="dream-intro-icon">
          <Sparkles size={25} />
        </span>
        <div>
          <h2>心愿可以很大，实现可以慢慢来。</h2>
          <p>
            本月结余{" "}
            <strong className={summary.net_cny < 0 ? "negative" : "positive"}>
              {money(summary.net_cny || 0)}
            </strong>
            ，留给未来，也留一点给喜欢的生活。
          </p>
        </div>
      </div>
      <div className="tabs standalone">
        <button
          className={status === "pending" ? "active" : ""}
          onClick={() => setStatus("pending")}
        >
          待实现{" "}
          <span>{items.filter((x) => x.status === "pending").length}</span>
        </button>
        <button
          className={status === "purchased" ? "active" : ""}
          onClick={() => setStatus("purchased")}
        >
          已拥有{" "}
          <span>{items.filter((x) => x.status === "purchased").length}</span>
        </button>
      </div>
      <ResourceState resource={resource}>
        {filtered.length ? (
          <div className="dream-grid">
            {filtered.map((item) => {
              const rate =
                item.currency === "CNY"
                  ? 1
                  : rates?.currencies?.find((x) => x.code === item.currency)
                      ?.rate;
              const cny = item.price_cny ?? (rate ? item.price * rate : null);
              return (
                <Card
                  key={item.id}
                  className={`dream-card ${status === "purchased" ? "purchased" : ""}`}
                >
                  <div className="between">
                    <span className="dream-item-icon">
                      {status === "purchased" ? (
                        <Check size={23} />
                      ) : (
                        <ShoppingBag size={23} />
                      )}
                    </span>
                    <span className={`tag priority-${item.priority}`}>
                      {status === "purchased"
                        ? "已拥有"
                        : PRIORITY[item.priority]}
                    </span>
                  </div>
                  <h2>{item.name}</h2>
                  <p className="dream-note">
                    {item.note || "给未来的一份期待"}
                  </p>
                  <Money
                    value={item.price}
                    currency={item.currency}
                    cny={cny}
                  />
                  <div className="dream-affordability">
                    {status === "purchased"
                      ? `实现于 ${dateText(item.purchased_at)}`
                      : summary.net_cny > 0 && cny !== null
                        ? `约占本月结余的 ${((cny / summary.net_cny) * 100).toFixed(1)}%`
                        : "先存一点，让心愿更近一点"}
                  </div>
                  <div className="dream-actions">
                    {status === "pending" && (
                      <Button
                        variant="secondary small"
                        onClick={() => setPurchase(item)}
                      >
                        <Check size={15} />
                        已购买
                      </Button>
                    )}
                    {/^https?:\/\//i.test(item.url || "") && (
                      <a
                        className="icon-button"
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        aria-label={`打开${item.name}链接`}
                        title="查看商品链接"
                      >
                        <ExternalLink size={17} />
                      </a>
                    )}
                    <RowActions
                      onEdit={() => setEditing(item)}
                      onDelete={() =>
                        actions.remove(
                          `/dreams/${item.id}`,
                          item.name,
                          "删除心愿不会删除已经生成的收支记录。",
                        )
                      }
                      label={item.name}
                    />
                  </div>
                </Card>
              );
            })}
          </div>
        ) : (
          <Card>
            <Empty
              icon={Heart}
              title={
                status === "purchased"
                  ? "你实现的心愿，会收藏在这里"
                  : "有什么，是你一直想要的？"
              }
              description={
                status === "purchased"
                  ? "在待实现清单中标记已购买，会自动生成一笔购物支出。"
                  : "从一件喜欢的物品开始，给每一份期待安排一个位置。"
              }
              action={
                <AddButton variant="secondary" onClick={() => setEditing({})}>
                  添加心愿
                </AddButton>
              }
            />
          </Card>
        )}
      </ResourceState>
      {editing && (
        <FormModal
          title={editing.id ? "编辑心愿" : "添加心愿"}
          initial={
            editing.id
              ? editing
              : {
                  name: "",
                  price: "",
                  currency: "CNY",
                  priority: "medium",
                  url: "",
                  note: "",
                }
          }
          fields={[
            {
              name: "name",
              label: "心愿名称",
              required: true,
              wide: true,
              placeholder: "例如：一台新的相机",
            },
            amountField("price", "预计价格"),
            currencyField,
            {
              name: "priority",
              label: "优先级",
              type: "select",
              options: options(PRIORITY),
            },
            {
              name: "url",
              label: "商品链接（选填）",
              type: "url",
              placeholder: "https://…",
            },
            ...(editing.id && editing.status === "purchased"
              ? [
                  {
                    name: "status",
                    label: "心愿状态",
                    type: "select",
                    options: [
                      { value: "pending", label: "待实现" },
                      { value: "purchased", label: "已拥有" },
                    ],
                    wide: true,
                    hint: "改回待实现不会撤销购物支出，请到收支记录中手动删除。",
                  },
                ]
              : []),
            noteField,
          ]}
          onClose={() => setEditing(null)}
          onSubmit={(payload) =>
            actions.save(
              `/dreams${editing.id ? `/${editing.id}` : ""}`,
              payload,
              editing.id ? "put" : "post",
              "心愿已保存",
            )
          }
        />
      )}
      {purchase && (
        <FormModal
          title={`实现心愿：${purchase.name}`}
          description="确认后将自动生成一笔购物支出，请填写实际支付金额。"
          initial={{ amount: purchase.price, currency: purchase.currency }}
          fields={[amountField("amount", "实际支付金额"), currencyField]}
          submitLabel="确认购买"
          onClose={() => setPurchase(null)}
          onSubmit={(payload) =>
            actions.save(
              `/dreams/${purchase.id}/purchase`,
              payload,
              "post",
              "心愿已实现，购物支出已记录",
            )
          }
        />
      )}
    </>
  );
}
