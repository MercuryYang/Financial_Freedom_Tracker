import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { CalendarDays, History, Plus, Target } from "lucide-react";
import dayjs from "dayjs";
import { get } from "../api/client";
import { useResource } from "../state";
import { STATUS, dateText, money, options, percent, today } from "../constants";
import {
  AddButton,
  Button,
  Card,
  Empty,
  FormModal,
  Modal,
  Money,
  PageTitle,
  Progress,
  ResourceState,
  RowActions,
  amountField,
  currencyField,
  noteField,
  useActions,
} from "../components/UI";
function Contributions({ goal, onClose }) {
  const resource = useResource(
    () => get(`/goals/${goal.id}/contributions`),
    [goal.id],
  );
  const actions = useActions();
  return (
    <Modal title={`${goal.name} · 存入历史`} onClose={onClose} wide>
      <div className="modal-body">
        <ResourceState resource={resource}>
          {resource.data?.length ? (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>日期</th>
                    <th>备注</th>
                    <th className="align-right">金额</th>
                    <th>操作</th>
                  </tr>
                </thead>
                <tbody>
                  {(resource.data || []).map((x) => (
                    <tr key={x.id}>
                      <td>{dateText(x.contributed_at)}</td>
                      <td>{x.note || "—"}</td>
                      <td className="align-right">
                        <Money
                          value={x.amount}
                          currency={x.currency}
                          cny={x.amount_cny}
                        />
                      </td>
                      <td>
                        <RowActions
                          onDelete={() =>
                            actions.remove(`/contributions/${x.id}`, "这笔存入")
                          }
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <Empty
              compact
              title="还没有存入记录"
              description="存下第一笔，让目标向前一步。"
            />
          )}
        </ResourceState>
      </div>
    </Modal>
  );
}
export default function Goals() {
  const [params] = useSearchParams();
  const [editing, setEditing] = useState(params.get("new") ? {} : null),
    [deposit, setDeposit] = useState(null),
    [history, setHistory] = useState(null),
    [filter, setFilter] = useState("active");
  const actions = useActions();
  const resource = useResource(() => get("/goals"));
  const all = resource.data || [],
    goals = all.filter((x) => filter === "all" || x.status === filter);
  const initial = editing?.id
    ? editing
    : {
        name: "",
        target_amount: "",
        currency: "CNY",
        deadline: "",
        status: "active",
      };
  return (
    <>
      <PageTitle
        title="存款目标"
        description="为值得期待的事，存下每一个小小的进展。"
        action={<AddButton onClick={() => setEditing({})}>新建目标</AddButton>}
      />
      <div className="tabs standalone">
        <button
          className={filter === "active" ? "active" : ""}
          onClick={() => setFilter("active")}
        >
          进行中 <span>{all.filter((x) => x.status === "active").length}</span>
        </button>
        <button
          className={filter === "done" ? "active" : ""}
          onClick={() => setFilter("done")}
        >
          已完成
        </button>
        <button
          className={filter === "all" ? "active" : ""}
          onClick={() => setFilter("all")}
        >
          全部目标
        </button>
      </div>
      <ResourceState resource={resource}>
        {goals.length ? (
          <div className="goal-grid">
            {goals.map((g, i) => {
              const days = g.deadline
                ? dayjs(g.deadline).diff(dayjs().startOf("day"), "day")
                : null;
              return (
                <Card key={g.id} className="goal-card">
                  <div className="between">
                    <span className={`goal-icon goal-${i % 3}`}>
                      <Target size={25} />
                    </span>
                    <span
                      className={`tag ${g.status === "done" ? "green" : ""}`}
                    >
                      {STATUS[g.status] || g.status}
                    </span>
                  </div>
                  <h2>{g.name}</h2>
                  <div className="goal-value">
                    <strong>{money(g.contributed_cny)}</strong>
                    <span> / {money(g.target_cny)}</span>
                  </div>
                  {g.currency !== "CNY" && (
                    <p className="muted text-small">
                      目标原币 {money(g.target_amount, g.currency)}
                    </p>
                  )}
                  <div className="between text-small">
                    <span className="muted">已完成</span>
                    <strong className="positive">{percent(g.progress)}</strong>
                  </div>
                  <Progress value={g.progress} label={g.name} />
                  <div className="goal-details">
                    <span>
                      还差 <b>{money(Math.max(0, g.remaining_cny || 0))}</b>
                    </span>
                    <span>
                      <CalendarDays size={14} />
                      {days === null
                        ? "不设截止日"
                        : days < 0
                          ? `已逾期 ${Math.abs(days)} 天`
                          : `剩余 ${days} 天`}
                    </span>
                  </div>
                  <div className="goal-actions">
                    <Button
                      variant="secondary small"
                      onClick={() => setDeposit(g)}
                    >
                      <Plus size={15} />
                      存入一笔
                    </Button>
                    <button
                      className="icon-button"
                      aria-label={`${g.name}存入历史`}
                      title="存入历史"
                      onClick={() => setHistory(g)}
                    >
                      <History size={17} />
                    </button>
                    <RowActions
                      onEdit={() => setEditing(g)}
                      onDelete={() =>
                        actions.remove(
                          `/goals/${g.id}`,
                          g.name,
                          "删除目标会同时删除该目标的所有存入记录。",
                        )
                      }
                      label={g.name}
                    />
                  </div>
                </Card>
              );
            })}
          </div>
        ) : (
          <Card>
            <Empty
              icon={Target}
              title={
                filter === "done"
                  ? "完成的目标会留在这里"
                  : "让目标，从一个名字开始"
              }
              description={
                filter === "done"
                  ? "每一次达成，都值得被记住。"
                  : "一笔应急金、一次旅行、一个家。选择你想要的未来。"
              }
              action={
                <AddButton variant="secondary" onClick={() => setEditing({})}>
                  新建存款目标
                </AddButton>
              }
            />
          </Card>
        )}
      </ResourceState>
      {editing && (
        <FormModal
          title={editing.id ? "编辑存款目标" : "新建存款目标"}
          initial={initial}
          onClose={() => setEditing(null)}
          fields={[
            {
              name: "name",
              label: "目标名称",
              required: true,
              wide: true,
              placeholder: "例如：六个月应急基金",
            },
            amountField("target_amount", "目标金额"),
            currencyField,
            {
              name: "deadline",
              label: "截止日期（选填）",
              type: "date",
              nullable: true,
            },
            ...(editing.id
              ? [
                  {
                    name: "status",
                    label: "目标状态",
                    type: "select",
                    options: options(STATUS),
                  },
                ]
              : []),
          ]}
          onSubmit={(payload) =>
            actions.save(
              `/goals${editing.id ? `/${editing.id}` : ""}`,
              payload,
              editing.id ? "put" : "post",
              "目标已保存",
            )
          }
        />
      )}
      {deposit && (
        <FormModal
          title={`存入「${deposit.name}」`}
          initial={{
            amount: "",
            currency: deposit.currency,
            contributed_at: today(),
            note: "",
          }}
          fields={[
            amountField(),
            currencyField,
            {
              name: "contributed_at",
              label: "存入日期",
              type: "date",
              required: true,
            },
            noteField,
          ]}
          onClose={() => setDeposit(null)}
          onSubmit={(payload) =>
            actions.save(
              `/goals/${deposit.id}/contributions`,
              payload,
              "post",
              "已记录存入，离目标更近一步",
            )
          }
        />
      )}
      {history && (
        <Contributions goal={history} onClose={() => setHistory(null)} />
      )}
    </>
  );
}
