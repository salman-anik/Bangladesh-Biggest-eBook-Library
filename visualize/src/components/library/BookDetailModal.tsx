"use client";

import React, { useEffect, useState } from "react";
import {
  Bookmark,
  BookOpen,
  Check,
  CheckCircle2,
  Download,
  FolderOpen,
  FolderPlus,
  NotebookPen,
  Plus,
  Share2,
  X,
} from "lucide-react";
import type { BookProgress, ThemeTokens } from "@/lib/anabookTheme";
import {
  BookNote,
  buildBookShareUrl,
  CustomCollection,
} from "@/lib/userLibraryStore";
import { BookItem, formatBytes, getDownloadUrl } from "@/types/library";
import { AuthorAvatar } from "./AuthorAvatar";
import { BookCover } from "./BookCover";

interface BookDetailModalProps {
  book: BookItem | null;
  progress?: BookProgress;
  note?: BookNote;
  collections: CustomCollection[];
  isCurrentRead: boolean;
  isSaved: boolean;
  theme: ThemeTokens;
  onClose: () => void;
  onReadOnline: (book: BookItem) => void;
  onToggleSave: (bookId: string) => void;
  onSetCurrentlyReading: (bookId: string) => void;
  onUpdateProgress: (
    bookId: string,
    currentPage: number,
    totalPages: number
  ) => void;
  onSaveNote: (bookId: string, text: string) => void;
  onToggleCollectionBook: (collectionId: string, bookId: string) => void;
  onCreateCollection: (name: string, initialBookId?: string) => void;
  onNavigateFolder: (path: string[]) => void;
  onFilterAuthor: (authorName: string) => void;
}

/**
 * Enhanced BookDetailModal with cloth-bound cover, Share Deep Link,
 * Custom Reading Lists (Collections), Personal Study Note, and Reading Progress editor.
 */
