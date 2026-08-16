"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  FileText,
  Trash2,
  Settings2,
  ChevronDown,
  Plus,
  MessageSquare,
  Pencil,
  X,
  Sparkles,
} from "lucide-react";
import clsx from "clsx";
import { Uploader } from "./Uploader";
import type { ClariaSettings, Conversation, DocumentMeta, SearchMode } from "@/lib/types";

const SEARCH_MODE_LABELS: Record<SearchMode, string> = {
  hybrid: "Hybride (sémantique + mots-clés)",
  semantic: "Sémantique seule",
  keyword: "Mots-clés seuls (BM25)",
};

function fileIcon(name: string) {
  const ext = name.split(".").pop()?.toLowerCase();
  if (ext === "pdf") return "📕";
  if (ext === "docx") return "📘";
  return "📄";
}

export function Sidebar({
  documents,
  onAddFiles,
  onRemoveDocument,
  indexing,
  indexProgress,
  settings,
  onSettingsChange,
  conversations,
  currentConversationId,
  onNewConversation,
  onLoadConversation,
  onDeleteConversation,
  onRenameConversation,
}: {
  documents: DocumentMeta[];
  onAddFiles: (files: File[]) => void;
  onRemoveDocument: (id: string) => void;
  indexing: boolean;
  indexProgress: { done: number; total: number; label: string } | null;
  settings: ClariaSettings;
  onSettingsChange: (s: ClariaSettings) => void;
  conversations: Conversation[];
  currentConversationId: string | null;
  onNewConversation: () => void;
  onLoadConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
  onRenameConversation: (id: string, title: string) => void;
}) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [expandedSummary, setExpandedSummary] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  return (
    <aside className="flex h-full w-[320px] shrink-0 flex-col overflow-y-auto border-r border-white/10 bg-ink-900/60 px-4 py-5">
      <div className="mb-6 flex items-center gap-2.5 px-1">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-accent-500 to-violet-500 shadow-glow">
          <Sparkles size={17} className="text-white" />
        </div>
        <div>
          <h1 className="text-[15px] font-semibold leading-none text-slate-50">ClarIA</h1>
          <p className="mt-1 text-[11px] leading-none text-slate-500">
            Assistant documentaire IA
          </p>
        </div>
      </div>

      {/* Documents */}
      <section className="mb-5">
        <h2 className="mb-2 flex items-center gap-1.5 px-1 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
          <FileText size={12} /> Documents
        </h2>
        <Uploader onFiles={onAddFiles} disabled={indexing} />

        {indexing && indexProgress && (
          <div className="mt-3 space-y-1.5">
            <div className="h-1.5 overflow-hidden rounded-full bg-white/5">
              <motion.div
                className="h-full bg-gradient-to-r from-accent-500 to-violet-500"
                initial={{ width: 0 }}
                animate={{
                  width: `${((indexProgress.done + 0.5) / Math.max(indexProgress.total, 1)) * 100}%`,
                }}
                transition={{ ease: "easeOut" }}
              />
            </div>
            <p className="shimmer-text text-[11px]">{indexProgress.label}</p>
          </div>
        )}

        {documents.length > 0 && (
          <div className="mt-3 space-y-1.5">
            <p className="px-1 text-[11px] text-slate-500">
              {documents.length} document{documents.length > 1 ? "s" : ""} indexé
              {documents.length > 1 ? "s" : ""}
            </p>
            {documents.map((doc) => (
              <div key={doc.id} className="rounded-xl border border-white/8 bg-white/[0.03]">
                <div className="flex items-center gap-2 px-3 py-2.5">
                  <span className="text-base leading-none">{fileIcon(doc.name)}</span>
                  <button
                    onClick={() => setExpandedSummary(expandedSummary === doc.id ? null : doc.id)}
                    className="min-w-0 flex-1 text-left"
                  >
                    <p className="truncate text-xs font-medium text-slate-200">{doc.name}</p>
                    <p className="text-[10px] text-slate-500">{doc.chunkCount} extraits</p>
                  </button>
                  <button
                    onClick={() => onRemoveDocument(doc.id)}
                    className="rounded-md p-1 text-slate-500 hover:bg-red-500/10 hover:text-red-400"
                    title={`Retirer '${doc.name}'`}
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
                {expandedSummary === doc.id && (
                  <div className="border-t border-white/8 px-3 py-2.5 text-[11px] leading-relaxed text-slate-400">
                    {doc.summaryLoading ? (
                      <span className="shimmer-text">Résumé en cours de génération...</span>
                    ) : (
                      doc.summary
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Réglages avancés */}
      <section className="mb-5 rounded-xl border border-white/8 bg-white/[0.02]">
        <button
          onClick={() => setSettingsOpen((o) => !o)}
          className="flex w-full items-center justify-between px-3 py-2.5 text-xs font-medium text-slate-300"
        >
          <span className="flex items-center gap-1.5">
            <Settings2 size={13} /> Paramètres avancés
          </span>
          <ChevronDown
            size={13}
            className={clsx("transition-transform", settingsOpen && "rotate-180")}
          />
        </button>
        {settingsOpen && (
          <div className="space-y-3 border-t border-white/8 px-3 py-3">
            <div>
              <label className="mb-1 flex justify-between text-[11px] text-slate-400">
                <span>Taille des chunks</span>
                <span>{settings.chunkSize}</span>
              </label>
              <input
                type="range"
                min={300}
                max={2000}
                step={50}
                value={settings.chunkSize}
                onChange={(e) => onSettingsChange({ ...settings, chunkSize: Number(e.target.value) })}
                className="w-full accent-accent-500"
              />
            </div>
            <div>
              <label className="mb-1 flex justify-between text-[11px] text-slate-400">
                <span>Chevauchement</span>
                <span>{settings.chunkOverlap}</span>
              </label>
              <input
                type="range"
                min={0}
                max={500}
                step={25}
                value={settings.chunkOverlap}
                onChange={(e) => onSettingsChange({ ...settings, chunkOverlap: Number(e.target.value) })}
                className="w-full accent-accent-500"
              />
            </div>
            <div>
              <label className="mb-1 flex justify-between text-[11px] text-slate-400">
                <span>Top-k extraits</span>
                <span>{settings.topK}</span>
              </label>
              <input
                type="range"
                min={1}
                max={10}
                value={settings.topK}
                onChange={(e) => onSettingsChange({ ...settings, topK: Number(e.target.value) })}
                className="w-full accent-accent-500"
              />
            </div>
            <div className="h-px bg-white/8" />
            <div>
              <label className="mb-1.5 block text-[11px] text-slate-400">Mode de recherche</label>
              <div className="space-y-1">
                {(Object.keys(SEARCH_MODE_LABELS) as SearchMode[]).map((mode) => (
                  <button
                    key={mode}
                    onClick={() => onSettingsChange({ ...settings, searchMode: mode })}
                    className={clsx(
                      "w-full rounded-lg px-2.5 py-1.5 text-left text-[11px] transition-colors",
                      settings.searchMode === mode
                        ? "bg-accent-500/15 text-accent-300"
                        : "text-slate-400 hover:bg-white/5"
                    )}
                  >
                    {SEARCH_MODE_LABELS[mode]}
                  </button>
                ))}
              </div>
            </div>
            {settings.searchMode === "hybrid" && (
              <div>
                <label className="mb-1 flex justify-between text-[11px] text-slate-400">
                  <span>Poids sémantique</span>
                  <span>{settings.hybridAlpha.toFixed(2)}</span>
                </label>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={settings.hybridAlpha}
                  onChange={(e) =>
                    onSettingsChange({ ...settings, hybridAlpha: Number(e.target.value) })
                  }
                  className="w-full accent-accent-500"
                />
              </div>
            )}
          </div>
        )}
      </section>

      {/* Conversation */}
      <section className="mb-2">
        <button
          onClick={onNewConversation}
          className="flex w-full items-center justify-center gap-1.5 rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-xs font-medium text-slate-200 transition-colors hover:bg-white/10"
        >
          <Plus size={14} /> Nouvelle conversation
        </button>

        <button
          onClick={() => setHistoryOpen((o) => !o)}
          className="mt-2 flex w-full items-center justify-between px-1 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-500"
        >
          <span className="flex items-center gap-1.5">
            <MessageSquare size={12} /> Historique
          </span>
          <ChevronDown size={13} className={clsx("transition-transform", historyOpen && "rotate-180")} />
        </button>

        {historyOpen && (
          <div className="space-y-1">
            {conversations.length === 0 && (
              <p className="px-1 text-[11px] text-slate-600">Aucune conversation sauvegardée.</p>
            )}
            {conversations.map((c) => (
              <div
                key={c.id}
                className={clsx(
                  "group flex items-center gap-1.5 rounded-lg px-2 py-1.5",
                  c.id === currentConversationId ? "bg-accent-500/10" : "hover:bg-white/5"
                )}
              >
                {renamingId === c.id ? (
                  <input
                    autoFocus
                    value={renameValue}
                    onChange={(e) => setRenameValue(e.target.value)}
                    onBlur={() => {
                      onRenameConversation(c.id, renameValue || c.title);
                      setRenamingId(null);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") e.currentTarget.blur();
                    }}
                    className="min-w-0 flex-1 rounded bg-black/30 px-1.5 py-1 text-[11px] text-slate-200 outline-none"
                  />
                ) : (
                  <button
                    onClick={() => onLoadConversation(c.id)}
                    className="min-w-0 flex-1 truncate text-left text-[11px] text-slate-300"
                    title={c.title}
                  >
                    {c.title}
                  </button>
                )}
                <button
                  onClick={() => {
                    setRenamingId(c.id);
                    setRenameValue(c.title);
                  }}
                  className="rounded p-1 text-slate-600 opacity-0 transition-opacity hover:text-slate-300 group-hover:opacity-100"
                >
                  <Pencil size={11} />
                </button>
                <button
                  onClick={() => onDeleteConversation(c.id)}
                  className="rounded p-1 text-slate-600 opacity-0 transition-opacity hover:text-red-400 group-hover:opacity-100"
                >
                  <X size={12} />
                </button>
              </div>
            ))}
          </div>
        )}
      </section>
    </aside>
  );
}
