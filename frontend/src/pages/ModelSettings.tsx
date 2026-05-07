import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { Panel } from "@/components/common/Panel";
import { api } from "@/lib/api";

export default function ModelSettingsPage() {
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState({ model_id: "", name: "", provider: "mock", base_url: "", api_key_env: "", system_prompt: "", params: "{}" });
  const configsQuery = useQuery({ queryKey: ["model-configs"], queryFn: api.modelConfigs });
  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        ...form,
        enabled: true,
        base_url: form.base_url || undefined,
        api_key_env: form.api_key_env || undefined,
        system_prompt: form.system_prompt || undefined,
        params: form.params.trim() ? JSON.parse(form.params) : undefined,
      };
      if (editingId) {
        return api.updateModelConfig(editingId, payload);
      }
      return api.createModelConfig(payload);
    },
    onSuccess: () => {
      toast.success(editingId ? "模型配置已更新" : "模型配置已创建");
      setEditingId(null);
      setForm({ model_id: "", name: "", provider: "mock", base_url: "", api_key_env: "", system_prompt: "", params: "{}" });
      queryClient.invalidateQueries({ queryKey: ["model-configs"] });
    },
    onError: (error: Error) => toast.error(error.message),
  });
  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteModelConfig(id),
    onSuccess: () => {
      toast.success("模型配置已删除");
      queryClient.invalidateQueries({ queryKey: ["model-configs"] });
      if (editingId) {
        setEditingId(null);
      }
    },
    onError: (error: Error) => toast.error(error.message),
  });

  return (
    <div className="grid gap-4 xl:grid-cols-[0.8fr_1.2fr]">
      <Panel title={editingId ? "编辑模型配置" : "新增模型配置"} subtitle="管理员在此维护 provider 和调用参数。">
        <div className="space-y-4">
          {([["model_id", "模型 ID"], ["name", "显示名称"], ["provider", "provider"], ["base_url", "base_url"], ["api_key_env", "api_key_env"], ["system_prompt", "system_prompt"]] as const).map(([key, label]) => (
            key === "system_prompt" ? <textarea key={key} value={form[key]} onChange={(event) => setForm((prev) => ({ ...prev, [key]: event.target.value }))} rows={4} className="w-full rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3" placeholder={label} /> : <input key={key} value={form[key]} disabled={key === "model_id" && !!editingId} onChange={(event) => setForm((prev) => ({ ...prev, [key]: event.target.value }))} className="w-full rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 disabled:opacity-50" placeholder={label} />
          ))}
          <textarea value={form.params} onChange={(event) => setForm((prev) => ({ ...prev, params: event.target.value }))} rows={4} className="w-full rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 font-mono-ui text-sm" placeholder='params JSON，例如 {"temperature":0.7}' />
          <div className="flex flex-wrap gap-3">
            <button onClick={() => saveMutation.mutate()} className="rounded-2xl border border-emerald-300/30 bg-emerald-300/15 px-4 py-3 text-white">{editingId ? "保存修改" : "创建模型"}</button>
            {editingId ? <button onClick={() => { setEditingId(null); setForm({ model_id: "", name: "", provider: "mock", base_url: "", api_key_env: "", system_prompt: "", params: "{}" }); }} className="rounded-2xl border border-white/10 px-4 py-3 text-slate-200">取消编辑</button> : null}
          </div>
        </div>
      </Panel>
      <Panel title="模型列表" subtitle="展示当前后端可管理的模型配置。">
        <div className="space-y-3">
          {(configsQuery.data || []).map((item) => (
            <div key={item.id} className="rounded-[24px] border border-white/10 bg-black/20 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="font-medium text-white">{item.name}</p>
                  <p className="mt-1 text-sm text-slate-400">{item.model_id} · {item.provider} · {item.enabled ? "enabled" : "disabled"}</p>
                  {item.system_prompt ? <p className="mt-2 text-xs leading-6 text-slate-500">{item.system_prompt.slice(0, 120)}</p> : null}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      setEditingId(item.id);
                      setForm({
                        model_id: item.model_id,
                        name: item.name,
                        provider: item.provider,
                        base_url: item.base_url || "",
                        api_key_env: item.api_key_env || "",
                        system_prompt: item.system_prompt || "",
                        params: JSON.stringify(item.params || {}, null, 2),
                      });
                    }}
                    className="rounded-xl border border-white/10 px-3 py-2 text-sm text-slate-200"
                  >
                    编辑
                  </button>
                  <button onClick={() => deleteMutation.mutate(item.id)} className="rounded-xl border border-red-400/20 bg-red-500/10 px-3 py-2 text-sm text-red-100">删除</button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}
