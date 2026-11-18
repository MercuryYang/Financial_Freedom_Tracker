import dayjs from "dayjs";
export const CURRENCIES = ["CNY", "USD"];
export const INCOME = {
  salary: "工资",
  bonus: "奖金",
  side_hustle: "副业",
  investment: "投资收益",
  other: "其他",
};
export const EXPENSE = {
  food: "餐饮",
  housing: "住房",
  transport: "交通",
  shopping: "购物",
  entertainment: "娱乐",
  medical: "医疗",
  education: "教育",
  other: "其他",
};
export const ASSETS = {
  cash: "现金",
  checking: "活期存款",
  term_deposit: "定期存款",
  real_estate: "房产",
  other: "其他资产",
  investment_portfolio: "投资组合",
};
export const INVESTMENTS = {
  stock: "股票",
  etf: "ETF",
  fund: "基金",
  crypto: "加密货币",
  bond: "债券",
  other: "其他",
};
export const PRIORITY = {
  high: "优先实现",
  medium: "慢慢积累",
  low: "未来计划",
};
export const STATUS = { active: "进行中", done: "已完成", abandoned: "已暂停" };
export const CHART_COLORS = [
  "#267765",
  "#759c8c",
  "#dbad64",
  "#7b92b5",
  "#ac87a0",
  "#85b2b8",
  "#b8bd8a",
  "#cf8e80",
];
export const today = () => dayjs().format("YYYY-MM-DD");
export const currentMonth = () => dayjs().format("YYYY-MM");
export const dateText = (date) =>
  date ? dayjs(date).format("YYYY.MM.DD") : "—";
export const money = (value, currency = "CNY") =>
  value === null || value === undefined || !Number.isFinite(Number(value))
    ? "—"
    : new Intl.NumberFormat("zh-CN", {
        style: "currency",
        currency,
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }).format(Number(value));
export const number = (value) =>
  new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 6 }).format(
    Number(value) || 0,
  );
export const percent = (value) => `${((Number(value) || 0) * 100).toFixed(1)}%`;
export const options = (obj) =>
  Object.entries(obj).map(([value, label]) => ({ value, label }));
export const categoryName = (item) =>
  (item.type === "income" ? INCOME : EXPENSE)[item.category] || item.category;
