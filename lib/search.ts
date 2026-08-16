import { tokenize } from "./chunk";
import type { DocChunk, SearchMode } from "./types";

export interface SearchResult {
  chunk: DocChunk;
  score: number;
}

function cosineSimilarity(a: number[], b: number[]): number {
  let dot = 0;
  let normA = 0;
  let normB = 0;
  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i];
    normA += a[i] * a[i];
    normB += b[i] * b[i];
  }
  if (normA === 0 || normB === 0) return 0;
  return dot / (Math.sqrt(normA) * Math.sqrt(normB));
}

/** BM25 (Okapi), implémentation légère, sans dépendance. */
class Bm25 {
  private docs: string[][];
  private docLengths: number[];
  private avgDocLength: number;
  private df: Map<string, number>;
  private idf: Map<string, number>;
  private k1 = 1.5;
  private b = 0.75;

  constructor(docs: string[][]) {
    this.docs = docs;
    this.docLengths = docs.map((d) => d.length);
    this.avgDocLength =
      this.docLengths.reduce((a, b) => a + b, 0) / (docs.length || 1);

    this.df = new Map();
    for (const doc of docs) {
      const seen = new Set(doc);
      for (const term of seen) {
        this.df.set(term, (this.df.get(term) ?? 0) + 1);
      }
    }

    this.idf = new Map();
    const N = docs.length;
    for (const [term, freq] of this.df.entries()) {
      const idf = Math.log((N - freq + 0.5) / (freq + 0.5) + 1);
      this.idf.set(term, idf);
    }
  }

  scores(queryTerms: string[]): number[] {
    return this.docs.map((doc, idx) => {
      const termFreq = new Map<string, number>();
      for (const t of doc) termFreq.set(t, (termFreq.get(t) ?? 0) + 1);

      let score = 0;
      for (const term of queryTerms) {
        const tf = termFreq.get(term) ?? 0;
        if (tf === 0) continue;
        const idf = this.idf.get(term) ?? 0;
        const denom =
          tf + this.k1 * (1 - this.b + (this.b * this.docLengths[idx]) / this.avgDocLength);
        score += idf * ((tf * (this.k1 + 1)) / denom);
      }
      return score;
    });
  }
}

export function semanticSearch(
  chunks: DocChunk[],
  queryEmbedding: number[],
  k: number
): SearchResult[] {
  const scored = chunks.map((chunk) => ({
    chunk,
    score: cosineSimilarity(chunk.embedding, queryEmbedding),
  }));
  scored.sort((a, b) => b.score - a.score);
  return scored.slice(0, k);
}

export function keywordSearch(
  chunks: DocChunk[],
  query: string,
  k: number
): SearchResult[] {
  if (chunks.length === 0) return [];
  const tokenizedDocs = chunks.map((c) => tokenize(c.text));
  const bm25 = new Bm25(tokenizedDocs);
  const queryTerms = tokenize(query);
  const scores = bm25.scores(queryTerms);

  return chunks
    .map((chunk, i) => ({ chunk, score: scores[i] }))
    .filter((r) => r.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, k);
}

export function hybridSearch(
  chunks: DocChunk[],
  queryEmbedding: number[],
  query: string,
  k: number,
  alpha: number
): SearchResult[] {
  if (chunks.length === 0) return [];

  const semanticScores = chunks.map((chunk) =>
    cosineSimilarity(chunk.embedding, queryEmbedding)
  );

  const tokenizedDocs = chunks.map((c) => tokenize(c.text));
  const bm25 = new Bm25(tokenizedDocs);
  const queryTerms = tokenize(query);
  const bm25Scores = bm25.scores(queryTerms);
  const maxBm25 = Math.max(...bm25Scores, 0);
  const normalizedBm25 = bm25Scores.map((s) => (maxBm25 > 0 ? s / maxBm25 : 0));

  const combined = chunks.map((chunk, i) => ({
    chunk,
    score: alpha * semanticScores[i] + (1 - alpha) * normalizedBm25[i],
  }));

  combined.sort((a, b) => b.score - a.score);
  return combined.slice(0, k);
}

export function search(
  chunks: DocChunk[],
  mode: SearchMode,
  queryEmbedding: number[],
  query: string,
  k: number,
  alpha: number
): SearchResult[] {
  if (chunks.length === 0 || !query.trim()) return [];
  if (mode === "semantic") return semanticSearch(chunks, queryEmbedding, k);
  if (mode === "keyword") return keywordSearch(chunks, query, k);
  return hybridSearch(chunks, queryEmbedding, query, k, alpha);
}

/** Score de confiance déduit des scores de pertinence des extraits utilisés. */
export function computeConfidence(results: SearchResult[]): {
  label: "Forte" | "Moyenne" | "Faible" | "Aucune source";
  score: number;
} {
  if (results.length === 0) return { label: "Aucune source", score: 0 };
  const avg = results.reduce((a, r) => a + Math.max(r.score, 0), 0) / results.length;
  if (avg >= 0.55) return { label: "Forte", score: avg };
  if (avg >= 0.3) return { label: "Moyenne", score: avg };
  return { label: "Faible", score: avg };
}
