import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Panel } from "@/components/common/Panel";
import { StatCard } from "@/components/common/StatCard";
import { api } from "@/lib/api";
import { formatPercent } from "@/lib/format";
import { useSessionStore } from "@/store/session";

export default function OverviewPage() {
  const user = useSessionStore((state) => state.user);
  const dashboardQuery = useQuery({ queryKey: ["dashboard"], queryFn: api.dashboard });
  const progressQuery = useQuery({ queryKey: ["queue-progress"], queryFn: api.queueProgress, enabled: user?.role !== "reviewer" });
  const overview = dashboardQuery.data?.overview;

  const cards = [
    { label: "总任务数", value: String(overview?.total_tasks ?? "--"), hint: "覆盖当前工作台数据规模" },
    { label: "全局 Kappa", value: overview?.global_kappa?.toFixed(2) ?? "--", hint: "用于衡量一致性" },
    { label: "可用数据比例", value: formatPercent(overview?.usable_data_ratio), hint: "剔除 Drop/低一致性/低区分度" },
    { label: "个人剩余任务", value: String(progressQuery.data?.remaining_tasks ?? "--"), hint: "仅针对标注者路径" },
  ];

  return (
    <div className="space-y-4">
      <Panel title="工作台总览" subtitle="把标注、审核、质量和导出收束在一个仪表盘里。">
        <div className="grid gap-4 lg:grid-cols-4">{cards.map((card) => <StatCard key={card.label} {...card} />)}</div>
      </Panel>
      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Panel title="角色路径" subtitle="根据当前角色快速进入核心操作区。">
          <div className="grid gap-4 md:grid-cols-2">
            {[
              ["任务管理", "/tasks", "创建任务、批量导入、查看状态与 Kappa"],
              ["标注工作区", "/annotate", "领取下一条任务、排序打分编辑并提交"],
              ["审核工作台", "/review", "按集合处理低质量任务与异常标注"],
              ["导出中心", "/exports", "生成训练数据并下载导出作业"],
            ].map(([title, href, desc]) => (
              <Link key={href} to={href} className="rounded-[24px] border border-white/10 bg-black/20 p-5 transition hover:border-emerald-300/30 hover:bg-white/[0.05]">
                <p className="font-display text-lg text-white">{title}</p>
                <p className="mt-2 text-sm leading-6 text-slate-400">{desc}</p>
              </Link>
            ))}
          </div>
        </Panel>
        <Panel title="当前身份" subtitle="显示登录用户与角色授权范围。">
          <div className="space-y-4 rounded-[28px] border border-white/10 bg-black/20 p-5">
            <div>
              <p className="text-xs uppercase tracking-[0.28em] text-slate-500">用户</p>
              <p className="mt-2 font-display text-2xl text-white">{user?.name || user?.email}</p>
            </div>
            <div className="flex flex-wrap gap-3 text-sm">
              <span className="rounded-full border border-emerald-300/20 bg-emerald-300/10 px-3 py-2 text-emerald-100">角色：{user?.role}</span>
              {overview ? <span className="rounded-full border border-white/10 px-3 py-2 text-slate-300">Drop 率：{formatPercent(overview.drop_rate)}</span> : null}
              {overview ? <span className="rounded-full border border-white/10 px-3 py-2 text-slate-300">低区分度占比：{formatPercent(overview.low_distinctness_ratio)}</span> : null}
            </div>
          </div>
        </Panel>
      </div>
    </div>
  );
}
