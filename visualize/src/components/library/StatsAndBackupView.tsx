"use client";

import React, { useMemo, useRef, useState } from "react";
import {
  Bookmark,
  BookOpen,
  CheckCircle2,
  Download,
  Flame,
  FolderHeart,
  NotebookPen,
  Upload,
} from "lucide-react";
import type { BookProgress, ThemeTokens } from "@/lib/anabookTheme";
import {
  BookNote,
  CustomCollection,
  exportUserLibraryJson,
  importUserLibraryJson,
  ReadingStreak,
  UserLibraryBackup,
} from "@/lib/userLibraryStore";
import { BookItem, formatBytes } from "@/types/library";
import { BookCover } from "./BookCover";

const WEEK_LETTERS = ["M", "T", "W", "T", "F", "S", "S"];

interface StatsAndBackupViewProps {
  books: BookItem[];
  savedIds: string[];
  progressById: Record<string, BookProgress>;
  notesById: Record<string, BookNote>;
  collections: CustomCollection[];
  streak: ReadingStreak;
  theme: ThemeTokens;
  onSelectCategory: (cat: string) => void;
  onOpenDetail: (book: BookItem) => void;
  onRestoreBackup: (backup: UserLibraryBackup) => void;
}

/**
 * Web port of AnaBook's StatsScreen featuring Reading Streak & Weekly Activity,
 * personal metrics, 29,178+ archive distribution charts, and JSON Backup/Restore.
 */
