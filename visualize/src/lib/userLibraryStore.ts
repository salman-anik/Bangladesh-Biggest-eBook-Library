"use client";

import type {
  BookProgress,
  ThemeMode,
  ThemePresetKey,
} from "@/lib/anabookTheme";

export interface ReadingStreak {
  days: number;
  lastReadDate: string;
  activeWeekdays: boolean[];
  totalMinutes: number;
}

export interface BookNote {
  text: string;
  updatedAt: string;
}

export interface CustomCollection {
  id: string;
  name: string;
  bookIds: string[];
  createdAt: string;
}

export interface UserLibraryBackup {
  version: number;
  exportedAt: string;
  savedIds: string[];
  progressById: Record<string, BookProgress>;
  currentReadId: string | null;
  recentIds: string[];
  notesById: Record<string, BookNote>;
  collections: CustomCollection[];
  streak: ReadingStreak;
  theme?: { preset: ThemePresetKey; mode: ThemeMode };
}

export const STORAGE_KEYS = {
  SAVED: "anabook_saved_v1",
  THEME: "anabook_web_theme_v1",
  PROGRESS: "anabook_progress_v1",
  CURRENT_READ: "anabook_current_read_v1",
  STREAK: "anabook_streak_v1",
  RECENT: "anabook_recent_v1",
  NOTES: "anabook_notes_v1",
  COLLECTIONS: "anabook_collections_v1",
} as const;

export const DEFAULT_STREAK: ReadingStreak = {
  days: 0,
  lastReadDate: "",
  activeWeekdays: [false, false, false, false, false, false, false],
  totalMinutes: 0,
};

function todayIsoDate(now = new Date()): string {
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function mondayIndex(now = new Date()): number {
  return (now.getDay() + 6) % 7;
}

export function safeReadJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

export function safeWriteJson(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Ignore storage quota errors
  }
}

/**
 * Updates the user's consecutive daily reading streak, active weekdays (Mon-Sun),
 * and accumulated reading minutes.
 */
export function recordReadingActivity(
  prev: ReadingStreak,
  minutesDelta = 0
): ReadingStreak {
  const now = new Date();
  const today = todayIsoDate(now);
  const idx = mondayIndex(now);
  const nextWeek = Array.isArray(prev.activeWeekdays) &&
    prev.activeWeekdays.length === 7
    ? [...prev.activeWeekdays]
    : [false, false, false, false, false, false, false];
  nextWeek[idx] = true;

  let nextDays = prev.days || 0;
  if (!prev.lastReadDate) {
    nextDays = 1;
  } else if (prev.lastReadDate !== today) {
    const prevDate = new Date(`${prev.lastReadDate}T00:00:00`);
    const todayDate = new Date(`${today}T00:00:00`);
    const diffDays = Math.round(
      (todayDate.getTime() - prevDate.getTime()) / 86400000
    );
    nextDays = diffDays === 1 ? Math.max(1, prev.days + 1) : 1;
  } else if (nextDays === 0) {
    nextDays = 1;
  }

  const next: ReadingStreak = {
    days: nextDays,
    lastReadDate: today,
    activeWeekdays: nextWeek,
    totalMinutes: Math.max(0, (prev.totalMinutes || 0) + minutesDelta),
  };
  safeWriteJson(STORAGE_KEYS.STREAK, next);
  return next;
}

/**
 * Prepends a bookId to the recently viewed list (max 16 unique items).
 */
export function pushRecentBookId(prev: string[], bookId: string): string[] {
  const next = [bookId, ...prev.filter((id) => id !== bookId)].slice(0, 16);
  safeWriteJson(STORAGE_KEYS.RECENT, next);
  return next;
}

/**
 * Builds a shareable deep link URL pointing directly to a book on /library/.
 */
export function buildBookShareUrl(bookId: string): string {
  if (typeof window === "undefined") {
    return `https://anabook-bd.vercel.app/library/?book=${encodeURIComponent(bookId)}`;
  }
  const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";
  return `${window.location.origin}${basePath}/library/?book=${encodeURIComponent(bookId)}`;
}

