import { useEffect, useId, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertCircle,
  ArrowDownLeft,
  ArrowUpRight,
  Check,
  ChevronLeft,
  ChevronRight,
  Inbox,
  Loader2,
  Pencil,
  Plus,
  Trash2,
  X,
} from "lucide-react";
import dayjs from "dayjs";
import { api, errorText } from "../api/client";
import { useApp } from "../state";
import { money, CURRENCIES, categoryName, dateText } from "../constants";
export const Button = ({
  children,
  variant = "",
  className = "",
  ...props
}) => (
  <button className={`button ${variant} ${className}`} {...props}>
    {children}
  </button>
);
export const AddButton = ({ children = "新增", ...props }) => (
  <Button {...props}>
    <Plus size={17} />
    {children}
  </Button>
);
export function PageTitle({ title, description, action }) {
  return (
    <div className="page-heading">
      <div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      <div className="page-actions">{action}</div>
    </div>
  );
}
export function Card({ title, sub, action, children, className = "" }) {
  return (
    <section className={`card ${className}`}>
      {title && (
        <div className="card-heading">
          <div>
            <h2>{title}</h2>
            {sub && <p>{sub}</p>}
          </div>
          {action}
        </div>
      )}
      {children}
    </section>
  );
}
export function Empty({
  title = "还没有记录",
  description = "添加第一笔记录，开始了解你的财务状况。",
  action,
  compact = false,
  icon: Icon = Inbox,
}) {
  return (
    <div className={`empty-state ${compact ? "compact" : ""}`}>
      <span className="empty-icon">
        <Icon size={25} />
      </span>
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  );
}
export function ResourceState({ resource, children }) {
  if (resource.loading && !resource.data)
    return (
      <div className="loading-state" role="status">
        <Loader2 className="spin" size={24} />
        <span>正在整理你的财务数据…</span>
      </div>
    );
  if (resource.error)
    return (
      <div className="error-state" role="alert">
        <AlertCircle size={24} />
        <h3>暂时无法加载</h3>
        <p>{resource.error}</p>
        <Button variant="secondary" onClick={resource.reload}>
          重新加载
        </Button>
      </div>
    );
  return children;
}
export function Money({
  value,
  currency = "CNY",
  cny,
  sign = "",
  className = "",
}) {
  const { rates } = useApp();
  const rate =
    currency === "CNY"
      ? 1
      : rates?.currencies?.find((x) => x.code === currency)?.rate;
  const converted = cny ?? (rate ? Number(value) * rate : null);
  return (
    <span className={`money-stack ${className}`}>
      <span>
        {sign}
        {money(value, currency)}
      </span>
      {currency !== "CNY" && <small>≈ {money(converted)} CNY</small>}
    </span>
  );
}
export function Metric({
  label,
  value,
  hint,
  icon: Icon,
  tone = "",
  currency = "CNY",
}) {
  return (
    <div className={`metric ${tone}`}>
      <div className="metric-top">
        <span>{label}</span>
        {Icon && <Icon size={19} />}
      </div>
      <strong>{money(value, currency)}</strong>
      {hint && <small>{hint}</small>}
    </div>
  );
}
export function Progress({ value = 0, tone = "", label }) {
  return (
    <div
      className={`progress ${tone}`}
      role="progressbar"
      aria-label={label || "完成进度"}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(Math.min(1, Math.max(0, value)) * 100)}
    >
      <span style={{ width: `${Math.min(1, Math.max(0, value)) * 100}%` }} />
    </div>
  );
}
export function MonthPicker({ value, onChange }) {
  return (
    <div className="month-picker">
      <button
        aria-label="上个月"
        onClick={() =>
          onChange(dayjs(`${value}-01`).subtract(1, "month").format("YYYY-MM"))
        }
      >
        <ChevronLeft size={18} />
      </button>
      <label>
        <span className="sr-only">选择月份</span>
        <input
          type="month"
          value={value}
          onChange={(e) => e.target.value && onChange(e.target.value)}
        />
      </label>
      <button
        aria-label="下个月"
        onClick={() =>
          onChange(dayjs(`${value}-01`).add(1, "month").format("YYYY-MM"))
        }
      >
        <ChevronRight size={18} />
      </button>
    </div>
  );
}
export function IconButton({ icon: Icon, label, ...props }) {
  return (
    <button className="icon-button" aria-label={label} title={label} {...props}>
      <Icon size={16} />
    </button>
  );
}
export function RowActions({ onEdit, onDelete, label = "" }) {
  return (
    <div className="row-actions">
      {onEdit && (
        <IconButton icon={Pencil} label={`编辑${label}`} onClick={onEdit} />
      )}
      {onDelete && (
        <IconButton icon={Trash2} label={`删除${label}`} onClick={onDelete} />
      )}
    </div>
  );
}
export function Modal({ title, description, onClose, children, wide = false }) {
  const id = useId(),
    ref = useRef(),
    close = useRef(onClose);
  close.current = onClose;
  useEffect(() => {
    const before = document.activeElement,
      old = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const el = ref.current;
    const focusable = () =>
      [
        ...el.querySelectorAll(
          'button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),a[href],[tabindex="0"]',
        ),
      ].filter((x) => x.offsetParent !== null);
    focusable()[0]?.focus();
    const key = (e) => {
      if (e.key === "Escape") {
        e.preventDefault();
        close.current?.();
      }
      if (e.key === "Tab") {
        const elements = focusable(),
          first = elements[0],
          last = elements[elements.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last?.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first?.focus();
        }
      }
    };
    el.addEventListener("keydown", key);
    return () => {
      el.removeEventListener("keydown", key);
      document.body.style.overflow = old;
      before?.focus();
    };
  }, []);
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose?.();
      }}
    >
      <section
        className={`modal ${wide ? "wide" : ""}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby={id}
        ref={ref}
      >
        <div className="modal-heading">
          <div>
            <h2 id={id}>{title}</h2>
            {description && <p>{description}</p>}
          </div>
          <IconButton label="关闭弹窗" icon={X} onClick={onClose} />
        </div>
        {children}
      </section>
    </div>
  );
}
export function FormModal({
  title,
  description,
  initial = {},
  fields,
  onSubmit,
  onClose,
  submitLabel = "保存",
}) {
  const [values, setValues] = useState(initial),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const errorRef = useRef();
  const rendered = typeof fields === "function" ? fields(values) : fields;
  const update = (field, value) =>
    setValues((prev) => ({
      ...prev,
      [field.name]: value,
      ...(field.onChange?.(value, prev) || {}),
    }));
  const submit = async (e) => {
    e.preventDefault();
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      let payload = {};
      for (const field of rendered) {
        let v = values[field.name] ?? "";
        if (field.type === "number")
          v = v === "" ? (field.required ? 0 : null) : Number(v);
        if (field.type === "checkbox") v = Boolean(v);
        if (v === "" && field.nullable) v = null;
        payload[field.name] = v;
      }
      await onSubmit(payload);
      onClose();
    } catch (e) {
      setError(errorText(e));
      setTimeout(() => errorRef.current?.focus(), 0);
    } finally {
      setBusy(false);
    }
  };
  return (
    <Modal
      title={title}
      description={description}
      onClose={busy ? () => {} : onClose}
    >
      <form onSubmit={submit}>
        <div className="form-body">
          {error && (
            <div
              className="form-error"
              role="alert"
              tabIndex={-1}
              ref={errorRef}
            >
              {error}
            </div>
          )}
          <div className="form-grid">
            {rendered.map((field) => (
              <label
                className={`field ${field.wide ? "full" : ""} ${field.type === "checkbox" ? "check-field" : ""}`}
                key={field.name}
              >
                <span>
                  {field.label}
                  {field.required && <span className="required"> *</span>}
                </span>
                {field.type === "select" ? (
                  <select
                    required={field.required}
                    value={values[field.name] ?? ""}
                    onChange={(e) => update(field, e.target.value)}
                  >
                    {(field.options || []).map((option) =>
                      typeof option === "string" ? (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ) : (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ),
                    )}
                  </select>
                ) : field.type === "textarea" ? (
                  <textarea
                    rows={3}
                    value={values[field.name] ?? ""}
                    onChange={(e) => update(field, e.target.value)}
                    maxLength={field.maxLength || 1000}
                    placeholder={field.placeholder}
                  />
                ) : (
                  <input
                    type={field.type || "text"}
                    value={
                      field.type === "checkbox"
                        ? undefined
                        : (values[field.name] ?? "")
                    }
                    checked={
                      field.type === "checkbox"
                        ? Boolean(values[field.name])
                        : undefined
                    }
                    onChange={(e) =>
                      update(
                        field,
                        field.type === "checkbox"
                          ? e.target.checked
                          : e.target.value,
                      )
                    }
                    required={field.required}
                    min={field.min}
                    max={field.max}
                    step={
                      field.type === "number"
                        ? (field.step ?? "0.01")
                        : undefined
                    }
                    maxLength={field.maxLength || 200}
                    placeholder={field.placeholder}
                    inputMode={field.type === "number" ? "decimal" : undefined}
                  />
                )}{" "}
                {field.hint && <small>{field.hint}</small>}
              </label>
            ))}
          </div>
        </div>
        <div className="modal-footer">
          <Button
            type="button"
            variant="secondary"
            disabled={busy}
            onClick={onClose}
          >
            取消
          </Button>
          <Button type="submit" disabled={busy}>
            {busy ? (
              <Loader2 size={16} className="spin" />
            ) : (
              <Check size={16} />
            )}
            {busy ? "正在保存…" : submitLabel}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
export const currencyField = {
  name: "currency",
  label: "币种",
  type: "select",
  options: CURRENCIES.map((value) => ({
    value,
    label: value === "CNY" ? "人民币 · CNY" : "美元 · USD",
  })),
  required: true,
};
export const amountField = (name = "amount", label = "金额") => ({
  name,
  label,
  type: "number",
  min: "0.01",
  step: "0.01",
  required: true,
});
export const noteField = {
  name: "note",
  label: "备注",
  type: "textarea",
  wide: true,
  placeholder: "添加一些说明（选填）",
};
export function useActions() {
  const { refresh, notify, confirm } = useApp();
  return {
    save: async (path, payload, method = "post", message = "已保存") => {
      await api[method](path, payload);
      refresh();
      notify(message);
    },
    remove: async (path, name = "这条记录", description) => {
      if (
        !(await confirm(
          `删除${name}？`,
          description || "删除后无法恢复，请确认后继续。",
        ))
      )
        return;
      try {
        await api.delete(path);
        refresh();
        notify("已删除");
      } catch (e) {
        notify(errorText(e), "error");
      }
    },
  };
}
export function ConfirmDialog() {
  const { confirmation, setConfirmation } = useApp();
  const close = (value) => {
    confirmation.resolve(value);
    setConfirmation(null);
  };
  return confirmation ? (
    <Modal
      title={confirmation.title}
      description={confirmation.description}
      onClose={() => close(false)}
    >
      <div className="modal-footer">
        <Button variant="secondary" onClick={() => close(false)}>
          取消
        </Button>
        <Button variant="danger" onClick={() => close(true)}>
          确认删除
        </Button>
      </div>
    </Modal>
  ) : null;
}
export function Toasts() {
  const { toasts } = useApp();
  return (
    <div className="toasts" aria-live="polite">
      {toasts.map((x) => (
        <div className={`toast ${x.type}`} key={x.id}>
          {x.type === "error" ? <AlertCircle size={19} /> : <Check size={19} />}
          {x.text}
        </div>
      ))}
    </div>
  );
}
export function TransactionTable({ items, onEdit, onDelete, compact = false }) {
  return (
    <div className={`table-scroll ${compact ? "compact-transactions" : ""}`}>
      <table>
        <thead>
          <tr>
            <th>交易</th>
            <th>日期</th>
            {!compact && <th>来源</th>}
            <th className="align-right">金额</th>
            {!compact && <th className="align-right">操作</th>}
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}>
              <td>
                <div className="transaction-cell">
                  <span className={`category-icon ${item.type}`}>
                    {item.type === "income" ? (
                      <ArrowDownLeft size={18} />
                    ) : (
                      <ArrowUpRight size={18} />
                    )}
                  </span>
                  <div>
                    <strong>{categoryName(item)}</strong>
                    {compact && (
                      <time
                        className="mobile-transaction-date"
                        dateTime={item.tx_date}
                      >
                        {dateText(item.tx_date)}
                      </time>
                    )}
                    <small>
                      {item.note ||
                        (item.type === "income" ? "收入记录" : "日常支出")}
                    </small>
                  </div>
                </div>
              </td>
              <td className="muted nowrap">{dateText(item.tx_date)}</td>
              {!compact && (
                <td>
                  <span className="tag">
                    {{
                      manual: "手动记录",
                      recurring: "周期记录",
                      dream: "心愿购买",
                    }[item.source] || "手动记录"}
                  </span>
                </td>
              )}
              <td className="align-right">
                <Money
                  value={item.amount}
                  currency={item.currency}
                  cny={item.amount_cny}
                  sign={item.type === "income" ? "+" : "−"}
                  className={item.type === "income" ? "positive" : ""}
                />
              </td>
              {!compact && (
                <td>
                  <RowActions
                    onEdit={() => onEdit(item)}
                    onDelete={() => onDelete(item)}
                    label={`${categoryName(item)}记录`}
                  />
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
export const MoreLink = ({ to, children = "查看全部" }) => (
  <Link className="more-link" to={to}>
    {children}
    <ArrowUpRight size={14} />
  </Link>
);
