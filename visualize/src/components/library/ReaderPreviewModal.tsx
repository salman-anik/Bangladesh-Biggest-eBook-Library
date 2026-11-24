"use client";

import React, { useEffect, useRef, useState } from "react";
import {
  Bookmark,
  Check,
  Clock,
  Download,
  ExternalLink,
  Maximize2,
  Minimize2,
  NotebookPen,
  Share2,
  X,
} from "lucide-react";
import type { BookProgress, ThemeTokens } from "@/lib/anabookTheme";
import { BookNote, buildBookShareUrl } from "@/lib/userLibraryStore";
import {
  BookItem,
  formatBytes,
  getDownloadUrl,
  getPreviewUrl,
} from "@/types/library";

interface ReaderPreviewModalProps {
  book: BookItem | null;
  isSaved: boolean;
  progress?: BookProgress;
  note?: BookNote;
  theme: ThemeTokens;
  onToggleSave: (bookId: string) => void;
  onUpdateProgress: (
    bookId: string,
    currentPage: number,
    totalPages: number
  ) => void;
  onSaveNote: (bookId: string, text: string) => void;
  onLogReadingMinute: () => void;
  onClose: () => void;
}

function formatTimer(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

/**
 * Modernized ReaderPreviewModal featuring Cinema Fullscreen mode, live reading timer,
 * collapsible Notes & Progress side drawer, Share Deep Link, and Google Drive preview iframe.
 */
export function ReaderPreviewModal({
  book,
  isSaved,
  progress,
  note,
  theme,
  onToggleSave,
  onUpdateProgress,
  onSaveNote,
  onLogReadingMinute,
  onClose,
}: ReaderPreviewModalProps) {
  const [isCinema, setIsCinema] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [currPage, setCurrPage] = useState("0");
  const [totalPages, setTotalPages] = useState("300");
  const [noteText, setNoteText] = useState("");
  const [noteSaved, setNoteSaved] = useState(false);
  const [copied, setCopied] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const minuteCallbackRef = useRef(onLogReadingMinute);

  useEffect(() => {
    minuteCallbackRef.current = onLogReadingMinute;
  }, [onLogReadingMinute]);

  useEffect(() => {
    if (!book) {
      setIsCinema(false);
      setDrawerOpen(false);
      setElapsedSec(0);
      return;
    }
    setCurrPage(String(progress?.currentPage ?? 0));
    setTotalPages(String(progress?.totalPages ?? 300));
    setNoteText(note?.text ?? "");
    setNoteSaved(false);
    setElapsedSec(0);
  }, [book?.id, progress?.currentPage, progress?.totalPages, note?.text]);

  useEffect(() => {
    if (!book) return;
    const id = setInterval(() => {
      setElapsedSec((prev) => {
        const next = prev + 1;
        if (next > 0 && next % 60 === 0) {
          minuteCallbackRef.current();
        }
        return next;
      });
    }, 1000);
    return () => clearInterval(id);
  }, [book?.id]);

  useEffect(() => {
    if (!book) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        if (isCinema) setIsCinema(false);
        else onClose();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [book, isCinema, onClose]);

  if (!book) return null;

  const driveViewUrl = `https://drive.google.com/file/d/${encodeURIComponent(
    book.id
  )}/view`;

  const toggleCinema = async () => {
    const next = !isCinema;
    setIsCinema(next);
    try {
      if (next && containerRef.current?.requestFullscreen) {
        await containerRef.current.requestFullscreen();
      } else if (!next && document.fullscreenElement) {
        await document.exitFullscreen();
      }
    } catch {
      // Fall back cleanly to CSS full-viewport mode
    }
  };

  const handleShare = async () => {
    const url = buildBookShareUrl(book.id);
    try {
      if (navigator.share) {
        await navigator.share({
          title: `${book.title} — AnaBook`,
          url,
        });
        return;
      }
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(url);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }
    } catch {
      // Ignore canceled share
    }
  };

  return (
    <div
      className={`fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center ${
        isCinema ? "p-0" : "p-2 sm:p-5"
      }`}
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={`Reading ${book.title}`}
    >
      <div
        ref={containerRef}
        className={`border overflow-hidden flex flex-col shadow-2xl transition-all ${
          isCinema
            ? "w-screen h-screen rounded-none"
            : "w-full max-w-6xl h-[93vh] sm:h-[90vh] rounded-2xl sm:rounded-3xl"
        }`}
        style={{
          backgroundColor: theme.surface,
          borderColor: theme.border,
          color: theme.ink,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top Reader Toolbar */}
        <div
          className="px-3.5 sm:px-5 py-2.5 sm:py-3 border-b flex flex-wrap items-center justify-between gap-2"
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

          <div className="flex flex-wrap items-center gap-1.5 shrink-0">
            {/* Live Session Timer */}
            <span
              className="hidden sm:inline-flex items-center gap-1 px-2.5 py-1 rounded-full border text-[11px] font-bold tabular-nums"
              style={{
                backgroundColor: theme.surfaceAlt,
                borderColor: theme.border,
                color: theme.accent,
              }}
              title="Active reading session timer"
            >
              <Clock className="w-3 h-3" />
              <span>{formatTimer(elapsedSec)}</span>
            </span>

            {/* Collapsible Notes & Progress Drawer Button */}
            <button
              type="button"
              onClick={() => setDrawerOpen((o) => !o)}
              title="Toggle notes and progress"
              aria-label="Toggle notes and progress"
              aria-expanded={drawerOpen}
              className="inline-flex items-center gap-1 px-2.5 sm:px-3 py-1.5 rounded-full border text-[11px] font-bold transition cursor-pointer"
              style={{
                backgroundColor: drawerOpen
                  ? theme.accentSoft
                  : theme.surfaceAlt,
                borderColor: drawerOpen ? theme.accent : theme.border,
                color: drawerOpen ? theme.accent : theme.ink,
              }}
            >
              <NotebookPen className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Notes</span>
            </button>

            <button
              type="button"
              onClick={handleShare}
              title="Copy share link"
              aria-label="Share book link"
              className="w-8 h-8 rounded-full border flex items-center justify-center transition cursor-pointer"
              style={{
                backgroundColor: copied ? theme.accentSoft : theme.surfaceAlt,
                borderColor: copied ? theme.accent : theme.border,
                color: copied ? theme.accent : theme.ink,
              }}
            >
              {copied ? (
                <Check className="w-3.5 h-3.5" />
              ) : (
                <Share2 className="w-3.5 h-3.5" />
              )}
            </button>

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

            <button
              type="button"
              onClick={toggleCinema}
              title={isCinema ? "Exit fullscreen" : "Fullscreen cinema mode"}
              aria-label={
                isCinema ? "Exit fullscreen" : "Fullscreen cinema mode"
              }
              className="w-8 h-8 rounded-full border flex items-center justify-center transition cursor-pointer"
              style={{
                backgroundColor: isCinema
                  ? theme.accentSoft
                  : theme.surfaceAlt,
                borderColor: isCinema ? theme.accent : theme.border,
                color: isCinema ? theme.accent : theme.ink,
              }}
            >
              {isCinema ? (
                <Minimize2 className="w-3.5 h-3.5" />
              ) : (
                <Maximize2 className="w-3.5 h-3.5" />
              )}
            </button>

            <a
              href={driveViewUrl}
              target="_blank"
              rel="noopener noreferrer"
              title="Open in Google Drive"
              className="hidden md:inline-flex items-center gap-1 px-3 py-1.5 rounded-full border text-xs font-bold transition hover:opacity-85"
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
              className="inline-flex items-center gap-1 sm:gap-1.5 px-3 sm:px-4 py-1.5 rounded-full text-[11px] sm:text-xs font-bold transition hover:opacity-90"
              style={{
                backgroundColor: theme.cream,
                color: theme.creamInk,
              }}
            >
              <Download
                className="w-3 h-3 sm:w-3.5 sm:h-3.5"
                style={{ color: theme.accent }}
              />
              <span className="hidden xs:inline">Download</span>
            </a>

            <button
              type="button"
              onClick={onClose}
              aria-label="Close reader"
              className="w-8 h-8 rounded-full flex items-center justify-center transition hover:opacity-80 cursor-pointer"
              style={{
                backgroundColor: theme.surfaceAlt,
                color: theme.ink,
              }}
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Main Split Body: PDF Iframe + Optional Notes/Progress Drawer */}
        <div className="flex-1 min-h-0 flex flex-col md:flex-row">
          <iframe
            src={getPreviewUrl(book.id)}
            title={book.title}
            className="flex-1 w-full h-full"
            style={{ backgroundColor: theme.surfaceAlt }}
            allow="autoplay"
          />

          {drawerOpen && (
            <aside
              className="w-full md:w-80 border-t md:border-t-0 md:border-l p-4 flex flex-col gap-4 overflow-y-auto shrink-0 max-h-[42vh] md:max-h-none"
              style={{
                backgroundColor: theme.surfaceAlt,
                borderColor: theme.border,
              }}
            >
              {/* Live Progress Update */}
              <div
                className="rounded-2xl border p-3.5 space-y-2.5"
                style={{
                  backgroundColor: theme.surface,
                  borderColor: theme.borderSubtle,
                }}
              >
                <div className="flex items-center justify-between text-xs font-extrabold">
                  <span>Reading Progress</span>
                  <span style={{ color: theme.accent }}>
                    {progress?.progressPct ?? 0}%
                  </span>
                </div>
                <div className="flex items-end gap-2">
                  <label className="flex-1 space-y-1">
                    <span
                      className="text-[10px] font-semibold block"
                      style={{ color: theme.muted }}
                    >
                      Page
                    </span>
                    <input
                      type="number"
                      min={0}
                      value={currPage}
                      onChange={(e) => setCurrPage(e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded-xl border text-xs font-bold focus:outline-none"
                      style={{
                        backgroundColor: theme.bg,
                        borderColor: theme.border,
                        color: theme.ink,
                      }}
                    />
                  </label>
                  <label className="flex-1 space-y-1">
                    <span
                      className="text-[10px] font-semibold block"
                      style={{ color: theme.muted }}
                    >
                      Total
                    </span>
                    <input
                      type="number"
                      min={1}
                      value={totalPages}
                      onChange={(e) => setTotalPages(e.target.value)}
                      className="w-full px-2.5 py-1.5 rounded-xl border text-xs font-bold focus:outline-none"
                      style={{
                        backgroundColor: theme.bg,
                        borderColor: theme.border,
                        color: theme.ink,
                      }}
                    />
                  </label>
                  <button
                    type="button"
                    onClick={() =>
                      onUpdateProgress(
                        book.id,
                        Math.max(0, parseInt(currPage, 10) || 0),
                        Math.max(1, parseInt(totalPages, 10) || 300)
                      )
                    }
                    className="px-3 py-1.5 rounded-xl text-xs font-extrabold cursor-pointer"
                    style={{
                      backgroundColor: theme.cream,
                      color: theme.creamInk,
                    }}
                  >
                    Save
                  </button>
                </div>
              </div>

              {/* Study Notes */}
              <div
                className="rounded-2xl border p-3.5 flex-1 flex flex-col gap-2.5"
                style={{
                  backgroundColor: theme.surface,
                  borderColor: theme.borderSubtle,
                }}
              >
                <div className="flex items-center justify-between text-xs font-extrabold">
                  <span>Study Notes</span>
                  {noteSaved && (
                    <span style={{ color: theme.accent }}>Saved</span>
                  )}
                </div>
                <textarea
                  value={noteText}
                  onChange={(e) => {
                    setNoteText(e.target.value);
                    setNoteSaved(false);
                  }}
                  placeholder="Jot down notes, formulas, or quotes while reading…"
                  className="flex-1 min-h-[120px] w-full px-3 py-2 rounded-xl border text-xs leading-relaxed focus:outline-none resize-none"
                  style={{
                    backgroundColor: theme.bg,
                    borderColor: theme.border,
                    color: theme.ink,
                  }}
                />
                <button
                  type="button"
                  onClick={() => {
                    onSaveNote(book.id, noteText);
                    setNoteSaved(true);
                  }}
                  className="w-full py-2 rounded-xl text-xs font-extrabold cursor-pointer transition hover:opacity-90"
                  style={{
                    backgroundColor: theme.cream,
                    color: theme.creamInk,
                  }}
                >
                  Save Note
                </button>
              </div>
            </aside>
          )}
        </div>
      </div>
    </div>
  );
}
