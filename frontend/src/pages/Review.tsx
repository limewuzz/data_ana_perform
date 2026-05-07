import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { Panel } from "@/components/common/Panel";
import { api, type ReviewAnnotatorItem, type ReviewTaskItem } from "@/lib/api";

const tabs = {
  "low-kappa": "/api/review-sets/low-kappa",
  "needs-rework": "/api/review-sets/needs-rework",
  "low-margin": "/api/review-sets/low-margin",
  "slow-tasks": "/api/review-sets/slow-tasks",
  anomalies: "/api/review-sets/annotators/anomalies",
  inconsistencies: "/api/review-sets/annotators/inconsistencies",
} as const;

export default function ReviewPage() {
  const queryClient = useQueryClient();
  const [tab, setTab] = useState<keyof typeof tabs>("low-kappa");
  const [action, setAction] = useState("needs_rework");
  const [reason, setReason] = useState("");
  const [selectedTaskIds, setSelectedTaskIds] = useState<number[]>([]);
  const [previewResult, setPreviewResult] = useState<string>("");
  const reviewQuery = useQuery({ queryKey: ["review-set", tab], queryFn: () => api.reviewSet(tabs[tab]) });
  const eventsQuery = useQuery({ queryKey: ["review-events"], queryFn: api.reviewEvents });

  const items = useMemo(() => reviewQuery.data?.items || [], [reviewQuery.data]);
  const isTaskTab = tab !== "anomalies" && tab !== "inconsistencies";

  const applyMutation = useMutation({
    mutationFn: (dryRun: boolean) => api.applySetAction({ set_name: tab, action, reason: reason || undefined, dry_run: dryRun }),
    onSuccess: (result, dryRun) => {
      toast.success(dryRun ? "已生成 dry-run 预览" : "集合动作已执行");
      setPreviewResult(JSON.stringify(result, null, 2));
      queryClient.invalidateQueries({ queryKey: ["review-set", tab] });
      queryClient.invalidateQueries({ queryKey: ["review-events"] });
    },
    onError: (error: Error) => toast.error(error.message),
  });
  const bulkMutation = useMutation({
    mutationFn: () => api.bulkReviewAction({ task_ids: selectedTaskIds, action, reason: reason || undefined, source_set: tab }),
    onSuccess: () => {
      toast.success("批量动作已执行");
      setSelectedTaskIds([]);
      queryClient.invalidateQueries({ queryKey: ["review-set", tab] });
      queryClient.invalidateQueries({ queryKey: ["review-events"] });
    },
    onError: (error: Error) => toast.error(error.message),
  });

  function toggleTask(taskId: number) {
    setSelectedTaskIds((prev) => (prev.includes(taskId) ? prev.filter((id) => id !== taskId) : [...prev, taskId]));
  }

  function renderTaskItem(item: ReviewTaskItem) {
    const checked = selectedTaskIds.includes(item.task_id);
    return (
      <label key={item.task_id} className={`block rounded-[24px] border p-4 text-sm transition ${checked ? "border-emerald-300/30 bg-emerald-300/10" : "border-white/10 bg-black/20"}`}>
        <div className="flex items-start gap-3">
          <input type="checkbox" checked={checked} onChange={() => toggleTask(item.task_id)} className="mt-1" />
          <div className="flex-1">
            <div className="flex flex-wrap items-center gap-3">
              <p className="font-medium text-white">Task #{item.task_id}</p>
              <span className="rounded-full border border-white/10 px-3 py-1 text-xs uppercase tracking-[0.16em] text-slate-400">{item.status}</span>
              <span className="rounded-full border border-white/10 px-3 py-1 text-xs uppercase tracking-[0.16em] text-slate-400">{item.review_status}</span>
            </div>
            <p className="mt-3 leading-7 text-slate-300">{item.prompt}</p>
            <div className="mt-3 flex flex-wrap gap-3 text-xs text-slate-500">
              {typeof item.kappa === "number" ? <span>Kappa: {item.kappa.toFixed(2)}</span> : null}
              {typeof item.small_margin_ratio === "number" ? <span>Small margin: {(item.small_margin_ratio * 100).toFixed(1)}%</span> : null}
              {typeof item.avg_duration_ms === "number" ? <span>Avg duration: {(item.avg_duration_ms / 1000).toFixed(1)}s</span> : null}
            </div>
          </div>
        </div>
      </label>
    );
  }

  function renderAnnotatorItem(item: ReviewAnnotatorItem) {
    return (
      <div key={item.annotator_id} className="rounded-[24px] border border-white/10 bg-black/20 p-4 text-sm">
        <div className="flex flex-wrap items-center gap-3">
          <p className="font-medium text-white">Annotator #{item.annotator_id}</p>
          {(item.flags || []).map((flag) => (
            <span key={flag} className="rounded-full border border-amber-300/20 bg-amber-300/10 px-3 py-1 text-xs uppercase tracking-[0.16em] text-amber-100">{flag}</span>
          ))}
        </div>
        <div className="mt-3 grid gap-3 md:grid-cols-3 text-slate-300">
          <div>任务数：{item.task_count}</div>
          {typeof item.annotation_count === "number" ? <div>标注数：{item.annotation_count}</div> : null}
          <div>Drop：{(item.drop_rate * 100).toFixed(1)}%</div>
          {typeof item.avg_duration_ms === "number" ? <div>耗时：{(item.avg_duration_ms / 1000).toFixed(1)}s</div> : null}
          {typeof item.avg_kappa_with_others === "number" ? <div>Kappa：{item.avg_kappa_with_others.toFixed(2)}</div> : null}
          {typeof item.conflict_rate === "number" ? <div>冲突率：{(item.conflict_rate * 100).toFixed(1)}%</div> : null}
        </div>
      </div>
    );
  }

  return (
    <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
      <Panel title="审查集合" subtitle="面向集合处理低质量任务，而不是逐条流水线审核。">
        <div className="flex flex-wrap gap-2">
          {Object.keys(tabs).map((key) => (
            <button key={key} onClick={() => setTab(key as keyof typeof tabs)} className={`rounded-full border px-3 py-2 text-sm transition ${tab === key ? "border-emerald-300/40 bg-emerald-300/10 text-white" : "border-white/10 bg-white/[0.04] text-slate-300"}`}>{key}</button>
          ))}
        </div>
        <div className="mt-4 space-y-3">
          {items.map((item: any) => ("task_id" in item ? renderTaskItem(item as ReviewTaskItem) : renderAnnotatorItem(item as ReviewAnnotatorItem)))}
          {!items.length ? <div className="rounded-[24px] border border-dashed border-white/10 bg-black/20 p-6 text-sm text-slate-400">当前集合为空。</div> : null}
        </div>
      </Panel>
      <div className="space-y-4">
        <Panel title="集合动作" subtitle="支持 dry-run 预览与正式执行。">
          <div className="space-y-4">
            <input value={action} onChange={(event) => setAction(event.target.value)} className="w-full rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 outline-none focus:border-emerald-300/40" placeholder="动作，例如 needs_rework / locked / approved" />
            <textarea value={reason} onChange={(event) => setReason(event.target.value)} rows={3} className="w-full rounded-[18px] border border-white/10 bg-white/[0.04] px-4 py-3 outline-none focus:border-emerald-300/40" placeholder="原因（可选）" />
            <div className="flex flex-wrap gap-3">
              <button onClick={() => applyMutation.mutate(true)} className="rounded-2xl border border-amber-300/30 bg-amber-300/10 px-4 py-3 text-sm text-amber-50">dry-run</button>
              <button onClick={() => applyMutation.mutate(false)} className="rounded-2xl border border-emerald-300/30 bg-emerald-300/15 px-4 py-3 text-sm text-white">正式执行</button>
              {isTaskTab ? (
                <button
                  onClick={() => bulkMutation.mutate()}
                  disabled={!selectedTaskIds.length}
                  className="rounded-2xl border border-white/10 bg-white/[0.05] px-4 py-3 text-sm text-slate-100 disabled:opacity-50"
                >
                  批量作用于已选 {selectedTaskIds.length}
                </button>
              ) : null}
            </div>
            {previewResult ? <pre className="overflow-x-auto rounded-[18px] border border-white/10 bg-black/20 p-4 font-mono-ui text-xs leading-6 text-slate-300">{previewResult}</pre> : null}
          </div>
        </Panel>
        <Panel title="审查日志" subtitle="记录 reviewer/admin 执行过的动作。">
          <div className="space-y-3">
            {(eventsQuery.data || []).map((event) => (
              <div key={event.id} className="rounded-[24px] border border-white/10 bg-black/20 p-4 text-sm text-slate-200">
                <p className="font-medium text-white">Task #{event.task_id} · {event.action}</p>
                <p className="mt-1 text-slate-400">reviewer #{event.reviewer_id} · {event.source_set || "manual"}</p>
              </div>
            ))}
          </div>
        </Panel>
      </div>
    </div>
  );
}
