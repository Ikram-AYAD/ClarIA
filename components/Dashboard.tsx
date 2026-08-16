"use client";

import { motion } from "framer-motion";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { BarChart3, Clock, Gauge, MessagesSquare } from "lucide-react";
import type { QueryLogEntry } from "@/lib/types";
import { aggregateUsageStats } from "@/lib/analytics";

const CONFIDENCE_COLORS: Record<string, string> = {
  Forte: "#2dd4bf",
  Moyenne: "#fbbf24",
  Faible: "#fb923c",
  "Aucune source": "#475569",
};

function StatCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="glass rounded-2xl p-4">
      <div className="mb-2 flex h-8 w-8 items-center justify-center rounded-lg bg-accent-500/15 text-accent-300">
        {icon}
      </div>
      <p className="text-xl font-semibold text-slate-50">{value}</p>
      <p className="mt-0.5 text-xs text-slate-500">{label}</p>
    </div>
  );
}

export function Dashboard({ queryLog }: { queryLog: QueryLogEntry[] }) {
  if (queryLog.length === 0) {
    return (
      <div className="flex h-full items-center justify-center px-8 text-center">
        <div>
          <BarChart3 size={28} className="mx-auto mb-3 text-slate-600" />
          <p className="text-sm text-slate-500">
            Pose au moins une question dans l&rsquo;onglet Chat pour voir apparaître des
            statistiques ici.
          </p>
        </div>
      </div>
    );
  }

  const stats = aggregateUsageStats(queryLog);
  const confidenceData = Object.entries(stats.confidenceDistribution)
    .filter(([, v]) => v > 0)
    .map(([label, value]) => ({ name: label, value }));
  const docData = stats.mostConsultedDocuments.map(([name, value]) => ({ name, value }));

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="h-full overflow-y-auto px-6 py-6 md:px-10"
    >
      <div className="mx-auto max-w-5xl space-y-6">
        <div>
          <h2 className="text-lg font-semibold text-slate-50">Tableau de bord d&rsquo;usage</h2>
          <p className="text-sm text-slate-500">Statistiques calculées en temps réel, en local.</p>
        </div>

        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <StatCard icon={<MessagesSquare size={16} />} label="Questions posées" value={String(stats.totalQuestions)} />
          <StatCard
            icon={<Gauge size={16} />}
            label="Réponses sourcées"
            value={`${Math.round(stats.answeredRate * 100)} %`}
          />
          <StatCard
            icon={<Clock size={16} />}
            label="Temps de réponse moyen"
            value={`${stats.avgResponseTimeSeconds.toFixed(1)} s`}
          />
          <StatCard
            icon={<BarChart3 size={16} />}
            label="Confiance moyenne"
            value={stats.avgConfidenceScore.toFixed(2)}
          />
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <div className="glass rounded-2xl p-4">
            <h3 className="mb-3 text-sm font-medium text-slate-300">
              Répartition de la confiance des réponses
            </h3>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={confidenceData}
                  dataKey="value"
                  nameKey="name"
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={3}
                >
                  {confidenceData.map((entry) => (
                    <Cell key={entry.name} fill={CONFIDENCE_COLORS[entry.name] ?? "#6c7bff"} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: "#0e111c",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: 10,
                    fontSize: 12,
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="mt-2 flex flex-wrap justify-center gap-3">
              {confidenceData.map((d) => (
                <span key={d.name} className="flex items-center gap-1.5 text-[11px] text-slate-400">
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ background: CONFIDENCE_COLORS[d.name] ?? "#6c7bff" }}
                  />
                  {d.name} ({d.value})
                </span>
              ))}
            </div>
          </div>

          <div className="glass rounded-2xl p-4">
            <h3 className="mb-3 text-sm font-medium text-slate-300">Documents les plus consultés</h3>
            {docData.length === 0 ? (
              <p className="py-10 text-center text-xs text-slate-600">Aucun document cité pour l&rsquo;instant.</p>
            ) : (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={docData} layout="vertical" margin={{ left: 8, right: 16 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" horizontal={false} />
                  <XAxis type="number" tick={{ fill: "#64748b", fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={110}
                    tick={{ fill: "#94a3b8", fontSize: 11 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#0e111c",
                      border: "1px solid rgba(255,255,255,0.1)",
                      borderRadius: 10,
                      fontSize: 12,
                    }}
                  />
                  <Bar dataKey="value" radius={[0, 6, 6, 0]} fill="#6c7bff" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="glass overflow-hidden rounded-2xl">
          <h3 className="border-b border-white/8 px-4 py-3 text-sm font-medium text-slate-300">
            Historique détaillé des questions
          </h3>
          <div className="max-h-80 overflow-y-auto">
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 bg-ink-900/95 text-slate-500">
                <tr>
                  <th className="px-4 py-2 font-medium">Question</th>
                  <th className="px-4 py-2 font-medium">Confiance</th>
                  <th className="px-4 py-2 font-medium">Temps</th>
                  <th className="px-4 py-2 font-medium">Mode</th>
                </tr>
              </thead>
              <tbody>
                {[...queryLog].reverse().map((e) => (
                  <tr key={e.id} className="border-t border-white/5 text-slate-400">
                    <td className="max-w-xs truncate px-4 py-2">{e.question}</td>
                    <td className="px-4 py-2">{e.confidence.label}</td>
                    <td className="px-4 py-2">{e.responseTimeSeconds.toFixed(1)}s</td>
                    <td className="px-4 py-2">{e.searchMode}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
