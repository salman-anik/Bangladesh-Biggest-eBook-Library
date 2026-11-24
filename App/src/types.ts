export type TabKey = 'home' | 'library' | 'explore' | 'search' | 'more';

export type ThemeMode = 'dark' | 'light';

export type FontScaleKey = 'small' | 'normal' | 'large';

export type ThemePresetKey = 'espresso' | 'matcha' | 'midnight' | 'sepia' | 'rosewood';

export interface CompactCatalog {
  v: number;
  generated_at: string;
  total: number;
  total_bytes: number;
  covers_count: number;
  authors_count: number;
  drive_roots: Record<string, string>;
  cats: string[];
  subs: string[];
  langs: string[];
  fmts: string[];
  books: [
    string, // 0: drive_file_id
    string, // 1: title
    string, // 2: author
    number, // 3: catIdx
    number, // 4: subIdx
    number, // 5: langIdx
    number, // 6: fmtIdx
    number, // 7: sizeBytes
    string, // 8: coverDriveId
    string, // 9: series
  ][];
}

export interface Book {
  id: string;
  title: string;
  author: string;
  cat: string;
  sub: string;
  lang: string;
  fmt: string;
  size: number;
  coverId: string;
  series: string;
  searchBlob: string;
}

export interface BookProgress {
  bookId: string;
  currentPage: number;
  totalPages: number;
  progressPct: number;
  updatedAt: string;
}

export interface OfflineBookEntry {
  bookId: string;
  title: string;
  author: string;
  cat: string;
  sub: string;
  fmt: string;
  localUri: string;
  coverLocalUri?: string;
  size: number;
  downloadedAt: string;
}

export interface ReadingStreak {
  days: number;
  lastReadDate: string; // YYYY-MM-DD
  weekDaysActive: number[]; // indices 0..6 (Mon..Sun) active this week
}

export interface AppPersistedState {
  currentlyReadingId: string | null;
  progressById: Record<string, BookProgress>;
  offlineById: Record<string, OfflineBookEntry>;
  savedIds: string[];
  streak: ReadingStreak;
  themeMode?: ThemeMode;
  fontScale?: FontScaleKey;
  themePreset?: ThemePresetKey;
}

export interface BatchDownloadStatus {
  folderName: string;
  total: number;
  completed: number;
  failed: number;
  currentTitle: string;
}
