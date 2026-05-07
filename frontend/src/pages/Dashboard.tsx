import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Panel } from "@/components/common/Panel";
import { StatCard } from "@/components/common/StatCard";
import { api } from "@/lib/api";
import { formatDuration, formatPercent } from "@/lib/format";

export default function DashboardPage() {
  const dashboardQuery = useQuery({ queryKey: ["dashboard"], queryFn: api.dashboard });
  const kappaQuery = useQuery({ queryKey: ["kappa"], queryFn: api.kappa });
  const annotatorsQuery = useQuery({ queryKey: ["annotators"], queryFn: api.annotators });
  const overview = dashboardQuery.data?.overview;
  const kappaData = (dashboardQuery.data?.kappa_histogram || []).map((count, index) => ({ bucket: `${index / 10}-${(index + 1) / 10}`, count }));
  const similarityData = (dashboardQuery.data?.similarity_histogram || []).map((count, index) => ({ bucket: `${index / 10}-${(index + 1) / 10}`, count }));

  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-5">
        <StatCard label="总任务" value={String(overview?.total_tasks ?? "--")} />
        <StatCard label="已完成" value={String(overview?.completed_tasks ?? "--")} />
        <StatCard label="Drop 率" value={formatPercent(overview?.drop_rate)} />
        <StatCard label="平均耗时" value={formatDuration(overview?.avg_duration_ms)} />
        <StatCard label="可用数据比例" value={formatPercent(overview?.usable_data_ratio)} />
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <Panel title="Kappa 分布" subtitle="包含全局 Kappa、分 Task Kappa 与分类 Kappa。">
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={kappaData}><CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} /><XAxis dataKey="bucket" tick={{ fill: '#94a3b8', fontSize: 12 }} /><YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} /><Tooltip /><Bar dataKey="count" fill="#48ffc7" radius={[8, 8, 0, 0]} /></BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-4 grid gap-3 md:grid-cols-2">{(kappaQuery.data?.per_category || []).map((item) => <div key={item.category} className="rounded-[20px] border border-white/10 bg-black/20 p-4 text-sm text-slate-300">{item.category} · {item.task_count} 条 · Kappa {item.kappa?.toFixed(2) ?? "--"}</div>)}</div>
        </Panel>
        <Panel title="Prompt 多样性与区分度" subtitle="同时呈现类别覆盖和相似度分布。">
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={dashboardQuery.data?.category_distribution || []} dataKey="task_count" nameKey="category" innerRadius={58} outerRadius={92} fill="#ffb84c" label />
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={similarityData}><CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} /><XAxis dataKey="bucket" tick={{ fill: '#94a3b8', fontSize: 12 }} /><YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} /><Tooltip /><Bar dataKey="count" fill="#ffb84c" radius={[8, 8, 0, 0]} /></BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </Panel>
      </div>
      <Panel title="标注者行为分析" subtitle="耗时、Drop 率、位置偏差与对他人一致性。">
        <div className="space-y-3">
          {(annotatorsQuery.data?.items || []).map((item) => (
            <div key={item.annotator_id} className="grid gap-3 rounded-[24px] border border-white/10 bg-black/20 p-4 lg:grid-cols-5">
              <div className="text-white">Annotator #{item.annotator_id}</div>
              <div className="text-slate-300">任务数：{item.task_count}</div>
              <div className="text-slate-300">耗时：{formatDuration(item.avg_duration_ms)}</div>
              <div className="text-slate-300">Drop：{formatPercent(item.drop_rate)}</div>
              <div className="text-slate-300">位置偏差：{formatPercent(item.position_bias || 0)}</div>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
