import type { QueryLogEntry } from "./types";

export interface UsageStats {
  totalQuestions: number;
  answeredRate: number;
  noInfoRate: number;
  avgResponseTimeSeconds: number;
  avgConfidenceScore: number;
  confidenceDistribution: Record<string, number>;
  mostConsultedDocuments: [string, number][];
  totalApiCalls: number;
  totalTokensEstimate: number;
}

function estimateTokens(text: string): number {
  // Approximation grossière (≈ 4 caractères par token), suffisante pour un
  // tableau de bord indicatif.
  return Math.ceil(text.length / 4);
}

export function aggregateUsageStats(entries: QueryLogEntry[]): UsageStats {
  if (entries.length === 0) {
    return {
      totalQuestions: 0,
      answeredRate: 0,
      noInfoRate: 0,
      avgResponseTimeSeconds: 0,
      avgConfidenceScore: 0,
      confidenceDistribution: { Forte: 0, Moyenne: 0, Faible: 0, "Aucune source": 0 },
      mostConsultedDocuments: [],
      totalApiCalls: 0,
      totalTokensEstimate: 0,
    };
  }

  const answered = entries.filter((e) => e.isAnswerFound).length;
  const distribution: Record<string, number> = {
    Forte: 0,
    Moyenne: 0,
    Faible: 0,
    "Aucune source": 0,
  };
  const docCounts = new Map<string, number>();
  let totalTokens = 0;

  for (const e of entries) {
    distribution[e.confidence.label] = (distribution[e.confidence.label] ?? 0) + 1;
    for (const doc of e.sourceDocuments) {
      docCounts.set(doc, (docCounts.get(doc) ?? 0) + 1);
    }
    totalTokens += estimateTokens(e.question) + estimateTokens(e.answer);
  }

  const mostConsulted = Array.from(docCounts.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6);

  return {
    totalQuestions: entries.length,
    answeredRate: answered / entries.length,
    noInfoRate: 1 - answered / entries.length,
    avgResponseTimeSeconds:
      entries.reduce((a, e) => a + e.responseTimeSeconds, 0) / entries.length,
    avgConfidenceScore: entries.reduce((a, e) => a + e.confidence.score, 0) / entries.length,
    confidenceDistribution: distribution,
    mostConsultedDocuments: mostConsulted,
    totalApiCalls: entries.length * 2, // recherche + génération
    totalTokensEstimate: totalTokens,
  };
}
