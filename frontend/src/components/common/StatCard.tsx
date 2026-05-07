export function StatCard({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="panel-surface rounded-[24px] p-5">
      <p className="text-xs uppercase tracking-[0.28em] text-slate-500">{label}</p>
      <div className="mt-3 flex items-end justify-between gap-4">
        <p className="font-display text-3xl text-white">{value}</p>
        {hint ? <p className="max-w-[120px] text-right text-xs text-slate-400">{hint}</p> : null}
      </div>
    </div>
  );
}