export function BookDetailModal({
  book,
  progress,
  note,
  collections,
  isCurrentRead,
  isSaved,
  theme,
  onClose,
  onReadOnline,
  onToggleSave,
  onSetCurrentlyReading,
  onUpdateProgress,
  onSaveNote,
  onToggleCollectionBook,
  onCreateCollection,
  onNavigateFolder,
  onFilterAuthor,
}: BookDetailModalProps) {
  const [currInput, setCurrInput] = useState("0");
  const [totalInput, setTotalInput] = useState("300");
  const [savedNotice, setSavedNotice] = useState(false);
  const [noteInput, setNoteInput] = useState("");
  const [noteSaved, setNoteSaved] = useState(false);
  const [newCollectionName, setNewCollectionName] = useState("");
  const [showNewCollection, setShowNewCollection] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);

  useEffect(() => {
    if (book) {
      setCurrInput(String(progress?.currentPage ?? 0));
      setTotalInput(String(progress?.totalPages ?? 300));
      setNoteInput(note?.text ?? "");
      setSavedNotice(false);
      setNoteSaved(false);
      setCopiedLink(false);
      setShowNewCollection(false);
      setNewCollectionName("");
    }
  }, [book?.id, progress?.currentPage, progress?.totalPages, note?.text]);

  useEffect(() => {
    if (!book) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [book, onClose]);

  if (!book) return null;

  const pct = progress?.progressPct ?? 0;
  const folderPath = [
    book.cat,
    ...(book.sub ? book.sub.split("/").filter(Boolean) : []),
  ];

  const handleShare = async () => {
    const shareUrl = buildBookShareUrl(book.id);
    try {
      if (typeof navigator !== "undefined" && navigator.share) {
        await navigator.share({
          title: `${book.title} — AnaBook`,
          text: `${book.title} by ${book.author} on AnaBook Online Library`,
          url: shareUrl,
        });
        return;
      }
      if (typeof navigator !== "undefined" && navigator.clipboard) {
        await navigator.clipboard.writeText(shareUrl);
        setCopiedLink(true);
        setTimeout(() => setCopiedLink(false), 2200);
      }
    } catch {
      // Ignore canceled share sheets
    }
  };

  const handleCreateCol = (e: React.FormEvent) => {
    e.preventDefault();
    const clean = newCollectionName.trim();
    if (!clean) return;
    onCreateCollection(clean, book.id);
    setNewCollectionName("");
    setShowNewCollection(false);
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-black/72 backdrop-blur-sm flex items-end sm:items-center justify-center p-0 sm:p-5"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={`Book details: ${book.title}`}
    >
      <div
        className="w-full max-w-xl max-h-[92vh] rounded-t-3xl sm:rounded-3xl border overflow-hidden flex flex-col shadow-2xl"
        style={{
          backgroundColor: theme.surfaceAlt,
          borderColor: theme.border,
          color: theme.ink,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-5 pt-4 pb-2 flex items-center justify-between gap-2">
          <span
            className="text-[11px] font-extrabold uppercase tracking-wider"
            style={{ color: theme.accent }}
          >
            Book Overview
          </span>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleShare}
              className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-[11px] font-bold transition hover:opacity-85 cursor-pointer"
              style={{
                backgroundColor: copiedLink ? theme.accentSoft : theme.surface,
                borderColor: copiedLink ? theme.accent : theme.border,
                color: copiedLink ? theme.accent : theme.ink,
              }}
            >
              {copiedLink ? (
                <Check className="w-3.5 h-3.5" />
              ) : (
                <Share2 className="w-3.5 h-3.5" />
              )}
              <span>{copiedLink ? "Link Copied!" : "Share"}</span>
            </button>

            <button
              type="button"
              onClick={onClose}
              aria-label="Close book detail"
              className="w-8 h-8 rounded-full border flex items-center justify-center transition hover:opacity-80 cursor-pointer"
              style={{
                backgroundColor: theme.surface,
                borderColor: theme.border,
                color: theme.ink,
              }}
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="overflow-y-auto px-5 pb-6 pt-2 space-y-4">
          {/* Top Book Overview */}
          <div className="flex gap-4">
            <BookCover
              book={book}
              theme={theme}
              isSaved={isSaved}
              className="w-[104px] sm:w-[114px] h-[154px] sm:h-[168px] shrink-0"
            />

            <div className="flex-1 min-w-0 space-y-2">
              <button
                type="button"
                onClick={() => {
                  onNavigateFolder(folderPath);
                  onClose();
                }}
                className="inline-flex items-center gap-1.5 text-left text-[11px] font-bold hover:underline cursor-pointer"
                style={{ color: theme.accent }}
                title="Open this category folder"
              >
                <FolderOpen className="w-3.5 h-3.5 shrink-0" />
                <span className="line-clamp-2">
                  {book.cat}
                  {book.sub ? ` / ${book.sub}` : ""}
                </span>
              </button>

              <h3 className="text-base sm:text-lg font-extrabold leading-snug line-clamp-3">
                {book.title}
              </h3>

              <button
                type="button"
                onClick={() => {
                  onFilterAuthor(book.author);
                  onClose();
                }}
                className="inline-flex items-center gap-2 text-left group cursor-pointer"
                title="Browse books by this author"
              >
                <AuthorAvatar name={book.author} size={26} theme={theme} />
                <span
                  className="text-xs sm:text-sm font-semibold group-hover:underline line-clamp-1"
                  style={{ color: theme.muted }}
                >
                  {book.author}
                </span>
              </button>

              <div className="flex flex-wrap gap-1.5 pt-1">
                <span
                  className="px-2.5 py-0.5 rounded-md text-[11px] font-bold"
                  style={{
                    backgroundColor: theme.surface,
                    color: theme.cream,
                  }}
                >
                  {book.fmt}
                </span>
                <span
                  className="px-2.5 py-0.5 rounded-md text-[11px] font-bold"
                  style={{
                    backgroundColor: theme.surface,
                    color: theme.cream,
                  }}
                >
                  {formatBytes(book.size)}
                </span>
                <span
                  className="px-2.5 py-0.5 rounded-md text-[11px] font-bold"
                  style={{
                    backgroundColor: theme.surface,
                    color: theme.cream,
                  }}
                >
                  {book.lang}
                </span>
              </div>
            </div>
          </div>

          {/* Primary Actions */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            <button
              type="button"
              onClick={() => onReadOnline(book)}
              className="w-full py-3 rounded-full flex items-center justify-center gap-2 text-sm font-extrabold transition hover:opacity-90 cursor-pointer"
              style={{
                backgroundColor: theme.cream,
                color: theme.creamInk,
              }}
            >
              <BookOpen className="w-4 h-4" />
              <span>Read Online</span>
            </button>

            <a
              href={getDownloadUrl(book.id)}
              target="_blank"
              rel="noopener noreferrer"
              className="w-full py-3 rounded-full flex items-center justify-center gap-2 text-sm font-extrabold transition hover:opacity-90"
              style={{
                backgroundColor: theme.accent,
                color: theme.creamInk,
              }}
            >
              <Download className="w-4 h-4" />
              <span>Download {book.fmt}</span>
            </a>
          </div>

          {/* Secondary Actions */}
          <div className="grid grid-cols-2 gap-2.5">
            <button
              type="button"
              onClick={() => onSetCurrentlyReading(book.id)}
              className="py-2.5 px-3 rounded-2xl border flex items-center justify-center gap-1.5 text-xs font-bold transition cursor-pointer"
              style={{
                backgroundColor: isCurrentRead
                  ? theme.accentSoft
                  : theme.surface,
                borderColor: isCurrentRead ? theme.accent : theme.border,
                color: theme.ink,
              }}
            >
              <CheckCircle2
                className="w-4 h-4"
                style={{ color: isCurrentRead ? theme.accent : theme.ink }}
              />
              <span>{isCurrentRead ? "Reading Now" : "Mark Current"}</span>
            </button>

            <button
              type="button"
              onClick={() => onToggleSave(book.id)}
              className="py-2.5 px-3 rounded-2xl border flex items-center justify-center gap-1.5 text-xs font-bold transition cursor-pointer"
              style={{
                backgroundColor: isSaved ? theme.accentSoft : theme.surface,
                borderColor: isSaved ? theme.accent : theme.border,
                color: theme.ink,
              }}
            >
              <Bookmark
                className="w-4 h-4"
                style={{ color: isSaved ? theme.accent : theme.ink }}
                fill={isSaved ? "currentColor" : "none"}
              />
              <span>{isSaved ? "Saved" : "Bookmark"}</span>
            </button>
          </div>

          {/* Add to Custom Collections */}
          <div
            className="rounded-2xl p-4 space-y-2.5 border"
            style={{
              backgroundColor: theme.surface,
              borderColor: theme.borderSubtle,
            }}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold inline-flex items-center gap-1.5">
                <FolderPlus
                  className="w-3.5 h-3.5"
                  style={{ color: theme.accent }}
                />
                <span>Reading Lists</span>
              </span>

              <button
                type="button"
                onClick={() => setShowNewCollection((v) => !v)}
                className="inline-flex items-center gap-1 text-[11px] font-extrabold hover:underline cursor-pointer"
                style={{ color: theme.accent }}
              >
                <Plus className="w-3 h-3" />
                <span>New List</span>
              </button>
            </div>

            {showNewCollection && (
              <form onSubmit={handleCreateCol} className="flex gap-2">
                <input
                  type="text"
                  value={newCollectionName}
                  onChange={(e) => setNewCollectionName(e.target.value)}
                  placeholder="e.g. BCS Prep, Weekend Fiction…"
                  className="flex-1 px-3 py-1.5 rounded-xl border text-xs focus:outline-none"
                  style={{
                    backgroundColor: theme.bg,
                    borderColor: theme.border,
                    color: theme.ink,
                  }}
                />
                <button
                  type="submit"
                  className="px-3 py-1.5 rounded-xl text-xs font-extrabold cursor-pointer"
                  style={{
                    backgroundColor: theme.cream,
                    color: theme.creamInk,
                  }}
                >
                  Create
                </button>
              </form>
            )}

            {collections.length === 0 ? (
              <p className="text-[11px]" style={{ color: theme.muted }}>
                No custom reading lists yet. Click &ldquo;New List&rdquo; to
                organize books.
              </p>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {collections.map((col) => {
                  const inCol = col.bookIds.includes(book.id);
                  return (
                    <button
                      key={col.id}
                      type="button"
                      onClick={() => onToggleCollectionBook(col.id, book.id)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full border text-[11px] font-bold transition cursor-pointer"
                      style={{
                        backgroundColor: inCol
                          ? theme.accentSoft
                          : theme.surfaceAlt,
                        borderColor: inCol ? theme.accent : theme.border,
                        color: inCol ? theme.accent : theme.ink,
                      }}
                    >
                      {inCol && <Check className="w-3 h-3" />}
                      <span>{col.name}</span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Reading Progress Editor */}
          <div
            className="rounded-2xl p-4 space-y-3 border"
            style={{
              backgroundColor: theme.surface,
              borderColor: theme.borderSubtle,
            }}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold">Reading Progress</span>
              <span
                className="text-xs font-extrabold tabular-nums"
                style={{ color: theme.accent }}
              >
                {pct}%{savedNotice ? " · Updated" : ""}
              </span>
            </div>

            <div
              className="w-full h-1.5 rounded-full overflow-hidden"
              style={{ backgroundColor: theme.surfaceAlt }}
            >
              <div
                className="h-full rounded-full transition-all"
                style={{
                  width: `${Math.min(100, Math.max(0, pct))}%`,
                  backgroundColor: theme.accent,
                }}
              />
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
                  value={currInput}
                  onChange={(e) => setCurrInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border text-xs sm:text-sm font-bold focus:outline-none"
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
                  value={totalInput}
                  onChange={(e) => setTotalInput(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border text-xs sm:text-sm font-bold focus:outline-none"
                  style={{
                    backgroundColor: theme.bg,
                    borderColor: theme.border,
                    color: theme.ink,
                  }}
                />
              </label>

              <button
                type="button"
                onClick={() => {
                  const c = Math.max(0, parseInt(currInput, 10) || 0);
                  const t = Math.max(1, parseInt(totalInput, 10) || 300);
                  onUpdateProgress(book.id, c, t);
                  setSavedNotice(true);
                }}
                className="px-4 py-2 rounded-xl text-xs font-extrabold transition hover:opacity-90 cursor-pointer"
                style={{
                  backgroundColor: theme.cream,
                  color: theme.creamInk,
                }}
              >
                Save
              </button>
            </div>
          </div>

          {/* Personal Study Note */}
          <div
            className="rounded-2xl p-4 space-y-2.5 border"
            style={{
              backgroundColor: theme.surface,
              borderColor: theme.borderSubtle,
            }}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold inline-flex items-center gap-1.5">
                <NotebookPen
                  className="w-3.5 h-3.5"
                  style={{ color: theme.accent }}
                />
                <span>Personal Study Note</span>
              </span>
              {noteSaved && (
                <span
                  className="text-[11px] font-bold"
                  style={{ color: theme.accent }}
                >
                  Saved
                </span>
              )}
            </div>

            <textarea
              rows={2}
              value={noteInput}
              onChange={(e) => {
                setNoteInput(e.target.value);
                setNoteSaved(false);
              }}
              placeholder="Write key takeaways, favorite quotes, or page reminders…"
              className="w-full px-3 py-2 rounded-xl border text-xs leading-relaxed focus:outline-none resize-y"
              style={{
                backgroundColor: theme.bg,
                borderColor: theme.border,
                color: theme.ink,
              }}
            />

            <div className="flex justify-end">
              <button
                type="button"
                onClick={() => {
                  onSaveNote(book.id, noteInput);
                  setNoteSaved(true);
                }}
                className="px-3.5 py-1.5 rounded-xl text-xs font-extrabold transition hover:opacity-90 cursor-pointer"
                style={{
                  backgroundColor: theme.cream,
                  color: theme.creamInk,
                }}
              >
                Save Note
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
