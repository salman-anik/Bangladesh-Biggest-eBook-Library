import AsyncStorage from '@react-native-async-storage/async-storage';
import * as FileSystem from 'expo-file-system/legacy';
import * as IntentLauncher from 'expo-intent-launcher';
import * as Sharing from 'expo-sharing';
import { Platform } from 'react-native';

import type {
  AppPersistedState,
  Book,
  BookProgress,
  CompactCatalog,
  OfflineBookEntry,
  ReadingStreak,
} from '../types';

const REMOTE_CATALOG_URL =
  'https://salman-anik.github.io/Bangladesh-Biggest-eBook-Library/books.json';

// eslint-disable-next-line @typescript-eslint/no-var-requires
const STARTER_CATALOG = require('../../assets/starter_books.json') as CompactCatalog;

const BASE_DIR = FileSystem.documentDirectory ?? '';
const CATALOG_CACHE_PATH = `${BASE_DIR}books_cache_v2.json`;
const OFFLINE_BOOKS_DIR = `${BASE_DIR}offline_books/`;
const OFFLINE_COVERS_DIR = `${BASE_DIR}offline_covers/`;

const STORAGE_STATE_KEY = 'bd_ebook_app_state_v1';
const STORAGE_CATALOG_META_KEY = 'bd_ebook_catalog_meta_v1';

const MIME_BY_FMT: Record<string, string> = {
  PDF: 'application/pdf',
  EPUB: 'application/epub+zip',
  MOBI: 'application/x-mobipocket-ebook',
  DOC: 'application/msword',
  DOCX: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  TXT: 'text/plain',
  JPG: 'image/jpeg',
  JPEG: 'image/jpeg',
  PNG: 'image/png',
};

export interface CatalogMeta {
  source: 'starter' | 'cache' | 'network';
  syncedAt: string;
  totalBooks: number;
  totalBytes: number;
  coversCount: number;
  authorsCount: number;
  driveRoots: Record<string, string>;
  cats: string[];
}

export function formatBytes(bytes: number): string {
  const n = Number(bytes) || 0;
  if (n <= 0) return '—';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let v = n;
  for (let i = 0; i < units.length; i++) {
    if (v < 1000 || i === units.length - 1) {
      return `${i <= 1 ? Math.round(v) : v.toFixed(1)} ${units[i]}`;
    }
    v /= 1000;
  }
  return `${n} B`;
}

export function getThumbnailUrl(book: Book, fallback = false): string {
  const isImage = ['JPG', 'JPEG', 'PNG'].includes(book.fmt.toUpperCase());
  const thumbId = book.coverId || (isImage ? book.id : '');
  if (!thumbId) return '';
  return fallback
    ? `https://lh3.googleusercontent.com/d/${encodeURIComponent(thumbId)}=w400`
    : `https://drive.google.com/thumbnail?id=${encodeURIComponent(thumbId)}&sz=w400`;
}

export function inflateCatalog(data: CompactCatalog): { books: Book[]; meta: Omit<CatalogMeta, 'source' | 'syncedAt'> } {
  const { cats = [], subs = [], langs = [], fmts = [], books = [] } = data;
  const inflated: Book[] = books.map((r) => {
    const id = r[0] || '';
    const title = r[1] || 'Untitled';
    const author = r[2] || 'Unknown';
    const cat = cats[r[3]] || 'Other';
    const sub = subs[r[4]] || '';
    const lang = langs[r[5]] || 'Unknown';
    const fmt = (fmts[r[6]] || 'PDF').toUpperCase();
    const size = Number(r[7]) || 0;
    const coverId = r[8] || '';
    const series = r[9] || '';
    return {
      id,
      title,
      author,
      cat,
      sub,
      lang,
      fmt,
      size,
      coverId,
      series,
      searchBlob: `${title} ${author} ${cat} ${sub} ${series} ${fmt} ${lang}`.toLowerCase(),
    };
  });

  return {
    books: inflated,
    meta: {
      totalBooks: data.total || inflated.length,
      totalBytes: data.total_bytes || 0,
      coversCount: data.covers_count || 0,
      authorsCount: data.authors_count || 0,
      driveRoots: data.drive_roots || {},
      cats: cats.filter((c) => c && c !== 'Library Management'),
    },
  };
}