export function StatsAndBackupView({
  books,
  savedIds,
  progressById,
  notesById,
  collections,
  streak,
  theme,
  onSelectCategory,
  onOpenDetail,
  onRestoreBackup,
}: StatsAndBackupViewProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [backupMsg, setBackupMsg] = useState<string>("");
  const [backupErr, setBackupErr] = useState<string>("");

  const stats = useMemo(() => {
    let totalBytes = 0;
    const byCat = new Map<string, number>();
    const byEdu = new Map<string, number>();
    const byFmt = new Map<string, number>();
    const bookById = new Map<string, BookItem>();

    for (const b of books) {
      bookById.set(b.id, b);
      totalBytes += b.size;
      byCat.set(b.cat, (byCat.get(b.cat) || 0) + 1);
      if (b.cat === "Education & Textbooks") {
        const top = (b.sub || "Other").split("/")[0];
        byEdu.set(top, (byEdu.get(top) || 0) + 1);
      }
      byFmt.set(b.fmt, (byFmt.get(b.fmt) || 0) + 1);
    }

    const progressEntries = Object.values(progressById).sort((a, b) =>
      (b.updatedAt || "").localeCompare(a.updatedAt || "")
    );

    let completedCount = 0;
    let inProgressCount = 0;
    let totalPagesRead = 0;
    for (const p of progressEntries) {
      totalPagesRead += p.currentPage || 0;
      if (p.progressPct >= 100) completedCount++;
      else if (p.progressPct > 0 || p.currentPage > 0) inProgressCount++;
    }

    const recentProgressBooks = progressEntries
      .map((p) => {
        const book = bookById.get(p.bookId);
        return book ? { book, prog: p } : null;
      })
      .filter((x): x is { book: BookItem; prog: BookProgress } => Boolean(x))
      .slice(0, 6);

    const notesCount = Object.values(notesById).filter(
      (n) => n?.text?.trim().length > 0
    ).length;

    return {
      total: books.length,
      totalBytes,
      completedCount,
      inProgressCount,
      totalPagesRead,
      notesCount,
      recentProgressBooks,
      cats: [...byCat.entries()].sort((a, b) => b[1] - a[1]),
      edu: [...byEdu.entries()].sort((a, b) => b[1] - a[1]),
      fmts: [...byFmt.entries()].sort((a, b) => b[1] - a[1]).slice(0, 6),
    };
  }, [books, progressById, notesById]);

  const maxCat = stats.cats[0]?.[1] || 1;
  const maxEdu = stats.edu[0]?.[1] || 1;

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBackupErr("");
    setBackupMsg("");
    try {
      const restored = await importUserLibraryJson(file);
      onRestoreBackup(restored);
      setBackupMsg(
        `Restored ${restored.savedIds.length} saved books, ${
          Object.keys(restored.progressById).length
        } progress records, and ${restored.collections.length} reading lists.`
      );
    } catch (err) {
      setBackupErr(
        err instanceof Error ? err.message : "Unable to import backup file."
      );
    } finally {
      e.target.value = "";
    }
  };

  return (
    <div className="space-y-6">
      {/* Reading Streak & Weekly Activity Card */}
      <section
        className="rounded-3xl border p-5 sm:p-6 space-y-5"
        style={{
          backgroundColor: theme.surface,
          borderColor: theme.border,
        }}
      >
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-1">
            <p
              className="text-[10px] font-extrabold uppercase tracking-[0.1em]"
              style={{ color: theme.muted }}
            >
              Reading Streak
            </p>
            <div className="flex items-center gap-2">
              <Flame className="w-6 h-6" style={{ color: theme.accent }} />
              <span className="text-2xl font-extrabold">
                {streak.days} {streak.days === 1 ? "day" : "days"}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {WEEK_LETTERS.map((letter, idx) => {
              const active = Boolean(streak.activeWeekdays?.[idx]);
              return (
                <div
                  key={`${letter}-${idx}`}
                  className="w-8 h-8 rounded-full border flex items-center justify-center text-xs font-extrabold transition"
                  style={{
                    backgroundColor: active ? theme.accent : theme.surfaceAlt,
                    borderColor: active ? theme.accent : theme.border,
                    color: active ? theme.creamInk : theme.muted,
                  }}
                >
                  {letter}
                </div>
              );
            })}
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          {[
            {
              label: "Saved",
              val: savedIds.length.toLocaleString(),
              Icon: Bookmark,
            },
            {
              label: "In Progress",
              val: stats.inProgressCount.toLocaleString(),
              Icon: BookOpen,
            },
            {
              label: "Completed",
              val: stats.completedCount.toLocaleString(),
              Icon: CheckCircle2,
            },
            {
              label: "Study Notes",
              val: stats.notesCount.toLocaleString(),
              Icon: NotebookPen,
            },
            {
              label: "Reading Lists",
              val: collections.length.toLocaleString(),
              Icon: FolderHeart,
            },
          ].map(({ label, val, Icon }) => (
            <div
              key={label}
              className="rounded-2xl border p-3.5 space-y-1"
              style={{
                backgroundColor: theme.surfaceAlt,
                borderColor: theme.borderSubtle,
              }}
            >
              <div className="flex items-center justify-between">
                <span
                  className="text-[11px] font-semibold"
                  style={{ color: theme.muted }}
                >
                  {label}
                </span>
                <Icon className="w-3.5 h-3.5" style={{ color: theme.accent }} />
              </div>
              <p className="text-lg font-extrabold tabular-nums">{val}</p>
            </div>
          ))}
        </div>

        <p className="text-xs font-semibold" style={{ color: theme.muted }}>
          Total pages logged:{" "}
          <strong style={{ color: theme.ink }}>
            {stats.totalPagesRead.toLocaleString()}
          </strong>{" "}
          · Active reader time:{" "}
          <strong style={{ color: theme.ink }}>
            {streak.totalMinutes.toLocaleString()} min
          </strong>
        </p>
      </section>

      {/* Portable Backup & Restore */}
      <section
        className="rounded-3xl border p-5 sm:p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
        style={{
          backgroundColor: theme.surface,
          borderColor: theme.border,
        }}
      >
        <div className="space-y-1 max-w-xl">
          <h3 className="text-sm sm:text-base font-extrabold">
            Portable Library Backup &amp; Restore
          </h3>
          <p className="text-xs leading-relaxed" style={{ color: theme.muted }}>
            Export your saved bookmarks, reading progress, study notes, custom
            lists, streak, and theme settings as JSON—or restore them on any
            browser.
          </p>
          {backupMsg && (
            <p className="text-xs font-bold pt-1" style={{ color: theme.accent }}>
              {backupMsg}
            </p>
          )}
          {backupErr && (
            <p className="text-xs font-bold pt-1" style={{ color: theme.danger }}>
              {backupErr}
            </p>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2.5 shrink-0">
          <button
            type="button"
            onClick={() => {
              exportUserLibraryJson();
              setBackupErr("");
              setBackupMsg("Downloaded JSON backup file.");
            }}
            className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-full text-xs font-extrabold transition hover:opacity-90 cursor-pointer"
            style={{
              backgroundColor: theme.cream,
              color: theme.creamInk,
            }}
          >
            <Download className="w-3.5 h-3.5" style={{ color: theme.accent }} />
            <span>Export Backup (.json)</span>
          </button>

          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-full border text-xs font-bold transition hover:opacity-85 cursor-pointer"
            style={{
              backgroundColor: theme.surfaceAlt,
              borderColor: theme.border,
              color: theme.ink,
            }}
          >
            <Upload className="w-3.5 h-3.5" />
            <span>Import Backup</span>
          </button>

          <input
            ref={fileInputRef}
            type="file"
            accept=".json,application/json"
            onChange={handleImport}
            className="hidden"
          />
        </div>
      </section>

      {/* Recent Progress Strip */}
      {stats.recentProgressBooks.length > 0 && (
        <section className="space-y-3">
          <h3 className="text-sm sm:text-base font-extrabold">
            Recent Reading Activity
          </h3>
          <div className="flex items-stretch gap-3 overflow-x-auto pb-1.5 no-scrollbar">
            {stats.recentProgressBooks.map(({ book, prog }) => (
              <button
                key={book.id}
                type="button"
                onClick={() => onOpenDetail(book)}
                className="w-40 shrink-0 rounded-2xl border p-3 text-left space-y-2 transition hover:-translate-y-0.5 cursor-pointer"
                style={{
                  backgroundColor: theme.surface,
                  borderColor: theme.border,
                }}
              >
                <BookCover
                  book={book}
                  theme={theme}
                  compact
                  className="w-full aspect-[2/3]"
                />
                <div className="space-y-1">
                  <p className="text-xs font-extrabold line-clamp-2 leading-snug">
                    {book.title}
                  </p>
                  <p
                    className="text-[10px] font-bold"
                    style={{ color: theme.accent }}
                  >
                    {prog.progressPct}% · p. {prog.currentPage}/
                    {prog.totalPages}
                  </p>
                </div>
              </button>
            ))}
          </div>
        </section>
      )}

      {/* Archive Distribution Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Categories Breakdown */}
        <section
          className="rounded-3xl border p-5 sm:p-6 space-y-4"
          style={{
            backgroundColor: theme.surface,
            borderColor: theme.border,
          }}
        >
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-extrabold">
              Archive by Category ({stats.total.toLocaleString()} Books)
            </h3>
            <span className="text-xs font-bold" style={{ color: theme.muted }}>
              {formatBytes(stats.totalBytes)}
            </span>
          </div>

          <div className="space-y-2.5">
            {stats.cats.map(([cat, count]) => {
              const widthPct = Math.max(4, Math.round((count / maxCat) * 100));
              return (
                <button
                  key={cat}
                  type="button"
                  onClick={() => onSelectCategory(cat)}
                  className="w-full text-left space-y-1 group cursor-pointer"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold group-hover:underline">
                      {cat}
                    </span>
                    <span
                      className="font-extrabold tabular-nums"
                      style={{ color: theme.accent }}
                    >
                      {count.toLocaleString()}
                    </span>
                  </div>
                  <div
                    className="h-2 rounded-full overflow-hidden"
                    style={{ backgroundColor: theme.surfaceAlt }}
                  >
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${widthPct}%`,
                        backgroundColor: theme.accent,
                      }}
                    />
                  </div>
                </button>
              );
            })}
          </div>
        </section>

        {/* Education & Formats Breakdown */}
        <div className="space-y-5">
          <section
            className="rounded-3xl border p-5 sm:p-6 space-y-3.5"
            style={{
              backgroundColor: theme.surface,
              borderColor: theme.border,
            }}
          >
            <h3 className="text-sm font-extrabold">
              Education &amp; Textbooks Breakdown
            </h3>
            <div className="space-y-2.5">
              {stats.edu.map(([sub, count]) => {
                const widthPct = Math.max(
                  4,
                  Math.round((count / maxEdu) * 100)
                );
                return (
                  <div key={sub} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold">{sub}</span>
                      <span
                        className="font-extrabold tabular-nums"
                        style={{ color: theme.accent }}
                      >
                        {count.toLocaleString()}
                      </span>
                    </div>
                    <div
                      className="h-2 rounded-full overflow-hidden"
                      style={{ backgroundColor: theme.surfaceAlt }}
                    >
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${widthPct}%`,
                          backgroundColor: theme.sage,
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </section>

          <section
            className="rounded-3xl border p-5 sm:p-6 space-y-3"
            style={{
              backgroundColor: theme.surface,
              borderColor: theme.border,
            }}
          >
            <h3 className="text-sm font-extrabold">Supported File Formats</h3>
            <div className="flex flex-wrap gap-2">
              {stats.fmts.map(([fmt, count]) => (
                <div
                  key={fmt}
                  className="px-3.5 py-2 rounded-2xl border flex items-center gap-2"
                  style={{
                    backgroundColor: theme.surfaceAlt,
                    borderColor: theme.border,
                  }}
                >
                  <span className="text-xs font-extrabold">{fmt}</span>
                  <span
                    className="text-xs font-bold tabular-nums"
                    style={{ color: theme.accent }}
                  >
                    {count.toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
