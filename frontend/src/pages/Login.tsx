import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Panel } from "@/components/common/Panel";
import { useSessionStore } from "@/store/session";

export default function LoginPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [form, setForm] = useState({ email: "", password: "", name: "" });
  const navigate = useNavigate();
  const setToken = useSessionStore((state) => state.setToken);
  const setUser = useSessionStore((state) => state.setUser);

  const authMutation = useMutation({
    mutationFn: async () => {
      const payload = mode === "login"
        ? await api.login({ email: form.email, password: form.password })
        : await api.register({ email: form.email, password: form.password, name: form.name || undefined, role: "annotator" });
      setToken(payload.access_token);
      const me = await api.me();
      setUser(me);
      return me;
    },
    onSuccess: () => {
      toast.success(mode === "login" ? "登录成功" : "注册成功");
      navigate("/");
    },
    onError: (error: Error) => toast.error(error.message || "认证失败"),
  });

  return (
    <div className="flex min-h-screen items-center justify-center px-4 py-10">
      <div className="grid w-full max-w-6xl gap-5 lg:grid-cols-[1.2fr_0.8fr]">
        <section className="panel-surface relative overflow-hidden rounded-[36px] p-8 lg:p-10">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(72,255,199,0.18),transparent_26%),radial-gradient(circle_at_bottom_left,rgba(255,184,76,0.14),transparent_20%)]" />
          <div className="relative">
            <p className="text-xs uppercase tracking-[0.3em] text-emerald-300/90">Preference Workbench</p>
            <h1 className="mt-4 max-w-2xl font-display text-4xl leading-tight text-white lg:text-6xl">把偏好数据生产流程压进一张高密度控制台。</h1>
            <p className="mt-5 max-w-xl text-sm leading-7 text-slate-300 lg:text-base">多模型生成、Listwise 标注、审查集合、质量看板和导出中心统一收束在同一套深色实验台界面里，适合演示也适合真实操作。</p>
            <div className="mt-10 grid gap-4 md:grid-cols-3">
              {[
                ["多模型生成", "前端展示模型选择，后端统一代理调用"],
                ["审核集合", "低 Kappa、低区分度、异常标注者集中处理"],
                ["导出中心", "DPO / Alpaca / JSONL / CSV 一键切换"],
              ].map(([title, desc]) => (
                <div key={title} className="rounded-[24px] border border-white/10 bg-black/20 p-4">
                  <p className="font-display text-lg text-white">{title}</p>
                  <p className="mt-2 text-sm leading-6 text-slate-400">{desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
        <Panel title={mode === "login" ? "登录控制台" : "创建账号"} subtitle="默认注册为 annotator，管理员可在系统设置里调整角色。" className="rounded-[36px] p-8">
          <div className="mb-5 grid grid-cols-2 rounded-2xl border border-white/10 bg-black/20 p-1">
            {(["login", "register"] as const).map((key) => (
              <button key={key} onClick={() => setMode(key)} className={`rounded-xl px-4 py-3 text-sm transition ${mode === key ? "bg-emerald-300/15 text-white" : "text-slate-400"}`}>{key === "login" ? "登录" : "注册"}</button>
            ))}
          </div>
          <div className="space-y-4">
            {mode === "register" ? <input value={form.name} onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))} className="w-full rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 outline-none focus:border-emerald-300/40" placeholder="姓名（可选）" /> : null}
            <input value={form.email} onChange={(event) => setForm((prev) => ({ ...prev, email: event.target.value }))} className="w-full rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 outline-none focus:border-emerald-300/40" placeholder="邮箱" />
            <input type="password" value={form.password} onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))} className="w-full rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 outline-none focus:border-emerald-300/40" placeholder="密码" />
            <button onClick={() => authMutation.mutate()} disabled={authMutation.isPending} className="w-full rounded-2xl border border-emerald-300/30 bg-emerald-300/15 px-4 py-3 font-medium text-white transition hover:bg-emerald-300/20 disabled:opacity-60">
              {authMutation.isPending ? "处理中..." : mode === "login" ? "登录并进入工作台" : "注册并进入工作台"}
            </button>
          </div>
        </Panel>
      </div>
    </div>
  );
}