async function ensureDirs(): Promise<void> {
  if (!BASE_DIR) return;
  for (const dir of [OFFLINE_BOOKS_DIR, OFFLINE_COVERS_DIR]) {
    const info = await FileSystem.getInfoAsync(dir);
    if (!info.exists) {
      await FileSystem.makeDirectoryAsync(dir, { intermediates: true });
    }
  }
}

export async function loadCachedOrStarterCatalog(): Promise<{ books: Book[]; meta: CatalogMeta }> {
  try {
    if (BASE_DIR) {
      const info = await FileSystem.getInfoAsync(CATALOG_CACHE_PATH);
      if (info.exists && (info.size ?? 0) > 1000) {
        const raw = await FileSystem.readAsStringAsync(CATALOG_CACHE_PATH);
        const parsed = JSON.parse(raw) as CompactCatalog;
        if (parsed && Array.isArray(parsed.books) && parsed.books.length > 0) {
          const { books, meta } = inflateCatalog(parsed);
          const storedMetaRaw = await AsyncStorage.getItem(STORAGE_CATALOG_META_KEY);
          const syncedAt = storedMetaRaw ? JSON.parse(storedMetaRaw).syncedAt || '' : parsed.generated_at;
          return {
            books,
            meta: { ...meta, source: 'cache', syncedAt },
          };
        }
      }
    }
  } catch {
    // Fall through to bundled starter catalog
  }

  const { books, meta } = inflateCatalog(STARTER_CATALOG);
  return {
    books,
    meta: { ...meta, source: 'starter', syncedAt: STARTER_CATALOG.generated_at || 'Starter Pack' },
  };
}

export async function syncRemoteCatalog(): Promise<{ books: Book[]; meta: CatalogMeta }> {
  const resp = await fetch(REMOTE_CATALOG_URL);
  if (!resp.ok) {
    throw new Error(`Catalog fetch failed (HTTP ${resp.status})`);
  }
  const text = await resp.text();
  const parsed = JSON.parse(text) as CompactCatalog;
  if (!parsed || !Array.isArray(parsed.books) || parsed.books.length === 0) {
    throw new Error('Downloaded catalog is empty or malformed');
  }
  if (BASE_DIR) {
    await FileSystem.writeAsStringAsync(CATALOG_CACHE_PATH, text);
  }
  const syncedAt = new Date().toISOString().slice(0, 16).replace('T', ' ');
  await AsyncStorage.setItem(STORAGE_CATALOG_META_KEY, JSON.stringify({ syncedAt }));
  const { books, meta } = inflateCatalog(parsed);
  return {
    books,
    meta: { ...meta, source: 'network', syncedAt },
  };
}

export async function clearCatalogCache(): Promise<{ books: Book[]; meta: CatalogMeta }> {
  try {
    if (BASE_DIR) {
      await FileSystem.deleteAsync(CATALOG_CACHE_PATH, { idempotent: true });
    }
    await AsyncStorage.removeItem(STORAGE_CATALOG_META_KEY);
  } catch {
    // Ignore
  }
  const { books, meta } = inflateCatalog(STARTER_CATALOG);
  return {
    books,
    meta: { ...meta, source: 'starter', syncedAt: 'Starter Pack' },
  };
}

export function getDefaultState(): AppPersistedState {
  const todayIdx = (new Date().getDay() + 6) % 7; // 0=Mon..6=Sun
  return {
    currentlyReadingId: null,
    progressById: {},
    offlineById: {},
    savedIds: [],
    streak: {
      days: 1,
      lastReadDate: new Date().toISOString().slice(0, 10),
      weekDaysActive: [todayIdx],
    },
  };
}

