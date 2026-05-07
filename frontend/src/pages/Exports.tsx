import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { Panel } from "@/components/common/Panel";
import { api } from "@/lib/api";

export default function ExportsPage() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ format: "dpo", file_type: "jsonl", min_kappa: "0.4", tie_handling: "random", use_edits: true });
  const jobsQuery = useQuery({ queryKey: ["export-jobs"], queryFn: api.exportJobs });
  const exportMutation = useMutation({
    mutationFn: () => api.exportData({ format: form.format, file_type: form.file_type, min_kappa: Number(form.min_kappa), tie_handling: form.tie_handling, use_edits: form.use_edits }),
    onSuccess: () => {
      toast.success("导出任务已创建");
      queryClient.invalidateQueries({ queryKey: ["export-jobs"] });
    },
    onError: (error: Error) => toast.error(error.message),
  });
  const deleteMutation = useMutation({
    mutationFn: (jobId: string) => api.deleteExportJob(jobId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["export-jobs"] }),
  });

  async function handleDownload(jobId: string) {
    try {
      const { blob, filename } = await api.downloadExportJob(jobId);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename || `${jobId}.download`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "下载失败");
    }
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
      <Panel title="导出表单" subtitle="训练工程师可在这里控制数据质量阈值。">
        <div className="space-y-4">
          <select value={form.format} onChange={(event) => setForm((prev) => ({ ...prev, format: event.target.value }))} className="w-full rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3"><option value="dpo">DPO</option><option value="alpaca">Alpaca</option></select>
          <select value={form.file_type} onChange={(event) => setForm((prev) => ({ ...prev, file_type: event.target.value }))} className="w-full rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3"><option value="jsonl">JSONL</option><option value="json">JSON</option><option value="csv">CSV</option></select>
          <input value={form.min_kappa} onChange={(event) => setForm((prev) => ({ ...prev, min_kappa: event.target.value }))} className="w-full rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3" placeholder="最低 Kappa" />
          <select value={form.tie_handling} onChange={(event) => setForm((prev) => ({ ...prev, tie_handling: event.target.value }))} className="w-full rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3"><option value="random">tie=random</option><option value="skip">tie=skip</option></select>
          <label className="flex items-center gap-3 rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-slate-300"><input type="checkbox" checked={form.use_edits} onChange={(event) => setForm((prev) => ({ ...prev, use_edits: event.target.checked }))} />优先使用编辑后内容</label>
          <button onClick={() => exportMutation.mutate()} className="rounded-2xl border border-emerald-300/30 bg-emerald-300/15 px-4 py-3 text-white">生成导出</button>
        </div>
      </Panel>
      <Panel title="导出作业" subtitle="显示下载链接和删除动作。">
        <div className="space-y-3">
          {(jobsQuery.data || []).map((job) => (
            <div key={job.id} className="grid gap-3 rounded-[24px] border border-white/10 bg-black/20 p-4 lg:grid-cols-[1fr_auto_auto] lg:items-center">
              <div>
                <p className="font-medium text-white">{job.id}</p>
                <p className="mt-1 text-sm text-slate-400">{job.format} / {job.file_type} / {job.status}</p>
              </div>
              {job.download_url ? <button onClick={() => void handleDownload(job.id)} className="rounded-2xl border border-white/10 px-4 py-3 text-sm text-slate-200">下载</button> : <span className="text-sm text-slate-500">无文件</span>}
              <button onClick={() => deleteMutation.mutate(job.id)} className="rounded-2xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-100">删除</button>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
