"use client";

import React, { useEffect } from "react";
import { Bookmark, Download, ExternalLink, X } from "lucide-react";
import type { ThemeTokens } from "@/lib/anabookTheme";
import {
  BookItem,
  formatBytes,
  getDownloadUrl,
  getPreviewUrl,
} from "@/types/library";

interface ReaderPreviewModalProps {
  book: BookItem | null;
  isSaved: boolean;
  theme: ThemeTokens;
  onToggleSave: (bookId: string) => void;
  onClose: () => void;
}

/**
 * Full-screen Google Drive PDF/eBook reader preview modal styled with active AnaBook theme tokens.
 */
export function ReaderPreviewModal({
  book,
  isSaved,
  theme,
  onToggleSave,
  onClose,
}: ReaderPreviewModalProps) {
  useEffect(() => {
    if (!book) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [book, onClose]);

  if (!book) return null;

  const driveViewUrl = `https://drive.google.com/file/d/${encodeURIComponent(
    book.id
  )}/view`;

  return (
    <div
      className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-2 sm:p-6"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={`Reading ${book.title}`}
    >
      <div
        className="w-full max-w-5xl h-[92vh] sm:h-[88vh] rounded-2xl sm:rounded-3xl border overflow-hidden flex flex-col shadow-2xl"
        style={{
          backgroundColor: theme.surface,
          borderColor: theme.border,
          color: theme.ink,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          className="px-4 sm:px-5 py-3 sm:py-3.5 border-b flex items-center justify-between gap-2.5"
          style={{
            backgroundColor: theme.surface,
            borderColor: theme.border,
          }}
        >
          <div className="min-w-0 flex-1">
            <h3 className="text-xs sm:text-sm font-extrabold truncate">
              {book.title}
            </h3>
            <p
              className="text-[10px] sm:text-[11px] truncate"
              style={{ color: theme.muted }}
            >
              {book.author} · {book.fmt} · {formatBytes(book.size)}
            </p>
          </div>

          <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
            <button
              type="button"
              onClick={() => onToggleSave(book.id)}
              title={isSaved ? "Remove bookmark" : "Bookmark"}
              aria-label={isSaved ? "Remove bookmark" : "Bookmark"}
              className="w-8 h-8 rounded-full border flex items-center justify-center transition cursor-pointer"
              style={{
                backgroundColor: isSaved ? theme.accentSoft : theme.surfaceAlt,
                borderColor: isSaved ? theme.accent : theme.border,
                color: isSaved ? theme.accent : theme.ink,
              }}
            >
              <Bookmark
                className="w-3.5 h-3.5"
                fill={isSaved ? "currentColor" : "none"}
              />
            </button>

            <a
              href={driveViewUrl}
              target="_blank"
              rel="noopener noreferrer"
              title="Open in Google Drive"
              className="hidden sm:inline-flex items-center gap-1 px-3 py-1.5 rounded-full border text-xs font-bold transition hover:opacity-85"
              style={{
                backgroundColor: theme.surfaceAlt,
                borderColor: theme.border,
                color: theme.ink,
              }}
            >
              <span>Drive</span>
              <ExternalLink className="w-3 h-3" />
            </a>

            <a
              href={getDownloadUrl(book.id)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 sm:gap-1.5 px-3 sm:px-4 py-1.5 sm:py-2 rounded-full text-[11px] sm:text-xs font-bold transition hover:opacity-90"
              style={{
                backgroundColor: theme.cream,
                color: theme.creamInk,
              }}
            >
              <Download
                className="w-3 h-3 sm:w-3.5 sm:h-3.5"
                style={{ color: theme.accent }}
              />
              <span>Download</span>
            </a>

            <button
              type="button"
              onClick={onClose}
              aria-label="Close reader"
              className="w-7 h-7 sm:w-8 sm:h-8 rounded-full flex items-center justify-center transition hover:opacity-80 cursor-pointer"
              style={{
                backgroundColor: theme.surfaceAlt,
                color: theme.ink,
              }}
            >
              <X className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
            </button>
          </div>
        </div>

        <iframe
          src={getPreviewUrl(book.id)}
          title={book.title}
          className="flex-1 w-full"
          style={{ backgroundColor: theme.surfaceAlt }}
          allow="autoplay"
        />
      </div>
    </div>
  );
}
