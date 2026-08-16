export type SearchMode = "hybrid" | "semantic" | "keyword";

export interface DocChunk {
  id: string;
  docId: string;
  docName: string;
  page: number | null;
  text: string;
  embedding: number[];
  ocr: boolean;
}

export interface DocumentMeta {
  id: string;
  name: string;
  addedAt: number;
  chunkCount: number;
  ocrPages: number;
  summary: string | null;
  summaryLoading: boolean;
}

export interface SourceRef {
  docName: string;
  page: number | null;
  text: string;
  score: number;
}

export type ConfidenceLabel = "Forte" | "Moyenne" | "Faible" | "Aucune source";

export interface Confidence {
  label: ConfidenceLabel;
  score: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceRef[];
  confidence?: Confidence;
  usedWebFallback?: boolean;
  createdAt: number;
}

export interface QueryLogEntry {
  id: string;
  timestamp: number;
  question: string;
  answer: string;
  confidence: Confidence;
  sourceDocuments: string[];
  responseTimeSeconds: number;
  searchMode: SearchMode;
  usedWebFallback: boolean;
  isAnswerFound: boolean;
}

export interface Conversation {
  id: string;
  title: string;
  updatedAt: number;
  messages: ChatMessage[];
  documentIds: string[];
}

export interface ClariaSettings {
  chunkSize: number;
  chunkOverlap: number;
  topK: number;
  searchMode: SearchMode;
  hybridAlpha: number;
}

export const DEFAULT_SETTINGS: ClariaSettings = {
  chunkSize: 800,
  chunkOverlap: 150,
  topK: 5,
  searchMode: "hybrid",
  hybridAlpha: 0.5,
};
