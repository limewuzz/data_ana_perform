import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Panel({ title, subtitle, children, className }: { title?: string; subtitle?: string; children: ReactNode; className?: string }) {
  return (
    <section className={cn("panel-surface rounded-[28px] p-5", className)}>
      {(title || subtitle) && (
        <header className="mb-4 flex items-start justify-between gap-3 border-b border-white/10 pb-4">
          <div>
            {title ? <h2 className="font-display text-lg text-white">{title}</h2> : null}
            {subtitle ? <p className="mt-1 text-sm text-slate-400">{subtitle}</p> : null}
          </div>
        </header>
      )}
      {children}
    </section>
  );
}
