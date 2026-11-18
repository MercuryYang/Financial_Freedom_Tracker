import { Component, useEffect, useState } from "react";
import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import {
  ArrowLeftRight,
  ChartNoAxesCombined,
  Check,
  ChevronRight,
  Heart,
  LayoutDashboard,
  Menu,
  PanelLeftClose,
  RefreshCw,
  ShieldCheck,
  Target,
  Wallet,
  X,
} from "lucide-react";
import dayjs from "dayjs";
import { api, errorText } from "./api/client";
import { AppProvider, useApp } from "./state";
import { Button, ConfirmDialog, IconButton, Toasts } from "./components/UI";
import Dashboard from "./pages/Dashboard";
import Transactions from "./pages/Transactions";
import Budget from "./pages/Budget";
import Goals from "./pages/Goals";
import Assets from "./pages/Assets";
import Dreams from "./pages/Dreams";
import Investments from "./pages/Investments";
const links = [
  { to: "/", label: "财务总览", icon: LayoutDashboard },
  { to: "/transactions", label: "收支记录", icon: ArrowLeftRight },
  { to: "/budget", label: "预算管理", icon: ShieldCheck },
  { to: "/goals", label: "存款目标", icon: Target },
  { to: "/assets", label: "资产分布", icon: Wallet },
  { to: "/dreams", label: "Dream 清单", icon: Heart },
  { to: "/investments", label: "投资 Tracker", icon: ChartNoAxesCombined },
];
class ErrorBoundary extends Component {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <div className="error-state">
        <h1>页面遇到了问题</h1>
        <p>刷新页面后重试，已保存的数据不会丢失。</p>
        <Button onClick={() => window.location.reload()}>刷新页面</Button>
      </div>
    ) : (
      this.props.children
    );
  }
}
function Shell() {
  const location = useLocation(),
    { rates, refresh, notify } = useApp();
  const [menu, setMenu] = useState(false),
    [updating, setUpdating] = useState(false);
  const page =
    links.find((x) => x.to === location.pathname)?.label || "页面未找到";
  useEffect(() => {
    setMenu(false);
    window.scrollTo(0, 0);
    document.title = `${page} · 财富自由之路`;
  }, [location.pathname, page]);
  useEffect(() => {
    if (!menu) return;
    const sidebar = document.querySelector(".sidebar");
    const before = document.activeElement;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const targets = () =>
      [...sidebar.querySelectorAll("a[href], button")].filter(
        (el) => el.offsetParent !== null,
      );
    targets()[0]?.focus();
    const handleKey = (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setMenu(false);
      }
      if (event.key === "Tab") {
        const items = targets(),
          first = items[0],
          last = items[items.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("keydown", handleKey);
      document.body.style.overflow = previousOverflow;
      before?.focus();
    };
  }, [menu]);
  const updateRates = async () => {
    setUpdating(true);
    try {
      const result = (await api.post("/rates/refresh")).data;
      refresh();
      notify(
        result.refreshed
          ? "汇率已更新"
          : result.rates_updated_at
            ? "汇率源暂不可用，已保留已有缓存。"
            : "暂时无法获取外币汇率，人民币记账仍可使用。",
        result.refreshed ? "success" : "error",
      );
    } catch (e) {
      notify(errorText(e), "error");
    } finally {
      setUpdating(false);
    }
  };
  const rateDate =
    rates?.rates_updated_at ||
    rates?.currencies?.find((x) => x.code !== "CNY" && x.fetched_at)
      ?.fetched_at;
  return (
    <div className="app-shell">
      <a href="#main-content" className="skip-link">
        跳到主要内容
      </a>
      {menu && (
        <div className="sidebar-overlay" onClick={() => setMenu(false)} />
      )}
      <aside className={`sidebar ${menu ? "open" : ""}`} aria-label="主导航">
        <div className="brand">
          <span className="brand-mark">
            <ChartNoAxesCombined size={25} />
          </span>
          <div>
            <strong>财富自由之路</strong>
            <small>个人财务工作台</small>
          </div>
          <button
            className="icon-button mobile-close"
            aria-label="关闭导航"
            onClick={() => setMenu(false)}
          >
            <X size={19} />
          </button>
        </div>
        <div className="nav-caption">我的财务</div>
        <nav>
          {links.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `nav-item ${isActive ? "active" : ""}`
              }
            >
              <Icon size={19} />
              <span>{label}</span>
              <ChevronRight size={15} className="nav-arrow" />
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="currency-info">
            <span className="currency-symbol">¥</span>
            <div>
              <strong>人民币 CNY</strong>
              <small>汇总记账币种</small>
            </div>
          </div>
          <div className="workspace-owner">
            <span className="avatar">我</span>
            <div>
              <strong>我的财务空间</strong>
              <small>每一步积累，都算数</small>
            </div>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon-button menu-toggle"
              aria-label="打开导航"
              aria-expanded={menu}
              onClick={() => setMenu(true)}
            >
              <Menu size={21} />
            </button>
            <span>我的工作台</span>
            <ChevronRight size={14} />
            <strong>{page}</strong>
          </div>
          <div className="topbar-right">
            <span className="today-date">
              {dayjs().format("YYYY 年 M 月 D 日")}
            </span>
            <span className="topbar-divider" />
            <span className="live-state">
              <i />
              记录生活，积累自由
            </span>
          </div>
        </header>
        <main id="main-content" tabIndex={-1}>
          <ErrorBoundary>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/transactions" element={<Transactions />} />
              <Route path="/budget" element={<Budget />} />
              <Route path="/goals" element={<Goals />} />
              <Route path="/assets" element={<Assets />} />
              <Route path="/dreams" element={<Dreams />} />
              <Route path="/investments" element={<Investments />} />
              <Route
                path="*"
                element={
                  <div className="error-state">
                    <h1>这个页面不存在</h1>
                    <NavLink className="button" to="/">
                      回到财务总览
                    </NavLink>
                  </div>
                }
              />
            </Routes>
          </ErrorBoundary>
          <footer className="page-footer">
            <span
              className={`rate-status ${rates?.rates_stale ? "stale" : ""}`}
            >
              <i />
              {rateDate
                ? `汇率更新于 ${dayjs(rateDate).format("MM.DD HH:mm")}`
                : "尚未获取外币汇率"}
              {rates?.rates_stale && rateDate ? " · 正在使用缓存" : ""}
            </span>
            <button
              className="text-button"
              disabled={updating}
              onClick={updateRates}
            >
              <RefreshCw size={13} className={updating ? "spin" : ""} />
              {updating ? "更新中…" : "刷新汇率"}
            </button>
            <span className="footer-note">所有汇总金额以人民币显示</span>
          </footer>
        </main>
      </div>
      <ConfirmDialog />
      <Toasts />
    </div>
  );
}
export default function App() {
  return (
    <AppProvider>
      <Shell />
    </AppProvider>
  );
}
