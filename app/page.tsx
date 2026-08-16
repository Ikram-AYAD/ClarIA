"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, MessageCircle, Sparkles, X, LayoutDashboard } from "lucide-react";
import clsx from "clsx";
import { useClaria } from "@/hooks/useClaria";
import { Sidebar } from "@/components/Sidebar";
import { ChatWindow } from "@/components/ChatWindow";
import { Dashboard } from "@/components/Dashboard";

type Tab = "chat" | "dashboard";

export default function Home() {
  const c = useClaria();
  const [tab, setTab] = useState<Tab>("chat");

  useEffect(() => {
    if (!c.globalError) return;
    const t = setTimeout(() => c.setGlobalError(null), 6000);
    return () => clearTimeout(t);
  }, [c.globalError, c]);

  if (!c.hydrated) {
    return (
      <div className="flex h-screen items-center justify-center">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
          className="h-8 w-8 rounded-full border-2 border-accent-500/30 border-t-accent-400"
        />
      </div>
    );
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        documents={c.documents}
        onAddFiles={c.addDocuments}
        onRemoveDocument={c.removeDocument}
        indexing={c.indexing}
        indexProgress={c.indexProgress}
        settings={c.settings}
        onSettingsChange={c.setSettings}
        conversations={c.conversations}
        currentConversationId={c.currentConversationId}
        onNewConversation={c.startNewConversation}
        onLoadConversation={c.loadConversation}
        onDeleteConversation={c.deleteConversation}
        onRenameConversation={c.renameConversation}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-white/8 px-6 py-3 md:px-10">
          <div>
            <h2 className="text-sm font-medium text-slate-200">
              {tab === "chat" ? "Assistant documentaire" : "Tableau de bord"}
            </h2>
            <p className="text-[11px] text-slate-500">
              Réponses sourcées, sans invention — sémantique + mots-clés.
            </p>
          </div>
          <div className="flex items-center gap-1 rounded-xl border border-white/10 bg-white/[0.03] p-1">
            <TabButton active={tab === "chat"} onClick={() => setTab("chat")} icon={<MessageCircle size={13} />}>
              Chat
            </TabButton>
            <TabButton
              active={tab === "dashboard"}
              onClick={() => setTab("dashboard")}
              icon={<LayoutDashboard size={13} />}
            >
              Tableau de bord
            </TabButton>
          </div>
        </header>

        <div className="relative min-h-0 flex-1">
          {tab === "chat" ? (
            <ChatWindow
              messages={c.messages}
              documents={c.documents}
              asking={c.asking}
              onAsk={c.askQuestion}
            />
          ) : (
            <Dashboard queryLog={c.queryLog} />
          )}
        </div>
      </div>

      <AnimatePresence>
        {c.globalError && (
          <motion.div
            initial={{ opacity: 0, y: 20, x: "-50%" }}
            animate={{ opacity: 1, y: 0, x: "-50%" }}
            exit={{ opacity: 0, y: 20, x: "-50%" }}
            className="fixed bottom-6 left-1/2 z-50 flex max-w-md items-start gap-2.5 rounded-xl border border-red-500/30 bg-ink-850/95 px-4 py-3 shadow-card backdrop-blur"
          >
            <AlertTriangle size={16} className="mt-0.5 shrink-0 text-red-400" />
            <p className="text-xs text-slate-300">{c.globalError}</p>
            <button onClick={() => c.setGlobalError(null)} className="ml-1 text-slate-500 hover:text-slate-300">
              <X size={14} />
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function TabButton({
  active,
  onClick,
  icon,
  children,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors",
        active ? "bg-gradient-to-br from-accent-500 to-violet-500 text-white shadow-glow" : "text-slate-400 hover:text-slate-200"
      )}
    >
      {icon}
      {children}
    </button>
  );
}