/**
 * Exports all AnaBook user state (bookmarks, progress, notes, collections, streak, theme)
 * as a downloadable JSON backup file.
 */
export function exportUserLibraryJson(): void {
  const backup: UserLibraryBackup = {
    version: 1,
    exportedAt: new Date().toISOString(),
    savedIds: safeReadJson<string[]>(STORAGE_KEYS.SAVED, []),
    progressById: safeReadJson<Record<string, BookProgress>>(
      STORAGE_KEYS.PROGRESS,
      {}
    ),
    currentReadId:
      typeof localStorage !== "undefined"
        ? localStorage.getItem(STORAGE_KEYS.CURRENT_READ)
        : null,
    recentIds: safeReadJson<string[]>(STORAGE_KEYS.RECENT, []),
    notesById: safeReadJson<Record<string, BookNote>>(STORAGE_KEYS.NOTES, {}),
    collections: safeReadJson<CustomCollection[]>(
      STORAGE_KEYS.COLLECTIONS,
      []
    ),
    streak: safeReadJson<ReadingStreak>(STORAGE_KEYS.STREAK, DEFAULT_STREAK),
    theme: safeReadJson<{ preset: ThemePresetKey; mode: ThemeMode } | undefined>(
      STORAGE_KEYS.THEME,
      undefined
    ),
  };

  const dateTag = todayIsoDate();
  const blob = new Blob([JSON.stringify(backup, null, 2)], {
    type: "application/json;charset=utf-8",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `anabook-backup-${dateTag}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/**
 * Parses and restores an exported AnaBook JSON backup into localStorage.
 */
export async function importUserLibraryJson(
  file: File
): Promise<UserLibraryBackup> {
  const text = await file.text();
  const parsed = JSON.parse(text) as Partial<UserLibraryBackup>;
  if (!parsed || typeof parsed !== "object") {
    throw new Error("Invalid backup file format.");
  }

  const restored: UserLibraryBackup = {
    version: Number(parsed.version) || 1,
    exportedAt: parsed.exportedAt || new Date().toISOString(),
    savedIds: Array.isArray(parsed.savedIds)
      ? parsed.savedIds.filter((x): x is string => typeof x === "string")
      : [],
    progressById:
      parsed.progressById && typeof parsed.progressById === "object"
        ? parsed.progressById
        : {},
    currentReadId:
      typeof parsed.currentReadId === "string" ? parsed.currentReadId : null,
    recentIds: Array.isArray(parsed.recentIds)
      ? parsed.recentIds.filter((x): x is string => typeof x === "string")
      : [],
    notesById:
      parsed.notesById && typeof parsed.notesById === "object"
        ? parsed.notesById
        : {},
    collections: Array.isArray(parsed.collections) ? parsed.collections : [],
    streak:
      parsed.streak && typeof parsed.streak === "object"
        ? parsed.streak
        : DEFAULT_STREAK,
    theme: parsed.theme,
  };

  safeWriteJson(STORAGE_KEYS.SAVED, restored.savedIds);
  safeWriteJson(STORAGE_KEYS.PROGRESS, restored.progressById);
  if (restored.currentReadId) {
    try {
      localStorage.setItem(STORAGE_KEYS.CURRENT_READ, restored.currentReadId);
    } catch {
      // Ignore
    }
  }
  safeWriteJson(STORAGE_KEYS.RECENT, restored.recentIds);
  safeWriteJson(STORAGE_KEYS.NOTES, restored.notesById);
  safeWriteJson(STORAGE_KEYS.COLLECTIONS, restored.collections);
  safeWriteJson(STORAGE_KEYS.STREAK, restored.streak);
  if (restored.theme) {
    safeWriteJson(STORAGE_KEYS.THEME, restored.theme);
  }

  return restored;
}
