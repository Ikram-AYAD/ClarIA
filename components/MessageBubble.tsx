"use client";

import { motion } from "framer-motion";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Sparkles, User } from "lucide-react";
import clsx from "clsx";
import type { ChatMessage } from "@/lib/types";
import { ConfidenceBadge } from "./ConfidenceBadge";
import { SourceCitations } from "./SourceCitations";

export function MessageBubble({ message, isStreaming }: { message: ChatMessage; isStreaming?: boolean }) {
  const isUser = message.role === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className={clsx("flex gap-3", isUser && "flex-row-reverse")}
    >
      <div
        className={clsx(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border",
          isUser
            ? "border-white/10 bg-white/5 text-slate-300"
            : "border-accent-500/30 bg-gradient-to-br from-accent-500/25 to-violet-500/25 text-accent-300"
        )}
      >
        {isUser ? <User size={15} /> : <Sparkles size={15} />}
      </div>

      <div className={clsx("max-w-[78%] rounded-2xl px-4 py-3", isUser
        ? "bg-accent-500/15 border border-accent-500/20 text-slate-100"
        : "glass"
      )}>
        {message.content ? (
          <div className="prose-claria">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
            {isStreaming && (
              <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulseGlow rounded-sm bg-accent-400 align-text-bottom" />
            )}
          </div>
        ) : (
          <div className="flex items-center gap-1.5 py-1">
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent-400 [animation-delay:-0.3s]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent-400 [animation-delay:-0.15s]" />
            <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-accent-400" />
          </div>
        )}

        {!isUser && message.confidence && message.confidence.label !== "Aucune source" && (
          <div className="mt-3">
            <ConfidenceBadge confidence={message.confidence} />
          </div>
        )}
        {!isUser && message.sources && <SourceCitations sources={message.sources} />}
      </div>
    </motion.div>
  );
}
