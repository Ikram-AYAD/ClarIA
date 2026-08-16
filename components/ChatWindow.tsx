"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { ArrowUp, FileStack, MessagesSquare } from "lucide-react";
import type { ChatMessage, DocumentMeta } from "@/lib/types";
import { MessageBubble } from "./MessageBubble";

export function ChatWindow({
  messages,
  documents,
  asking,
  onAsk,
}: {
  messages: ChatMessage[];
  documents: DocumentMeta[];
  asking: boolean;
  onAsk: (question: string) => void;
}) {
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const submit = () => {
    if (!input.trim() || asking) return;
    onAsk(input.trim());
    setInput("");
  };

  return (
    <div className="flex h-full flex-1 flex-col">
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-6 py-6 md:px-10">
        <div className="mx-auto max-w-3xl">
          {messages.length === 0 ? (
            <EmptyState hasDocuments={documents.length > 0} />
          ) : (
            <div className="space-y-6">
              {messages.map((m, i) => (
                <MessageBubble
                  key={m.id}
                  message={m}
                  isStreaming={asking && i === messages.length - 1 && m.role === "assistant"}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-white/8 px-6 py-4 md:px-10">
        <div className="mx-auto flex max-w-3xl items-end gap-2 rounded-2xl border border-white/10 bg-white/[0.03] p-2 pl-4 shadow-card focus-within:border-accent-500/50 focus-within:shadow-glow">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            rows={1}
            placeholder="Pose une question sur tes documents..."
            className="max-h-32 flex-1 resize-none bg-transparent py-2 text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none"
          />
          <motion.button
            whileTap={{ scale: 0.92 }}
            onClick={submit}
            disabled={!input.trim() || asking}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-accent-500 to-violet-500 text-white transition-opacity disabled:opacity-30"
          >
            <ArrowUp size={16} />
          </motion.button>
        </div>
        <p className="mx-auto mt-2 max-w-3xl text-center text-[10px] text-slate-600">
          ClarIA répond uniquement à partir de tes documents et cite ses sources.
        </p>
      </div>
    </div>
  );
}

function EmptyState({ hasDocuments }: { hasDocuments: boolean }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex h-full min-h-[50vh] flex-col items-center justify-center text-center"
    >
      <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-white/10 bg-white/5">
        {hasDocuments ? (
          <MessagesSquare size={24} className="text-accent-400" />
        ) : (
          <FileStack size={24} className="text-slate-500" />
        )}
      </div>
      <h3 className="text-[15px] font-medium text-slate-200">
        {hasDocuments ? "Prêt à répondre à tes questions" : "Aucun document indexé pour l'instant"}
      </h3>
      <p className="mt-1.5 max-w-sm text-[13px] text-slate-500">
        {hasDocuments
          ? "Pose ta première question dans le champ ci-dessous."
          : "Dépose un PDF, un DOCX ou un TXT dans la barre latérale pour commencer."}
      </p>
    </motion.div>
  );
}
