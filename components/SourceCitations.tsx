"use client";

import { useState } from "react";
import { ChevronDown, FileText } from "lucide-react";
import type { SourceRef } from "@/lib/types";

export function SourceCitations({ sources }: { sources: SourceRef[] }) {
  const [open, setOpen] = useState(false);
  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-3 rounded-xl border border-white/10 bg-white/[0.03]">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-2 px-3.5 py-2.5 text-left text-xs font-medium text-slate-300 hover:text-slate-100"
      >
        <span className="flex items-center gap-1.5">
          <FileText size={13} className="text-accent-400" />
          {sources.length} source{sources.length > 1 ? "s" : ""} citée{sources.length > 1 ? "s" : ""}
        </span>
        <ChevronDown
          size={14}
          className={`transition-transform duration-200 ${open ? "rotate-180" : ""}`}
        />
      </button>
      {open && (
        <div className="space-y-2 border-t border-white/10 px-3.5 py-3">
          {sources.map((s, i) => (
            <div key={i} className="rounded-lg bg-black/20 p-2.5 text-xs">
              <div className="mb-1 flex items-center justify-between font-medium text-slate-300">
                <span>
                  {s.docName}
                  {s.page ? `, page ${s.page}` : ""}
                </span>
                <span className="text-[10px] text-slate-500">sim. {s.score.toFixed(2)}</span>
              </div>
              <p className="line-clamp-3 text-slate-500">{s.text}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
