"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  Bookmark,
  BookOpen,
  Download,
  LayoutGrid,
  List,
} from "lucide-react";
import type { BookProgress, ThemeTokens } from "@/lib/anabookTheme";
import { BookItem, formatBytes, getDownloadUrl } from "@/types/library";
import { BookCover } from "./BookCover";

const DEFAULT_PAGE_SIZE = 48;

interface BookCollectionViewProps {
  books: BookItem[];
  savedSet: Set<string>;
  theme: ThemeTokens;
  progressById: Record<string, BookProgress>;
  emptyTitle?: string;
  emptySubtitle?: string;
  initialPageSize?: number;
  hideFormatFilter?: boolean;
  onOpenDetail: (book: BookItem) => void;
  onQuickRead: (book: BookItem) => void;
  onToggleSave: (bookId: string) => void;
}

/**
 * Shared AnaBook book browser supporting format filtering, sorting, Grid/List toggle,
 * cloth-bound covers, quick Read/Download/Bookmark actions, and pagination.
 */
export function BookCollectionView({
  books,
  savedSet,
  theme,
  progressById,
  emptyTitle = "No matching books found",
  emptySubtitle = "Try clearing a filter or searching another keyword.",
  initialPageSize = DEFAULT_PAGE_SIZE,
  hideFormatFilter = false,
  onOpenDetail,
  onQuickRead,
  onToggleSave,
}: BookCollectionViewProps) {
  const [selectedFmt, setSelectedFmt] = useState("ALL");
  const [sortMode, setSortMode] = useState<"covers" | "title" | "size">(
    "covers"
  );
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [visibleCount, setVisibleCount] = useState(initialPageSize);

  const processed = useMemo(() => {
    const list = books.filter((b) =>
      selectedFmt === "ALL" ? true : b.fmt === selectedFmt
    );
    if (sortMode === "covers") {
      list.sort(
        (a, b) =>
          Number(Boolean(b.coverId)) - Number(Boolean(a.coverId)) ||
          a.title.localeCompare(b.title)
      );
    } else if (sortMode === "size") {
      list.sort((a, b) => b.size - a.size);
    } else {
      list.sort((a, b) => a.title.localeCompare(b.title));
    }
    return list;
  }, [books, selectedFmt, sortMode]);

  useEffect(() => {
    setVisibleCount(initialPageSize);
  }, [books, selectedFmt, sortMode, initialPageSize]);

  const shown = processed.slice(0, visibleCount);

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2.5">
        <span
          className="text-xs font-semibold"
          style={{ color: theme.muted }}
        >
          Showing{" "}
          <strong style={{ color: theme.ink }}>
            {shown.length.toLocaleString()}
          </strong>{" "}
          of{" "}
          <strong style={{ color: theme.ink }}>
            {processed.length.toLocaleString()}
          </strong>{" "}
          books
        </span>

        <div className="flex flex-wrap items-center gap-2">
          {!hideFormatFilter && (
            <select
              value={selectedFmt}
              onChange={(e) => setSelectedFmt(e.target.value)}
              aria-label="Filter by format"
              className="px-3 py-1.5 rounded-full border text-xs font-bold focus:outline-none cursor-pointer"
              style={{
                backgroundColor: theme.surface,
                borderColor: theme.border,
                color: theme.ink,
              }}
            >
              <option value="ALL">All Formats</option>
              <option value="PDF">PDF</option>
              <option value="EPUB">EPUB</option>
              <option value="MOBI">MOBI</option>
              <option value="DOCX">DOCX</option>
            </select>
          )}

          <select
            value={sortMode}
            onChange={(e) =>
              setSortMode(e.target.value as "covers" | "title" | "size")
            }
            aria-label="Sort books"
            className="px-3 py-1.5 rounded-full border text-xs font-bold focus:outline-none cursor-pointer"
            style={{
              backgroundColor: theme.surface,
              borderColor: theme.border,
              color: theme.ink,
            }}
          >
            <option value="covers">Covers First</option>
            <option value="title">Title A–Z</option>
            <option value="size">Largest First</option>
          </select>

          <div
            className="inline-flex items-center rounded-xl border p-0.5 gap-0.5"
            style={{
              backgroundColor: theme.surfaceAlt,
              borderColor: theme.border,
            }}
            role="group"
            aria-label="View mode"
          >
            {(
              [
                { key: "grid", label: "Grid", Icon: LayoutGrid },
                { key: "list", label: "List", Icon: List },
              ] as const
            ).map(({ key, label, Icon }) => {
              const active = viewMode === key;
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => setViewMode(key)}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-[9px] text-[11px] font-bold transition cursor-pointer"
                  style={{
                    backgroundColor: active ? theme.cream : "transparent",
                    color: active ? theme.creamInk : theme.muted,
                  }}
                >
                  <Icon className="w-3.5 h-3.5" />
                  <span>{label}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Empty State */}
      {shown.length === 0 ? (
        <div
          className="rounded-3xl border py-14 px-4 text-center space-y-1.5"
          style={{
            backgroundColor: theme.surfaceAlt,
            borderColor: theme.borderSubtle,
          }}
        >
          <p className="text-sm sm:text-base font-extrabold">{emptyTitle}</p>
          <p className="text-xs" style={{ color: theme.muted }}>
            {emptySubtitle}
          </p>
        </div>
      ) : viewMode === "grid" ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3.5 sm:gap-4">
          {shown.map((book) => {
            const isSaved = savedSet.has(book.id);
            const prog = progressById[book.id];
            return (
              <div
                key={book.id}
                className="group rounded-2xl border p-2.5 flex flex-col gap-2 transition hover:-translate-y-0.5"
                style={{
                  backgroundColor: theme.surface,
                  borderColor: theme.border,
                }}
              >
                <button
                  type="button"
                  onClick={() => onOpenDetail(book)}
                  className="aspect-[2/3] w-full cursor-pointer text-left"
                  aria-label={`Inspect ${book.title}`}
                >
                  <BookCover
                    book={book}
                    theme={theme}
                    isSaved={isSaved}
                    showFormatBadge
                    className="w-full h-full transition-transform duration-300 group-hover:scale-[1.02]"
                  />
                </button>

                <div className="flex-1 flex flex-col justify-between gap-2">
                  <div>
                    <h3
                      className="text-xs font-extrabold line-clamp-2 leading-snug cursor-pointer hover:underline"
                      title={book.title}
                      onClick={() => onOpenDetail(book)}
                    >
                      {book.title}
                    </h3>
                    <p
                      className="text-[11px] line-clamp-1 mt-0.5"
                      style={{ color: theme.muted }}
                    >
                      {book.author}
                    </p>
                    {prog && prog.progressPct > 0 ? (
                      <div className="mt-1.5 space-y-0.5">
                        <div
                          className="h-1 w-full rounded-full overflow-hidden"
                          style={{ backgroundColor: theme.surfaceAlt }}
                        >
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${Math.min(100, prog.progressPct)}%`,
                              backgroundColor: theme.accent,
                            }}
                          />
                        </div>
                      </div>
                    ) : null}
                  </div>

                  <div className="flex items-center gap-1.5 pt-0.5">
                    <button
                      type="button"
                      onClick={() => onQuickRead(book)}
                      className="flex-1 inline-flex items-center justify-center gap-1 py-1.5 rounded-full text-[11px] font-extrabold transition hover:opacity-90 cursor-pointer"
                      style={{
                        backgroundColor: theme.cream,
                        color: theme.creamInk,
                      }}
                    >
                      <BookOpen
                        className="w-3 h-3"
                        style={{ color: theme.accent }}
                      />
                      <span>Read</span>
                    </button>

                    <a
                      href={getDownloadUrl(book.id)}
                      target="_blank"
                      rel="noopener noreferrer"
                      title={`Download (${formatBytes(book.size)})`}
                      aria-label={`Download ${book.title}`}
                      className="w-7 h-7 rounded-full border flex items-center justify-center transition shrink-0 hover:opacity-80"
                      style={{
                        backgroundColor: theme.surfaceAlt,
                        borderColor: theme.border,
                        color: theme.ink,
                      }}
                    >
                      <Download className="w-3.5 h-3.5" />
                    </a>

                    <button
                      type="button"
                      onClick={() => onToggleSave(book.id)}
                      title={isSaved ? "Remove bookmark" : "Bookmark"}
                      aria-label={
                        isSaved
                          ? `Remove bookmark for ${book.title}`
                          : `Bookmark ${book.title}`
                      }
                      className="w-7 h-7 rounded-full border flex items-center justify-center transition shrink-0 cursor-pointer"
                      style={{
                        backgroundColor: isSaved
                          ? theme.accentSoft
                          : theme.surfaceAlt,
                        borderColor: isSaved ? theme.accent : theme.border,
                        color: isSaved ? theme.accent : theme.muted,
                      }}
                    >
                      <Bookmark
                        className="w-3.5 h-3.5"
                        fill={isSaved ? "currentColor" : "none"}
                      />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {shown.map((book) => {
            const isSaved = savedSet.has(book.id);
            const prog = progressById[book.id];
            return (
              <div
                key={book.id}
                className="rounded-2xl border p-3 flex gap-3.5 items-stretch transition"
                style={{
                  backgroundColor: theme.surface,
                  borderColor: theme.border,
                }}
              >
                <button
                  type="button"
                  onClick={() => onOpenDetail(book)}
                  className="w-[62px] h-[92px] shrink-0 cursor-pointer"
                  aria-label={`Inspect ${book.title}`}
                >
                  <BookCover
                    book={book}
                    theme={theme}
                    isSaved={isSaved}
                    compact
                    className="w-full h-full"
                  />
                </button>

                <div className="flex-1 min-w-0 flex flex-col justify-between gap-1.5">
                  <div>
                    <h3
                      className="text-xs sm:text-sm font-extrabold line-clamp-2 leading-snug cursor-pointer hover:underline"
                      onClick={() => onOpenDetail(book)}
                    >
                      {book.title}
                    </h3>
                    <p
                      className="text-[11px] line-clamp-1 mt-0.5"
                      style={{ color: theme.muted }}
                    >
                      {book.author} · {book.fmt} · {formatBytes(book.size)}
                    </p>
                    {prog && prog.progressPct > 0 ? (
                      <p
                        className="text-[10px] font-bold mt-0.5"
                        style={{ color: theme.accent }}
                      >
                        Progress: {prog.progressPct}% (p. {prog.currentPage}/
                        {prog.totalPages})
                      </p>
                    ) : null}
                  </div>

                  <div className="flex items-center gap-2 pt-1">
                    <button
                      type="button"
                      onClick={() => onQuickRead(book)}
                      className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-[11px] font-extrabold transition hover:opacity-90 cursor-pointer"
                      style={{
                        backgroundColor: theme.cream,
                        color: theme.creamInk,
                      }}
                    >
                      <BookOpen
                        className="w-3.5 h-3.5"
                        style={{ color: theme.accent }}
                      />
                      <span>Read</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => onOpenDetail(book)}
                      className="px-3 py-1.5 rounded-full border text-[11px] font-bold transition hover:opacity-85 cursor-pointer"
                      style={{
                        backgroundColor: theme.surfaceAlt,
                        borderColor: theme.border,
                        color: theme.ink,
                      }}
                    >
                      Details
                    </button>

                    <a
                      href={getDownloadUrl(book.id)}
                      target="_blank"
                      rel="noopener noreferrer"
                      title={`Download (${formatBytes(book.size)})`}
                      className="w-7 h-7 rounded-full border flex items-center justify-center transition"
                      style={{
                        backgroundColor: theme.surfaceAlt,
                        borderColor: theme.border,
                        color: theme.ink,
                      }}
                    >
                      <Download className="w-3.5 h-3.5" />
                    </a>

                    <button
                      type="button"
                      onClick={() => onToggleSave(book.id)}
                      title={isSaved ? "Remove bookmark" : "Bookmark"}
                      className="w-7 h-7 rounded-full border flex items-center justify-center transition cursor-pointer"
                      style={{
                        backgroundColor: isSaved
                          ? theme.accentSoft
                          : theme.surfaceAlt,
                        borderColor: isSaved ? theme.accent : theme.border,
                        color: isSaved ? theme.accent : theme.muted,
                      }}
                    >
                      <Bookmark
                        className="w-3.5 h-3.5"
                        fill={isSaved ? "currentColor" : "none"}
                      />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Load More Pagination */}
      {visibleCount < processed.length && (
        <div className="flex justify-center pt-3">
          <button
            type="button"
            onClick={() => setVisibleCount((c) => c + initialPageSize)}
            className="w-full sm:w-auto px-6 py-2.5 sm:py-3 rounded-full text-xs sm:text-sm font-extrabold transition hover:opacity-90 cursor-pointer"
            style={{
              backgroundColor: theme.cream,
              color: theme.creamInk,
            }}
          >
            Load More Books (
            {(processed.length - visibleCount).toLocaleString()} remaining)
          </button>
        </div>
      )}
    </div>
  );
}
