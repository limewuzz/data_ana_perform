import { DndContext, PointerSensor, closestCenter, useSensor, useSensors } from "@dnd-kit/core";
import { SortableContext, arrayMove, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { SortableResponseCard, type EditableResponse } from "@/components/annotate/SortableResponseCard";
import { Panel } from "@/components/common/Panel";
import { api, type Task } from "@/lib/api";
import { buildRankingGroups } from "@/lib/annotate";
import { formatDuration } from "@/lib/format";

export default function AnnotatePage() {
  const queryClient = useQueryClient();
  const sensors = useSensors(useSensor(PointerSensor));
  const progressQuery = useQuery({ queryKey: ["queue-progress"], queryFn: api.queueProgress });
  const historyQuery = useQuery({ queryKey: ["queue-history"], queryFn: api.queueHistory });
  const [task, setTask] = useState<Task | null>(null);
  const [items, setItems] = useState<EditableResponse[]>([]);
  const [dropReason, setDropReason] = useState("");
  const [startedAt, setStartedAt] = useState<number | null>(null);

  const nextMutation = useMutation({
    mutationFn: async () => {
      const response = await api.nextTask({ include_needs_rework: true, skip_recent_claim_window_minutes: 1, limit: 20 });
      if (response.task) await api.claimTask(response.task.id);
      return response.task || null;
    },
    onSuccess: (nextTask) => {
      setTask(nextTask);
      setItems((nextTask?.responses || []).map((response, index) => ({ ...response, group: index })));
      setDropReason("");
      setStartedAt(nextTask ? Date.now() : null);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  useEffect(() => {
    nextMutation.mutate();
  }, []);

  const submitMutation = useMutation({
    mutationFn: async (isDropped: boolean) => {
      if (!task) return;
      const duration = startedAt ? Date.now() - startedAt : undefined;
      const scores = Object.fromEntries(items.filter((item) => item.score).map((item) => [String(item.id), item.score as number]));
      const edits = Object.fromEntries(items.filter((item) => item.edit).map((item) => [String(item.id), item.edit as string]));
      await api.createAnnotation({
        task_id: task.id,
        ranking: items.map((item) => item.id),
        ranking_groups: buildRankingGroups(items),
        scores,
        edits,
        is_dropped: isDropped,
        drop_reason: isDropped ? dropReason || "其他" : undefined,
        duration_ms: duration,
      });
      await api.completeTask(task.id);
    },
    onSuccess: async () => {
      toast.success("标注已提交");
      await queryClient.invalidateQueries({ queryKey: ["queue-progress"] });
      await queryClient.invalidateQueries({ queryKey: ["queue-history"] });
      nextMutation.mutate();
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const durationPreview = useMemo(() => (startedAt ? formatDuration(Date.now() - startedAt) : "--"), [startedAt, items]);

  return (
    <div className="space-y-4">
      <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <Panel title="标注导航" subtitle="队列领取、进度回看与 Drop 提交。">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-[24px] border border-white/10 bg-black/20 p-4"><p className="text-xs uppercase tracking-[0.22em] text-slate-500">总任务</p><p className="mt-3 font-display text-3xl text-white">{progressQuery.data?.total_tasks ?? "--"}</p></div>
            <div className="rounded-[24px] border border-white/10 bg-black/20 p-4"><p className="text-xs uppercase tracking-[0.22em] text-slate-500">已标注</p><p className="mt-3 font-display text-3xl text-white">{progressQuery.data?.annotated_tasks ?? "--"}</p></div>
            <div className="rounded-[24px] border border-white/10 bg-black/20 p-4"><p className="text-xs uppercase tracking-[0.22em] text-slate-500">耗时预览</p><p className="mt-3 font-display text-3xl text-white">{durationPreview}</p></div>
          </div>
          <div className="mt-4 rounded-[24px] border border-white/10 bg-black/20 p-4">
            <div className="flex flex-wrap gap-3">
              <button onClick={() => nextMutation.mutate()} className="rounded-2xl border border-white/10 px-4 py-3 text-sm text-slate-200 transition hover:bg-white/[0.06]">加载下一条</button>
              <button onClick={() => submitMutation.mutate(false)} disabled={!task || submitMutation.isPending} className="rounded-2xl border border-emerald-300/30 bg-emerald-300/15 px-4 py-3 text-sm text-white disabled:opacity-50">提交标注</button>
              <button onClick={() => submitMutation.mutate(true)} disabled={!task || submitMutation.isPending} className="rounded-2xl border border-red-400/20 bg-red-500/10 px-4 py-3 text-sm text-red-100 disabled:opacity-50">Drop 当前任务</button>
            </div>
            <textarea value={dropReason} onChange={(event) => setDropReason(event.target.value)} rows={3} className="mt-4 w-full rounded-[18px] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm outline-none focus:border-red-300/30" placeholder="Drop 原因：Prompt 问题 / 所有回复太差 / 过于相似 / 其他" />
          </div>
          <div className="mt-4 space-y-3">
            {(historyQuery.data?.items || []).map((item) => (
              <div key={`${item.task_id}-${item.created_at}`} className="rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-sm text-slate-300">Task #{item.task_id} · {new Date(item.created_at).toLocaleString()}</div>
            ))}
          </div>
        </Panel>
        <Panel title="标注工作区" subtitle="支持拖拽排序、打分和编辑快照。">
          {!task ? (
            <div className="rounded-[24px] border border-dashed border-white/10 bg-black/20 p-8 text-center text-slate-400">当前没有可领取任务。</div>
          ) : (
            <div className="space-y-4">
              <div className="rounded-[24px] border border-white/10 bg-black/20 p-5">
                <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Task #{task.id} · {task.category || "uncategorized"}</p>
                <p className="mt-3 text-sm leading-7 text-white">{task.prompt}</p>
                <p className="mt-4 text-xs text-slate-500">将相同“并列组”编号的回答视为同一名次；提交时会自动组装成 `ranking_groups`。</p>
              </div>
              <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={(event) => {
                const { active, over } = event;
                if (!over || active.id === over.id) return;
                const oldIndex = items.findIndex((item) => item.id === active.id);
                const newIndex = items.findIndex((item) => item.id === over.id);
                setItems((prev) => arrayMove(prev, oldIndex, newIndex));
              }}>
                <SortableContext items={items.map((item) => item.id)} strategy={verticalListSortingStrategy}>
                  <div className="space-y-4">
                    {items.map((item, index) => (
                      <SortableResponseCard
                        key={item.id}
                        item={item}
                        index={index}
                        onScore={(id, score) => setItems((prev) => prev.map((entry) => entry.id === id ? { ...entry, score } : entry))}
                        onEdit={(id, value) => setItems((prev) => prev.map((entry) => entry.id === id ? { ...entry, edit: value } : entry))}
                        onGroupChange={(id, group) => setItems((prev) => prev.map((entry) => entry.id === id ? { ...entry, group } : entry))}
                      />
                    ))}
                  </div>
                </SortableContext>
              </DndContext>
            </div>
          )}
        </Panel>
      </div>
    </div>
  );
}