export async function loadPersistedState(): Promise<AppPersistedState> {
  try {
    const raw = await AsyncStorage.getItem(STORAGE_STATE_KEY);
    if (!raw) return getDefaultState();
    const parsed = JSON.parse(raw) as Partial<AppPersistedState>;
    const def = getDefaultState();

    // Verify offline files still exist on disk cleanly
    const verifiedOffline: Record<string, OfflineBookEntry> = {};
    for (const [id, entry] of Object.entries(parsed.offlineById || {})) {
      if (entry?.localUri) {
        const info = await FileSystem.getInfoAsync(entry.localUri);
        if (info.exists) {
          verifiedOffline[id] = entry;
        }
      }
    }

    return {
      currentlyReadingId: parsed.currentlyReadingId ?? null,
      progressById: parsed.progressById ?? {},
      offlineById: verifiedOffline,
      savedIds: Array.isArray(parsed.savedIds) ? parsed.savedIds : [],
      streak: parsed.streak ?? def.streak,
    };
  } catch {
    return getDefaultState();
  }
}

export async function savePersistedState(state: AppPersistedState): Promise<void> {
  try {
    await AsyncStorage.setItem(STORAGE_STATE_KEY, JSON.stringify(state));
  } catch {
    // Ignore storage quota error
  }
}

export function bumpDailyStreak(streak: ReadingStreak): ReadingStreak {
  const today = new Date().toISOString().slice(0, 10);
  const todayIdx = (new Date().getDay() + 6) % 7;
  const activeSet = new Set(streak.weekDaysActive || []);
  activeSet.add(todayIdx);

  if (streak.lastReadDate === today) {
    return {
      ...streak,
      weekDaysActive: Array.from(activeSet).sort((a, b) => a - b),
    };
  }

  const prev = new Date(streak.lastReadDate);
  const curr = new Date(today);
  const diffDays = Math.round((curr.getTime() - prev.getTime()) / (1000 * 60 * 60 * 24));
  const nextDays = diffDays === 1 ? streak.days + 1 : 1;
  const resetWeek = todayIdx === 0 && diffDays >= 1 ? [0] : Array.from(activeSet).sort((a, b) => a - b);

  return {
    days: nextDays,
    lastReadDate: today,
    weekDaysActive: resetWeek,
  };
}

export function updateProgressMap(
  progressById: Record<string, BookProgress>,
  bookId: string,
  currentPage: number,
  totalPages: number
): Record<string, BookProgress> {
  const safeTotal = Math.max(1, totalPages);
  const safePage = Math.max(0, Math.min(safeTotal, currentPage));
  const pct = Math.min(100, Math.max(1, Math.round((safePage / safeTotal) * 100)));
  return {
    ...progressById,
    [bookId]: {
      bookId,
      currentPage: safePage,
      totalPages: safeTotal,
      progressPct: pct,
      updatedAt: new Date().toISOString(),
    },
  };
}

export async function downloadBookOffline(
  book: Book,
  onProgress: (pct: number) => void
): Promise<OfflineBookEntry> {
  if (!BASE_DIR) {
    throw new Error('Offline file storage is unavailable on web; test on your phone with Expo Go.');
  }
  await ensureDirs();

  const ext = (book.fmt || 'PDF').toLowerCase().replace(/[^a-z0-9]/g, '') || 'pdf';
  const localUri = `${OFFLINE_BOOKS_DIR}${book.id}.${ext}`;

  const urls = [
    `https://drive.google.com/uc?export=download&id=${encodeURIComponent(book.id)}`,
    `https://drive.usercontent.google.com/download?id=${encodeURIComponent(book.id)}&export=download&confirm=t`,
  ];

  let finalSize = 0;
  let lastErr: Error | null = null;

  for (const url of urls) {
    try {
      const resumable = FileSystem.createDownloadResumable(url, localUri, {}, (p) => {
        if (p.totalBytesExpectedToWrite > 0) {
          onProgress(Math.round((p.totalBytesWritten / p.totalBytesExpectedToWrite) * 100));
        } else if (book.size > 0) {
          onProgress(Math.min(98, Math.round((p.totalBytesWritten / book.size) * 100)));
        }
      });
      const res = await resumable.downloadAsync();
      if (!res || res.status >= 400) {
        throw new Error(`HTTP ${res?.status ?? 'error'}`);
      }
      const ctype = (res.headers?.['content-type'] || res.headers?.['Content-Type'] || '').toLowerCase();
      if (ctype.includes('text/html')) {
        await FileSystem.deleteAsync(localUri, { idempotent: true });
        lastErr = new Error('Drive returned HTML interstitial; trying confirm URL');
        continue;
      }
      const info = await FileSystem.getInfoAsync(localUri);
      if (!info.exists || (info.size ?? 0) < 512) {
        await FileSystem.deleteAsync(localUri, { idempotent: true });
        throw new Error('Downloaded file was empty or invalid');
      }
      finalSize = info.size ?? book.size;
      lastErr = null;
      break;
    } catch (err) {
      lastErr = err instanceof Error ? err : new Error(String(err));
    }
  }

  if (lastErr) {
    throw lastErr;
  }

  // Also cache cover thumbnail locally for offline browsing
  let coverLocalUri: string | undefined;
  const thumbUrl = getThumbnailUrl(book, false);
  const thumbKey = book.coverId || book.id;
  if (thumbUrl && thumbKey) {
    const targetCover = `${OFFLINE_COVERS_DIR}${thumbKey}.jpg`;
    try {
      const covRes = await FileSystem.downloadAsync(thumbUrl, targetCover);
      if (covRes.status === 200) {
        coverLocalUri = covRes.uri;
      }
    } catch {
      // Optional cover cache failure should not fail offline book
    }
  }

  onProgress(100);
  return {
    bookId: book.id,
    title: book.title,
    author: book.author,
    cat: book.cat,
    sub: book.sub,
    fmt: book.fmt,
    localUri,
    coverLocalUri,
    size: finalSize,
    downloadedAt: new Date().toISOString(),
  };
}

