import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";
import { Panel } from "@/components/common/Panel";
import { api, type Role } from "@/lib/api";

const roles: Role[] = ["annotator", "reviewer", "admin"];

export default function UserSettingsPage() {
  const queryClient = useQueryClient();
  const [drafts, setDrafts] = useState<Record<number, { name: string; role: Role }>>({});
  const usersQuery = useQuery({ queryKey: ["users"], queryFn: api.users });
  const mutation = useMutation({
    mutationFn: ({ id, role, name }: { id: number; role: Role; name?: string }) => api.updateUser(id, { role, name }),
    onSuccess: () => {
      toast.success("用户信息已更新");
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (error: Error) => toast.error(error.message),
  });
  return (
    <Panel title="用户与角色管理" subtitle="管理员可直接调整角色。">
      <div className="space-y-3">
        {(usersQuery.data || []).map((user) => (
          <div key={user.id} className="grid gap-3 rounded-[24px] border border-white/10 bg-black/20 p-4 lg:grid-cols-[1fr_180px_auto] lg:items-center">
            <div>
              <input
                value={drafts[user.id]?.name ?? user.name ?? ""}
                onChange={(event) => setDrafts((prev) => ({ ...prev, [user.id]: { name: event.target.value, role: prev[user.id]?.role ?? user.role } }))}
                className="w-full rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2 font-medium text-white"
                placeholder={user.email}
              />
              <p className="mt-1 text-sm text-slate-400">{user.email}</p>
            </div>
            <select value={drafts[user.id]?.role ?? user.role} onChange={(event) => setDrafts((prev) => ({ ...prev, [user.id]: { name: prev[user.id]?.name ?? user.name ?? "", role: event.target.value as Role } }))} className="rounded-2xl border border-white/10 bg-white/[0.04] px-4 py-3 text-sm">
              {roles.map((role) => <option key={role} value={role}>{role}</option>)}
            </select>
            <button
              onClick={() => mutation.mutate({ id: user.id, role: drafts[user.id]?.role ?? user.role, name: drafts[user.id]?.name ?? user.name ?? "" })}
              className="rounded-2xl border border-emerald-300/30 bg-emerald-300/15 px-4 py-3 text-sm text-white"
            >
              保存
            </button>
          </div>
        ))}
      </div>
    </Panel>
  );
}
