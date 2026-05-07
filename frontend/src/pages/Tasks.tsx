import { Search, SlidersHorizontal } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { Panel } from "@/components/common/Panel";
import { api } from "@/lib/api";
import { formatPercent, truncate } from "@/lib/format";
import { parseTaskImportFile } from "@/lib/taskImport";

export default function TasksPage() {
  const queryClient = useQueryClient();
  const [prompt, setPrompt] = useState("");
  const [category, setCategory] = useState("");
  const [selectedModels, setSelectedModels] = useState<string[]>([]);
  const [bulkText, setBulkText] = useState("");
  const [importFile, setImportFile] = useState<File | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [selectedTaskId, setSelectedTaskId] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const modelsQuery = useQuery({ queryKey: ["models"], queryFn: api.models });
  const tasksQuery = useQuery({ queryKey: ["tasks"], queryFn: () => api.tasks("limit=50&offset=0") });

  const createMutation = useMutation({
    mutationFn: () => api.createTask({ prompt, category: category || undefined, model_ids: selectedModels }),
    onSuccess: () => {
      toast.success("任务已创建");
      setPrompt("");
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const importMutation = useMutation({
    mutationFn: () => {
      const lines = bulkText.split(/\n+/).map((line) => line.trim()).filter(Boolean);
      return api.importTasks({ tasks: lines.map((line) => ({ prompt: line, category: category || undefined, model_ids: selectedModels })) });
    },
    onSuccess: () => {
      toast.success("批量导入完成");
      setBulkText("");
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const fileImportMutation = useMutation({
    mutationFn: async () => {
      if (!importFile) {
        throw new Error("请先选择一个 .jsonl 或 .txt 文件");
      }
      const text = await importFile.text();
      const tasks = parseTaskImportFile({
        fileName: importFile.name,
        text,
        selectedModels,
        category: category || undefined,
      });
      return api.importTasks({ tasks });
    },
    onSuccess: () => {
      toast.success("文件导入完成");
      setImportFile(null);
      if (fileInputRef.current) fileInputRef.current.value = "";
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const metrics = useMemo(() => {
    const tasks = tasksQuery.data || [];
    const completed = tasks.filter((task) => task.status === "completed").length;
    const dropped = tasks.filter((task) => task.status === "dropped").length;
    return { total: tasks.length, completed, dropped };
  }, [tasksQuery.data]);

  const filteredTasks = useMemo(() => {
    return (tasksQuery.data || []).filter((task) => {
      if (statusFilter !== "all" && task.status !== statusFilter) return false;
      if (category && (task.category || "").toLowerCase() !== category.toLowerCase()) return false;
      if (search && !task.prompt.toLowerCase().includes(search.toLowerCase())) return false;
      return true;
    });
  }, [tasksQuery.data, statusFilter, category, search]);

  const selectedTask = useMemo(
    () => filteredTasks.find((task) => task.id === selectedTaskId) || filteredTasks[0] || null,
    [filteredTasks, selectedTaskId],
  );

  return (
    <div className="space-y-4">
      <div className="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <Panel title="创建任务" subtitle="输入 Prompt，选择至少两个模型，立即生成回复。">
          <div className="space-y-4">
            <textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} rows={6} className="w-full rounded-[24px] border border-white/10 bg-black/20 px-4 py-4 outline-none focus:border-emerald-300/40" placeholder="输入一条新的 prompt" />
            <div className="grid gap-4 md:grid-cols-[1fr_1fr]">
              <input value={category} onChange={(event) => setCategory(event.target.value)} className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 outline-none focus:border-emerald-300/40" placeholder="分类（可选）" />
              <div className="rounded-2xl border border-white/10 bg-black/20 p-3 text-sm text-slate-300">至少选择 2 个模型，前端只负责选择，密钥仍留在后端。</div>
            </div>
            <div className="flex flex-wrap gap-2">
              {(modelsQuery.data || []).map((model) => {
                const active = selectedModels.includes(model.id);
                return (
                  <button key={model.id} onClick={() => setSelectedModels((prev) => active ? prev.filter((item) => item !== model.id) : [...prev, model.id])} className={`rounded-full border px-3 py-2 text-sm transition ${active ? "border-emerald-300/40 bg-emerald-300/10 text-white" : "border-white/10 bg-white/[0.04] text-slate-300"}`}>{model.name}</button>
                );
              })}
            </div>
            <button onClick={() => createMutation.mutate()} disabled={createMutation.isPending || selectedModels.length < 2 || !prompt} className="rounded-2xl border border-emerald-300/30 bg-emerald-300/15 px-4 py-3 text-white transition hover:bg-emerald-300/20 disabled:opacity-50">{createMutation.isPending ? "生成中..." : "创建并生成"}</button>
          </div>
        </Panel>
        <Panel title="批量导入与概览" subtitle="适合一次性创建多条 prompt。">
          <div className="grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
            <div className="space-y-4">
              <textarea value={bulkText} onChange={(event) => setBulkText(event.target.value)} rows={10} className="w-full rounded-[24px] border border-white/10 bg-black/20 px-4 py-4 outline-none focus:border-emerald-300/40" placeholder="每行一条 prompt" />
              <button onClick={() => importMutation.mutate()} disabled={importMutation.isPending || selectedModels.length < 2 || !bulkText.trim()} className="rounded-2xl border border-amber-300/30 bg-amber-300/10 px-4 py-3 text-amber-50 transition hover:bg-amber-300/15 disabled:opacity-50">{importMutation.isPending ? "导入中..." : "批量导入"}</button>
              <div className="rounded-[24px] border border-white/10 bg-black/20 p-4 text-sm text-slate-300">
                <p className="font-medium text-white">文件导入</p>
                <p className="mt-2 text-slate-400">支持 `.txt` 和 `.jsonl`。TXT 按每行一个问题导入，使用当前已选模型；JSONL 每行必须带 `model` 和 `prompt`、`user_prompt` 或 `content` 字段。</p>
                <input ref={fileInputRef} type="file" accept=".txt,.jsonl" onChange={(event) => setImportFile(event.target.files?.[0] || null)} className="mt-4 block w-full rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-slate-300 file:mr-3 file:rounded-xl file:border-0 file:bg-emerald-300/15 file:px-3 file:py-2 file:text-sm file:text-white" />
                <div className="mt-3 rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-xs leading-6 text-slate-400">
                  <p>TXT: 每行一条 prompt，例如 `请写一段产品介绍`。</p>
                  <p>JSONL: `{"{"}"user_prompt":"问题","model":["kimi-k2.6","mimo-v2.5-pro"]{"}"}`</p>
                </div>
                <button onClick={() => fileImportMutation.mutate()} disabled={fileImportMutation.isPending || !importFile} className="mt-4 rounded-2xl border border-cyan-300/30 bg-cyan-300/10 px-4 py-3 text-cyan-50 transition hover:bg-cyan-300/15 disabled:opacity-50">{fileImportMutation.isPending ? "文件导入中..." : "导入文件"}</button>
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-3">
              <div className="rounded-[24px] border border-white/10 bg-black/20 p-4"><p className="text-xs uppercase tracking-[0.24em] text-slate-500">总数</p><p className="mt-3 font-display text-3xl text-white">{metrics.total}</p></div>
              <div className="rounded-[24px] border border-white/10 bg-black/20 p-4"><p className="text-xs uppercase tracking-[0.24em] text-slate-500">完成</p><p className="mt-3 font-display text-3xl text-white">{metrics.completed}</p></div>
              <div className="rounded-[24px] border border-white/10 bg-black/20 p-4"><p className="text-xs uppercase tracking-[0.24em] text-slate-500">Dropped</p><p className="mt-3 font-display text-3xl text-white">{metrics.dropped}</p></div>
            </div>
          </div>
        </Panel>
      </div>
      <Panel title="任务列表" subtitle="显示任务状态、响应数、标注数与 Kappa。">
        <div className="mb-4 grid gap-3 rounded-[24px] border border-white/10 bg-black/20 p-4 lg:grid-cols-[1.2fr_180px_180px]">
          <label className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-slate-400">
            <Search size={16} />
            <input value={search} onChange={(event) => setSearch(event.target.value)} className="w-full bg-transparent outline-none" placeholder="搜索 prompt 文本" />
          </label>
          <label className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-slate-400">
            <SlidersHorizontal size={16} />
            <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} className="w-full bg-transparent text-slate-200 outline-none">
              <option value="all">全部状态</option>
              <option value="pending">pending</option>
              <option value="annotating">annotating</option>
              <option value="completed">completed</option>
              <option value="dropped">dropped</option>
            </select>
          </label>
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm text-slate-400">
            命中 {filteredTasks.length} / {metrics.total}
          </div>
        </div>
        <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="space-y-3">
            {filteredTasks.map((task) => (
              <button
                key={task.id}
                onClick={() => setSelectedTaskId(task.id)}
                className={`grid w-full gap-3 rounded-[24px] border p-4 text-left transition lg:grid-cols-[minmax(0,1fr)_140px_140px_140px] lg:items-center ${selectedTask?.id === task.id ? "border-emerald-300/30 bg-emerald-300/10" : "border-white/10 bg-black/20 hover:bg-white/[0.05]"}`}
              >
                <div>
                  <p className="text-sm text-white">{truncate(task.prompt, 120)}</p>
                  <p className="mt-2 text-xs uppercase tracking-[0.22em] text-slate-500">#{task.id} · {task.category || "uncategorized"}</p>
                </div>
                <div className="text-sm text-slate-300">状态：{task.status}</div>
                <div className="text-sm text-slate-300">响应/标注：{task.response_count || 0}/{task.annotation_count || 0}</div>
                <div className="text-sm text-slate-300">Kappa：{task.kappa === null || task.kappa === undefined ? "--" : formatPercent(task.kappa)}</div>
              </button>
            ))}
            {!filteredTasks.length ? <div className="rounded-[24px] border border-dashed border-white/10 bg-black/20 p-6 text-sm text-slate-400">当前筛选条件下没有任务。</div> : null}
          </div>
          <div className="rounded-[24px] border border-white/10 bg-black/20 p-5">
            {selectedTask ? (
              <div className="space-y-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Task #{selectedTask.id}</p>
                  <p className="mt-3 text-sm leading-7 text-white">{selectedTask.prompt}</p>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-2xl border border-white/10 px-4 py-3 text-sm text-slate-300">状态：{selectedTask.status}</div>
                  <div className="rounded-2xl border border-white/10 px-4 py-3 text-sm text-slate-300">分类：{selectedTask.category || "uncategorized"}</div>
                  <div className="rounded-2xl border border-white/10 px-4 py-3 text-sm text-slate-300">标注数：{selectedTask.annotation_count || 0}</div>
                  <div className="rounded-2xl border border-white/10 px-4 py-3 text-sm text-slate-300">Kappa：{selectedTask.kappa === null || selectedTask.kappa === undefined ? "--" : formatPercent(selectedTask.kappa)}</div>
                </div>
                <div className="space-y-3">
                  <p className="text-xs uppercase tracking-[0.22em] text-slate-500">模型回复</p>
                  {selectedTask.responses.map((response) => (
                    <div key={response.id} className="rounded-[20px] border border-white/10 bg-white/[0.03] p-4">
                      <p className="text-xs uppercase tracking-[0.18em] text-emerald-300/80">{response.model_id}</p>
                      <p className="mt-2 text-sm leading-7 text-slate-200">{truncate(response.content, 260)}</p>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="rounded-[24px] border border-dashed border-white/10 p-6 text-sm text-slate-400">选择一条任务即可查看详情。</div>
            )}
          </div>
        </div>
      </Panel>
    </div>
  );
}