export async function removeOfflineBook(entry: OfflineBookEntry): Promise<void> {
  try {
    await FileSystem.deleteAsync(entry.localUri, { idempotent: true });
    if (entry.coverLocalUri) {
      await FileSystem.deleteAsync(entry.coverLocalUri, { idempotent: true });
    }
  } catch {
    // Ignore
  }
}

export async function openOfflineBookFile(entry: OfflineBookEntry): Promise<void> {
  const mime = MIME_BY_FMT[entry.fmt.toUpperCase()] || 'application/octet-stream';
  if (Platform.OS === 'android') {
    try {
      const contentUri = await FileSystem.getContentUriAsync(entry.localUri);
      await IntentLauncher.startActivityAsync('android.intent.action.VIEW', {
        data: contentUri,
        flags: 1, // FLAG_GRANT_READ_URI_PERMISSION
        type: mime,
      });
      return;
    } catch {
      // Fallback to share sheet if no direct handler matched
    }
  }
  const canShare = await Sharing.isAvailableAsync();
  if (canShare) {
    await Sharing.shareAsync(entry.localUri, { mimeType: mime, dialogTitle: entry.title });
  } else {
    throw new Error('No external viewer or share sheet available on this device');
  }
}

export interface AppStorageUsage {
  totalBytes: number;
  catalogBytes: number;
  offlineBooksBytes: number;
  offlineCoversBytes: number;
}

async function getDirTotalBytes(dirUri: string): Promise<number> {
  if (!dirUri) return 0;
  try {
    const info = await FileSystem.getInfoAsync(dirUri);
    if (!info.exists) return 0;
    const files = await FileSystem.readDirectoryAsync(dirUri);
    let total = 0;
    for (const f of files) {
      try {
        const fi = await FileSystem.getInfoAsync(`${dirUri}${f}`);
        if (fi.exists && !fi.isDirectory && typeof fi.size === 'number') {
          total += fi.size;
        }
      } catch {
        // Ignore single file error
      }
    }
    return total;
  } catch {
    return 0;
  }
}

export async function getAppStorageUsage(): Promise<AppStorageUsage> {
  let catalogBytes = 0;
  try {
    if (CATALOG_CACHE_PATH) {
      const ci = await FileSystem.getInfoAsync(CATALOG_CACHE_PATH);
      if (ci.exists && typeof ci.size === 'number') {
        catalogBytes = ci.size;
      }
    }
  } catch {
    catalogBytes = 0;
  }

  const [offlineBooksBytes, offlineCoversBytes] = await Promise.all([
    getDirTotalBytes(OFFLINE_BOOKS_DIR),
    getDirTotalBytes(OFFLINE_COVERS_DIR),
  ]);

  return {
    totalBytes: catalogBytes + offlineBooksBytes + offlineCoversBytes,
    catalogBytes,
    offlineBooksBytes,
    offlineCoversBytes,
  };
}
