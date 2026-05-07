import type { ReactNode } from "react";
import { BarChart3, ClipboardCheck, Download, LayoutDashboard, ListChecks, LogOut, Settings2, ShieldCheck } from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import type { Role } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useSessionStore } from "@/store/session";

type NavItem = { to: string; label: string; icon: typeof LayoutDashboard; roles: Role[] };

const items: NavItem[] = [
  { to: "/", label: "总览", icon: LayoutDashboard, roles: ["annotator", "reviewer", "admin"] },
  { to: "/tasks", label: "任务管理", icon: ListChecks, roles: ["annotator", "admin"] },
  { to: "/annotate", label: "标注工作区", icon: ClipboardCheck, roles: ["annotator", "admin"] },
  { to: "/review", label: "审核工作台", icon: ShieldCheck, roles: ["reviewer", "admin"] },
  { to: "/dashboard", label: "质量看板", icon: BarChart3, roles: ["annotator", "reviewer", "admin"] },
  { to: "/exports", label: "导出中心", icon: Download, roles: ["annotator", "reviewer", "admin"] },
  { to: "/settings/models", label: "模型设置", icon: Settings2, roles: ["admin"] },
  { to: "/settings/users", label: "用户设置", icon: Settings2, roles: ["admin"] },
];

export function AppShell({ children }: { children: ReactNode }) {
  const location = useLocation();
  const navigate = useNavigate();
  const user = useSessionStore((state) => state.user);
  const logout = useSessionStore((state) => state.logout);
  const links = items.filter((item) => user && item.roles.includes(user.role));

  return (
    <div className="min-h-screen px-4 py-4 lg:px-6">
      <div className="mx-auto grid min-h-[calc(100vh-2rem)] max-w-[1600px] gap-4 lg:grid-cols-[280px_1fr]">
        <aside className="panel-surface rounded-[32px] p-5">
          <div className="border-b border-white/10 pb-5">
            <p className="text-xs uppercase tracking-[0.28em] text-emerald-300/80">Preference Data</p>
            <h1 className="mt-3 font-display text-2xl text-white">Annotation Deck</h1>
            <p className="mt-2 text-sm text-slate-400">面向标注、审核、看板与导出的实验室工作台。</p>
          </div>
          <nav className="mt-5 space-y-2">
            {links.map((item) => {
              const Icon = item.icon;
              const active = location.pathname === item.to;
              return (
                <Link key={item.to} to={item.to} className={cn("flex items-center gap-3 rounded-2xl border px-4 py-3 text-sm transition", active ? "border-emerald-300/40 bg-emerald-300/10 text-white" : "border-white/5 bg-white/[0.03] text-slate-300 hover:border-white/10 hover:bg-white/[0.06]") }>
                  <Icon size={18} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
          <div className="mt-6 rounded-[24px] border border-white/10 bg-black/20 p-4 text-sm text-slate-300">
            <p className="font-medium text-white">{user?.name || user?.email}</p>
            <p className="mt-1 text-xs uppercase tracking-[0.24em] text-slate-500">{user?.role}</p>
            <button onClick={() => { logout(); navigate('/login'); }} className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl border border-red-400/20 bg-red-500/10 px-3 py-2 text-sm text-red-100 transition hover:bg-red-500/20">
              <LogOut size={16} /> 退出登录
            </button>
          </div>
        </aside>
        <main className="space-y-4">{children}</main>
      </div>
    </div>
  );
}
