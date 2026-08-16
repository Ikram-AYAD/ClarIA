import clsx from "clsx";
import type { Confidence } from "@/lib/types";

const STYLES: Record<Confidence["label"], string> = {
  Forte: "bg-mint-500/15 text-mint-400 border-mint-500/30",
  Moyenne: "bg-amber-500/15 text-amber-300 border-amber-500/30",
  Faible: "bg-orange-500/15 text-orange-300 border-orange-500/30",
  "Aucune source": "bg-white/5 text-slate-400 border-white/10",
};

const DOTS: Record<Confidence["label"], string> = {
  Forte: "bg-mint-400",
  Moyenne: "bg-amber-300",
  Faible: "bg-orange-300",
  "Aucune source": "bg-slate-500",
};

export function ConfidenceBadge({ confidence }: { confidence: Confidence }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium",
        STYLES[confidence.label]
      )}
      title={`Score de confiance : ${confidence.score.toFixed(2)}`}
    >
      <span className={clsx("h-1.5 w-1.5 rounded-full", DOTS[confidence.label])} />
      Confiance {confidence.label.toLowerCase()}
    </span>
  );
}
