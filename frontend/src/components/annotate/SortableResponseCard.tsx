import { CSS } from "@dnd-kit/utilities";
import { useSortable } from "@dnd-kit/sortable";
import { GripVertical, PencilLine, RotateCcw, Star } from "lucide-react";
import { cn } from "@/lib/utils";

export type EditableResponse = {
  id: number;
  model_id: string;
  content: string;
  score?: number;
  edit?: string;
  group?: number;
};

export function SortableResponseCard({
  item,
  index,
  onScore,
  onEdit,
  onGroupChange,
}: {
  item: EditableResponse;
  index: number;
  onScore: (id: number, score: number) => void;
  onEdit: (id: number, value: string | undefined) => void;
  onGroupChange: (id: number, group: number) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: item.id });
  const style = { transform: CSS.Transform.toString(transform), transition };
  const score = item.score || 0;
  return (
    <div ref={setNodeRef} style={style} className="panel-surface rounded-[24px] p-4">
      <div className="flex items-start gap-4">
        <button className="mt-1 rounded-xl border border-white/10 bg-white/5 p-2 text-slate-300" {...attributes} {...listeners}>
          <GripVertical size={18} />
        </button>
        <div className="flex-1 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.22em] text-emerald-300/80">#{index + 1} · {item.model_id}</p>
              <p className="mt-1 text-sm text-slate-400">拖拽排序、独立打分、可编辑快照</p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <label className="flex items-center gap-2 rounded-full border border-white/10 px-3 py-2 text-xs uppercase tracking-[0.16em] text-slate-400">
                并列组
                <input
                  type="number"
                  min={1}
                  value={(item.group ?? index) + 1}
                  onChange={(event) => onGroupChange(item.id, Math.max(0, Number(event.target.value || 1) - 1))}
                  className="w-16 bg-transparent text-right text-slate-200 outline-none"
                />
              </label>
              <div className="flex items-center gap-1 rounded-full border border-white/10 px-3 py-2">
              {Array.from({ length: 5 }).map((_, starIndex) => {
                const current = starIndex + 1;
                return (
                  <button key={current} onClick={() => onScore(item.id, current)} className={cn("rounded-full p-1 transition", current <= score ? "text-amber-300" : "text-slate-600 hover:text-slate-300") }>
                    <Star size={16} fill={current <= score ? "currentColor" : "none"} />
                  </button>
                );
              })}
              </div>
            </div>
          </div>
          <div className="rounded-[20px] border border-white/10 bg-black/20 p-4 text-sm leading-7 text-slate-100">{item.content}</div>
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-slate-500"><PencilLine size={14} /> 编辑快照</div>
            <textarea value={item.edit || ""} onChange={(event) => onEdit(item.id, event.target.value || undefined)} rows={4} className="w-full rounded-[18px] border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-slate-100 outline-none ring-0 transition focus:border-emerald-300/40" placeholder="留空表示使用原始内容" />
            {item.edit ? (
              <button onClick={() => onEdit(item.id, undefined)} className="inline-flex items-center gap-2 text-xs text-slate-400 transition hover:text-white"><RotateCcw size={14} />恢复原文</button>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
