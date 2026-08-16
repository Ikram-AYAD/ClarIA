"use client";

import { useCallback, useRef, useState } from "react";
import { UploadCloud } from "lucide-react";
import clsx from "clsx";

const ACCEPTED = [".pdf", ".docx", ".txt"];

export function Uploader({
  onFiles,
  disabled,
}: {
  onFiles: (files: File[]) => void;
  disabled?: boolean;
}) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(
    (fileList: FileList | null) => {
      if (!fileList) return;
      const files = Array.from(fileList).filter((f) =>
        ACCEPTED.some((ext) => f.name.toLowerCase().endsWith(ext))
      );
      if (files.length > 0) onFiles(files);
    },
    [onFiles]
  );

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        if (!disabled) handleFiles(e.dataTransfer.files);
      }}
      onClick={() => !disabled && inputRef.current?.click()}
      className={clsx(
        "group cursor-pointer rounded-xl border border-dashed px-4 py-6 text-center transition-all duration-200",
        disabled && "cursor-not-allowed opacity-50",
        dragging
          ? "border-accent-400 bg-accent-500/10 shadow-glow"
          : "border-white/15 bg-white/[0.02] hover:border-accent-500/40 hover:bg-white/[0.04]"
      )}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={ACCEPTED.join(",")}
        className="hidden"
        disabled={disabled}
        onChange={(e) => handleFiles(e.target.files)}
      />
      <UploadCloud
        size={22}
        className={clsx(
          "mx-auto mb-2 transition-colors",
          dragging ? "text-accent-400" : "text-slate-500 group-hover:text-accent-400"
        )}
      />
      <p className="text-xs font-medium text-slate-300">
        Dépose tes fichiers ici
      </p>
      <p className="mt-0.5 text-[11px] text-slate-500">PDF · DOCX · TXT</p>
    </div>
  );
}
