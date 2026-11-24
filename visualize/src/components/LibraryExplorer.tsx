"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  ArrowUp,
  BarChart3,
  Bookmark,
  BookOpen,
  ChevronRight,
  Compass,
  ExternalLink,
  FolderPlus,
  HardDrive,
  History,
  Library,
  Loader2,
  Moon,
  NotebookPen,
  Plus,
  RefreshCw,
  Search,
  Sparkles,
  Sun,
  Trash2,
  Users,
  X,
} from "lucide-react";
import type { AnaBookNavDetail } from "@/components/CommandPalette";
import { useWebTheme } from "@/context/WebThemeContext";
import {
  AuthorDetailRecord,
  BookProgress,
  getCategoryPalette,
  QUOTES,
  THEME_PRESETS,
  ThemePresetKey,
} from "@/lib/anabookTheme";
import { loadAuthorDetailsOnce, loadCatalogOnce } from "@/lib/catalogClient";
import {
  AuthorGroup,
  buildLibraryTree,
  collectNodeBooks,
  extractAuthorDirectory,
  FEATURED_AUTHOR_SHORTCUTS,
  NCTB_CLASS_SHORTCUTS,
  TreeNode,
} from "@/lib/libraryTree";
import {
  BookNote,
  CustomCollection,
  DEFAULT_STREAK,
  pushRecentBookId,
  ReadingStreak,
  recordReadingActivity,
  safeReadJson,
  safeWriteJson,
  STORAGE_KEYS,
  UserLibraryBackup,
} from "@/lib/userLibraryStore";
import {
  BookItem,
  formatBytes,
  getDriveFolderUrl,
  LibrarySummary,
} from "@/types/library";
import { AuthorAvatar } from "./library/AuthorAvatar";
import { AuthorDetailModal } from "./library/AuthorDetailModal";
import { BookCollectionView } from "./library/BookCollectionView";
import { BookCover } from "./library/BookCover";
import { BookDetailModal } from "./library/BookDetailModal";
import { CategoryIcon } from "./library/CategoryIcon";
import { ReaderPreviewModal } from "./library/ReaderPreviewModal";
import { StatsAndBackupView } from "./library/StatsAndBackupView";

type ActiveTab = "explore" | "search" | "authors" | "shelf" | "stats";
type AuthorFilter = "all" | AuthorGroup;

const AUTHORS_PAGE_SIZE = 36;
const SECTIONS_PAGE_SIZE = 48;

const AUTHOR_GROUP_FILTERS: { key: AuthorFilter; label: string }[] = [
  { key: "all", label: "All Authors" },
  { key: "Bangladeshi Authors", label: "Bangladeshi" },
  { key: "International Authors", label: "International" },
  { key: "Islamic Scholars", label: "Islamic Scholars" },
];

const THEME_KEYS: ThemePresetKey[] = [
  "espresso",
  "matcha",
  "midnight",
  "sepia",
  "rosewood",
];

function lookupAuthorDetail(
  detailsMap: Record<string, AuthorDetailRecord>,
  name: string
): AuthorDetailRecord | undefined {
  const raw = (name || "").trim().toLowerCase();
  if (!raw) return undefined;
  return detailsMap[raw] || detailsMap[raw.normalize("NFC")];
}

export function LibraryExplorer() {
  const {
    presetKey,
    themeMode,
    theme,
    setPresetKey,
    toggleThemeMode,
  } = useWebTheme();

  const [books, setBooks] = useState<BookItem[]>([]);
  const [summary, setSummary] = useState<LibrarySummary | null>(null);
  const [authorDetails, setAuthorDetails] = useState<
    Record<string, AuthorDetailRecord>
  >({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Navigation & filtering state
  const [activeTab, setActiveTab] = useState<ActiveTab>("explore");
  const [explorePath, setExplorePath] = useState<string[]>([]);
  const [folderFilter, setFolderFilter] = useState("");
  const [visibleSectionCount, setVisibleSectionCount] =
    useState(SECTIONS_PAGE_SIZE);

  // Global search state (All Books tab)
  const [query, setQuery] = useState("");
  const [searchCat, setSearchCat] = useState("ALL");

  // Authors directory state
  const [authorQuery, setAuthorQuery] = useState("");
  const [authorGroup, setAuthorGroup] = useState<AuthorFilter>("all");
  const [visibleAuthorCount, setVisibleAuthorCount] =
    useState(AUTHORS_PAGE_SIZE);

  // My Shelf filters
  const [shelfFilter, setShelfFilter] = useState<string>("SAVED");
  const [newListName, setNewListName] = useState("");

  // User shelf, progress, notes, collections, streak & modals state
  const [savedIds, setSavedIds] = useState<string[]>([]);
  const [progressById, setProgressById] = useState<
    Record<string, BookProgress>
  >({});
  const [currentReadId, setCurrentReadId] = useState<string | null>(null);
  const [recentIds, setRecentIds] = useState<string[]>([]);
  const [notesById, setNotesById] = useState<Record<string, BookNote>>({});
  const [collections, setCollections] = useState<CustomCollection[]>([]);
  const [streak, setStreak] = useState<ReadingStreak>(DEFAULT_STREAK);
  const [pendingBookId, setPendingBookId] = useState<string | null>(null);

  const [detailBook, setDetailBook] = useState<BookItem | null>(null);
  const [previewBook, setPreviewBook] = useState<BookItem | null>(null);
  const [authorModalOpen, setAuthorModalOpen] = useState(false);
  const [quoteIdx, setQuoteIdx] = useState(0);
  const [showScrollTop, setShowScrollTop] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  const applyNavDetail = useCallback((detail: AnaBookNavDetail) => {
    if (detail.bookId) {
      setPendingBookId(detail.bookId);
    }
    if (detail.tab) {
      setActiveTab(detail.tab);
    }
    if (detail.path) {
      setFolderFilter("");
      setExplorePath(detail.path);
      if (!detail.tab) setActiveTab("explore");
    } else if (detail.cat) {
      if (detail.cat === "SAVED") {
        setActiveTab("shelf");
      } else if (detail.tab === "search") {
        setSearchCat(detail.cat);
      } else if (detail.cat !== "ALL") {
        setExplorePath([detail.cat]);
        setActiveTab("explore");
      }
    }
    if (detail.q !== undefined) {
      setQuery(detail.q);
      if (detail.q && !detail.tab) setActiveTab("search");
    }
  }, []);

  // Hydrate persisted user state & URL parameters on mount
  useEffect(() => {
    setSavedIds(safeReadJson<string[]>(STORAGE_KEYS.SAVED, []));
    setProgressById(
      safeReadJson<Record<string, BookProgress>>(STORAGE_KEYS.PROGRESS, {})
    );
    setRecentIds(safeReadJson<string[]>(STORAGE_KEYS.RECENT, []));
    setNotesById(safeReadJson<Record<string, BookNote>>(STORAGE_KEYS.NOTES, {}));
    setCollections(
      safeReadJson<CustomCollection[]>(STORAGE_KEYS.COLLECTIONS, [])
    );
    setStreak(safeReadJson<ReadingStreak>(STORAGE_KEYS.STREAK, DEFAULT_STREAK));

    try {
      const storedCurrent = localStorage.getItem(STORAGE_KEYS.CURRENT_READ);
      if (storedCurrent) setCurrentReadId(storedCurrent);

      const params = new URLSearchParams(window.location.search);
      const bookParam = params.get("book");
      const tabParam = params.get("tab") as ActiveTab | null;
      const q = params.get("q");
      const pathParam = params.get("path");
      const catParam = params.get("cat") || params.get("category");

      if (bookParam) setPendingBookId(bookParam);

      if (
        tabParam &&
        ["explore", "search", "authors", "shelf", "stats"].includes(tabParam)
      ) {
        setActiveTab(tabParam);
      }

      if (q) {
        setQuery(q);
        setActiveTab("search");
        if (catParam && catParam !== "ALL" && catParam !== "SAVED") {
          setSearchCat(catParam);
        }
      } else if (pathParam) {
        const segs = pathParam.split("/").filter(Boolean);
        if (segs.length > 0) {
          setExplorePath(segs);
          setActiveTab("explore");
        }
      } else if (catParam) {
        if (catParam === "SAVED") {
          setActiveTab("shelf");
        } else if (catParam !== "ALL") {
          setExplorePath([catParam]);
          setActiveTab("explore");
        }
      }
    } catch {
      // Ignore URL/storage error
    } finally {
      setHydrated(true);
    }
  }, []);

  // Listen for CommandPalette instant navigation events when already on /library
  useEffect(() => {
    const handler = (e: Event) => {
      const custom = e as CustomEvent<AnaBookNavDetail>;
      if (custom.detail) applyNavDetail(custom.detail);
    };
    window.addEventListener("anabook:navigate", handler);
    return () => window.removeEventListener("anabook:navigate", handler);
  }, [applyNavDetail]);

  // Back-to-top scroll listener
  useEffect(() => {
    const onScroll = () => setShowScrollTop(window.scrollY > 520);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Fetch main 29,178-book catalog (cached singleton) + lazy author details
  useEffect(() => {
    let cancelled = false;
    loadCatalogOnce()
      .then(({ books: inflated, summary: meta }) => {
        if (cancelled) return;
        setBooks(inflated);
        setSummary(meta);
        setLoading(false);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to load catalog"
          );
          setLoading(false);
        }
      });

    loadAuthorDetailsOnce().then((details) => {
      if (!cancelled) setAuthorDetails(details);
    });

    return () => {
      cancelled = true;
    };
  }, []);

  const booksById = useMemo(() => {
    const map = new Map<string, BookItem>();
    for (const b of books) map.set(b.id, b);
    return map;
  }, [books]);

  // Resolve ?book=<id> deep-link once catalog is ready
  useEffect(() => {
    if (!pendingBookId || booksById.size === 0) return;
    const match = booksById.get(pendingBookId);
    if (match) {
      setDetailBook(match);
      setRecentIds((prev) => pushRecentBookId(prev, match.id));
    }
    setPendingBookId(null);
  }, [pendingBookId, booksById]);

  // Sync URL query params and document.title dynamically for SEO & deep links
  useEffect(() => {
    if (!hydrated) return;

    const trimmedQuery = query.trim();
    if (detailBook) {
      document.title = `${detailBook.title} — AnaBook | Bangladesh's Biggest eLibrary & PDF Library`;
    } else if (activeTab === "search" && trimmedQuery) {
      document.title = `"${trimmedQuery}" — AnaBook | Bangladesh's Biggest eLibrary & PDF Library`;
    } else if (activeTab === "explore" && explorePath.length > 0) {
      const label = explorePath[explorePath.length - 1];
      document.title = `${label} — AnaBook | Bangladesh's Biggest eLibrary & PDF Library`;
    } else if (activeTab === "authors") {
      document.title =
        "Authors & Scholars — AnaBook | Bangladesh's Biggest eLibrary & PDF Library";
    } else if (activeTab === "shelf") {
      document.title =
        "My Shelf & Collections — AnaBook | Bangladesh's Biggest eLibrary & PDF Library";
    } else if (activeTab === "stats") {
      document.title =
        "Reading Stats & Backup — AnaBook | Bangladesh's Biggest eLibrary & PDF Library";
    } else {
      document.title =
        "Online Library — Bangladesh's Biggest PDF Library & eBook Library (29,178+ Books) | AnaBook — Bangladesh's Biggest eLibrary";
    }

    try {
      const url = new URL(window.location.href);
      url.searchParams.delete("q");
      url.searchParams.delete("cat");
      url.searchParams.delete("category");
      url.searchParams.delete("path");
      url.searchParams.delete("tab");
      url.searchParams.delete("book");

      if (detailBook) {
        url.searchParams.set("book", detailBook.id);
      } else if (activeTab === "search") {
        url.searchParams.set("tab", "search");
        if (trimmedQuery) url.searchParams.set("q", trimmedQuery);
        if (searchCat !== "ALL") url.searchParams.set("cat", searchCat);
      } else if (activeTab === "explore" && explorePath.length === 1) {
        url.searchParams.set("cat", explorePath[0]);
      } else if (activeTab === "explore" && explorePath.length > 1) {
        url.searchParams.set("path", explorePath.join("/"));
      } else if (activeTab === "shelf") {
        url.searchParams.set("cat", "SAVED");
      } else if (activeTab === "authors" || activeTab === "stats") {
        url.searchParams.set("tab", activeTab);
      }

      window.history.replaceState(
        null,
        "",
        `${url.pathname}${url.search}${url.hash}`
      );
    } catch {
      // Ignore history API errors
    }
  }, [hydrated, activeTab, explorePath, query, searchCat, detailBook]);

  const savedSet = useMemo(() => new Set(savedIds), [savedIds]);

  const toggleSave = (id: string) => {
    setSavedIds((prev) => {
      const next = prev.includes(id)
        ? prev.filter((x) => x !== id)
        : [id, ...prev];
      safeWriteJson(STORAGE_KEYS.SAVED, next);
      return next;
    });
  };

  const handleSetCurrentlyReading = (bookId: string) => {
    setCurrentReadId(bookId);
    setRecentIds((prev) => pushRecentBookId(prev, bookId));
    try {
      localStorage.setItem(STORAGE_KEYS.CURRENT_READ, bookId);
    } catch {
      // Ignore
    }
  };

  const handleUpdateProgress = (
    bookId: string,
    currentPage: number,
    totalPages: number
  ) => {
    const safeTotal = Math.max(1, totalPages);
    const safeCurr = Math.min(safeTotal, Math.max(0, currentPage));
    const progressPct = Math.round((safeCurr / safeTotal) * 100);
    handleSetCurrentlyReading(bookId);
    setStreak((prev) => recordReadingActivity(prev, 0));
    setProgressById((prev) => {
      const next: Record<string, BookProgress> = {
        ...prev,
        [bookId]: {
          bookId,
          currentPage: safeCurr,
          totalPages: safeTotal,
          progressPct,
          updatedAt: new Date().toISOString(),
        },
      };
      safeWriteJson(STORAGE_KEYS.PROGRESS, next);
      return next;
    });
  };

  const handleSaveNote = (bookId: string, text: string) => {
    setNotesById((prev) => {
      const next = { ...prev };
      if (!text.trim()) {
        delete next[bookId];
      } else {
        next[bookId] = {
          text,
          updatedAt: new Date().toISOString(),
        };
      }
      safeWriteJson(STORAGE_KEYS.NOTES, next);
      return next;
    });
  };

  const handleCreateCollection = (name: string, initialBookId?: string) => {
    const clean = name.trim();
    if (!clean) return;
    const newCol: CustomCollection = {
      id: `col-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
      name: clean,
      bookIds: initialBookId ? [initialBookId] : [],
      createdAt: new Date().toISOString(),
    };
    setCollections((prev) => {
      const next = [newCol, ...prev];
      safeWriteJson(STORAGE_KEYS.COLLECTIONS, next);
      return next;
    });
  };

  const handleDeleteCollection = (collectionId: string) => {
    setCollections((prev) => {
      const next = prev.filter((c) => c.id !== collectionId);
      safeWriteJson(STORAGE_KEYS.COLLECTIONS, next);
      return next;
    });
    if (shelfFilter === collectionId) setShelfFilter("SAVED");
  };

  const handleToggleCollectionBook = (collectionId: string, bookId: string) => {
    setCollections((prev) => {
      const next = prev.map((col) => {
        if (col.id !== collectionId) return col;
        const exists = col.bookIds.includes(bookId);
        return {
          ...col,
          bookIds: exists
            ? col.bookIds.filter((id) => id !== bookId)
            : [bookId, ...col.bookIds],
        };
      });
      safeWriteJson(STORAGE_KEYS.COLLECTIONS, next);
      return next;
    });
  };

  const handleOpenDetail = (book: BookItem) => {
    setRecentIds((prev) => pushRecentBookId(prev, book.id));
    setDetailBook(book);
  };

  const handleOpenReader = (book: BookItem) => {
    handleSetCurrentlyReading(book.id);
    setStreak((prev) => recordReadingActivity(prev, 0));
    setPreviewBook(book);
  };

  const handleLogReadingMinute = useCallback(() => {
    setStreak((prev) => recordReadingActivity(prev, 1));
  }, []);

  const handleRestoreBackup = (backup: UserLibraryBackup) => {
    setSavedIds(backup.savedIds);
    setProgressById(backup.progressById);
    setCurrentReadId(backup.currentReadId);
    setRecentIds(backup.recentIds);
    setNotesById(backup.notesById);
    setCollections(backup.collections);
    setStreak(backup.streak);
    if (backup.theme?.preset) setPresetKey(backup.theme.preset);
  };

  // Hierarchical Category Tree (Explore Tab)
  const rootTree = useMemo(
    () => buildLibraryTree(books, summary?.cats || []),
    [books, summary?.cats]
  );

  const currentNode = useMemo(() => {
    let curr: TreeNode = rootTree;
    for (const seg of explorePath) {
      const next = curr.children.get(seg);
      if (!next) break;
      curr = next;
    }
    return curr;
  }, [rootTree, explorePath]);

  const pathKey = explorePath.join("/");
  useEffect(() => {
    setVisibleSectionCount(SECTIONS_PAGE_SIZE);
    setAuthorModalOpen(false);
  }, [pathKey, folderFilter]);

  const isRootExplore = explorePath.length === 0;

  const childSections = useMemo(() => {
    const q = folderFilter.trim().toLowerCase();
    const list = Array.from(currentNode.children.values()).filter(
      (n) => n.totalCount > 0
    );
    if (explorePath.length > 0) {
      list.sort((a, b) =>
        a.name.localeCompare(b.name, undefined, {
          numeric: true,
          sensitivity: "base",
        })
      );
    }
    return q ? list.filter((n) => n.name.toLowerCase().includes(q)) : list;
  }, [currentNode, folderFilter, explorePath.length]);

  const rootFolderMatches = useMemo(() => {
    const q = folderFilter.trim().toLowerCase();
    if (!isRootExplore || q.length < 2)
      return [] as { label: string; path: string[]; count: number }[];
    const matches: { label: string; path: string[]; count: number }[] = [];
    const walk = (node: TreeNode, trail: string[]) => {
      for (const child of node.children.values()) {
        const nextTrail = [...trail, child.name];
        if (nextTrail.length >= 2 && child.name.toLowerCase().includes(q)) {
          matches.push({
            label: nextTrail.join(" / "),
            path: nextTrail,
            count: child.totalCount,
          });
        }
        if (matches.length < 18) walk(child, nextTrail);
      }
    };
    walk(rootTree, []);
    return matches.slice(0, 14);
  }, [isRootExplore, folderFilter, rootTree]);

  const isAuthorsLeafGrid = useMemo(() => {
    if (explorePath[0] !== "Authors & Scholars" || childSections.length === 0)
      return false;
    return (
      ((explorePath[1] === "Bangladeshi Authors" ||
        explorePath[1] === "International Authors") &&
        explorePath.length === 2) ||
      (explorePath[1] === "Islamic Scholars" && explorePath.length === 3)
    );
  }, [explorePath, childSections.length]);

  const isViewingAuthor = Boolean(
    explorePath[0] === "Authors & Scholars" &&
      ((explorePath[1] !== "Islamic Scholars" && explorePath.length === 3) ||
        (explorePath[1] === "Islamic Scholars" && explorePath.length === 4))
  );

  const authorDetail = useMemo(
    () =>
      isViewingAuthor
        ? lookupAuthorDetail(authorDetails, currentNode.name)
        : undefined,
    [isViewingAuthor, authorDetails, currentNode.name]
  );

  const directBooksFiltered = useMemo(() => {
    const q = folderFilter.trim().toLowerCase();
    const list = currentNode.directBooks;
    if (!q) return list;
    return list.filter((b) => b.searchBlob.includes(q));
  }, [currentNode, folderFilter]);

  const folderAllBooksFiltered = useMemo(() => {
    if (isRootExplore) return [];
    const all = collectNodeBooks(currentNode);
    const q = folderFilter.trim().toLowerCase();
    if (!q) return all;
    return all.filter((b) => b.searchBlob.includes(q));
  }, [isRootExplore, currentNode, folderFilter]);

  const navigateExplorePath = (nextPath: string[]) => {
    setFolderFilter("");
    setExplorePath(nextPath);
    setActiveTab("explore");
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  // Personalized Suggested For You (ported from HomeScreen.tsx)
  const suggestedBooks = useMemo(() => {
    if (!books.length) return [] as { book: BookItem; reason: string }[];
    const seedIds = new Set<string>([
      ...(currentReadId ? [currentReadId] : []),
      ...savedIds,
      ...recentIds,
      ...Object.keys(progressById),
    ]);

    const prefAuthors = new Map<string, number>();
    const prefSubs = new Map<string, number>();
    const prefCats = new Map<string, number>();

    for (const id of seedIds) {
      const sb = booksById.get(id);
      if (!sb) continue;
      if (sb.author && sb.author !== "Unknown") {
        prefAuthors.set(sb.author, (prefAuthors.get(sb.author) || 0) + 4);
      }
      if (sb.sub) {
        prefSubs.set(sb.sub, (prefSubs.get(sb.sub) || 0) + 3);
      }
      prefCats.set(sb.cat, (prefCats.get(sb.cat) || 0) + 1);
    }

    const candidates: { book: BookItem; score: number; reason: string }[] = [];
    const seenCatMix = new Map<string, number>();

    for (const b of books) {
      if (currentReadId && b.id === currentReadId) continue;
      if (progressById[b.id] && progressById[b.id].progressPct >= 100) continue;

      let score = b.coverId ? 3 : 0;
      let reason = (b.sub || b.cat).split("/").pop() || b.cat;

      if (prefAuthors.has(b.author)) {
        score += (prefAuthors.get(b.author) || 0) * 3;
        reason = b.author;
      } else if (b.sub && prefSubs.has(b.sub)) {
        score += (prefSubs.get(b.sub) || 0) * 2;
      } else if (prefCats.has(b.cat)) {
        score += prefCats.get(b.cat) || 0;
      }

      if (score > 2) {
        candidates.push({ book: b, score, reason });
      }
      if (candidates.length >= 280) break;
    }

    candidates.sort((a, b) => b.score - a.score);
    const out: { book: BookItem; reason: string }[] = [];
    const used = new Set<string>();

    for (const c of candidates) {
      const catCnt = seenCatMix.get(c.book.cat) || 0;
      if (
        out.length < 10 &&
        !used.has(c.book.id) &&
        (prefAuthors.size > 0 || catCnt < 3)
      ) {
        used.add(c.book.id);
        seenCatMix.set(c.book.cat, catCnt + 1);
        out.push({ book: c.book, reason: c.reason });
      }
      if (out.length >= 10) break;
    }

    return out;
  }, [books, booksById, currentReadId, savedIds, recentIds, progressById]);

  const currentReadBook = currentReadId
    ? booksById.get(currentReadId) ?? null
    : null;

  const recentBooks = useMemo(
    () =>
      recentIds
        .map((id) => booksById.get(id))
        .filter((b): b is BookItem => Boolean(b))
        .slice(0, 10),
    [recentIds, booksById]
  );

  // Author Directory
  const authorDirectory = useMemo(
    () => extractAuthorDirectory(books, savedSet),
    [books, savedSet]
  );

  const filteredAuthors = useMemo(() => {
    const q = authorQuery.trim().toLowerCase();
    return authorDirectory.filter((item) => {
      if (authorGroup !== "all" && item.group !== authorGroup) return false;
      if (q && !item.name.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [authorDirectory, authorQuery, authorGroup]);

  useEffect(() => {
    setVisibleAuthorCount(AUTHORS_PAGE_SIZE);
  }, [authorQuery, authorGroup]);

  // Global Search Tab filtering
  const searchResults = useMemo(() => {
    const terms = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
    return books.filter((b) => {
      if (searchCat === "SAVED" && !savedSet.has(b.id)) return false;
      if (searchCat !== "ALL" && searchCat !== "SAVED") {
        const matchesPrimary = b.cat === searchCat;
        const matchesExtra = Boolean(
          b.extraPaths?.some((p) => p.cat === searchCat)
        );
        if (!matchesPrimary && !matchesExtra) return false;
      }
      for (const t of terms) {
        if (!b.searchBlob.includes(t)) return false;
      }
      return true;
    });
  }, [books, query, searchCat, savedSet]);

  const searchMatchingAuthors = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (q.length < 2) return [];
    return authorDirectory
      .filter((a) => a.name.toLowerCase().includes(q))
      .slice(0, 10);
  }, [authorDirectory, query]);

  const searchMatchingFolders = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (q.length < 2)
      return [] as { name: string; path: string[]; count: number }[];
    const out: { name: string; path: string[]; count: number }[] = [];
    const walk = (node: TreeNode, trail: string[]) => {
      for (const child of node.children.values()) {
        const nextTrail = [...trail, child.name];
        if (child.name.toLowerCase().includes(q)) {
          out.push({
            name: child.name,
            path: nextTrail,
            count: child.totalCount,
          });
        }
        if (out.length < 12) walk(child, nextTrail);
      }
    };
    walk(rootTree, []);
    return out.slice(0, 10);
  }, [rootTree, query]);

  // My Shelf Tab items
  const readingShelfItems = useMemo(() => {
    const seen = new Set<string>();
    const list: { book: BookItem; progress?: BookProgress }[] = [];
    const tracked = Object.values(progressById).sort((a, b) =>
      (b.updatedAt || "").localeCompare(a.updatedAt || "")
    );
    for (const prog of tracked) {
      const b = booksById.get(prog.bookId);
      if (b && !seen.has(b.id)) {
        seen.add(b.id);
        list.push({ book: b, progress: prog });
      }
    }
    if (currentReadId && !seen.has(currentReadId)) {
      const b = booksById.get(currentReadId);
      if (b) {
        seen.add(b.id);
        list.push({ book: b, progress: progressById[b.id] });
      }
    }
    return list;
  }, [progressById, currentReadId, booksById]);

  const savedBooks = useMemo(
    () =>
      savedIds
        .map((id) => booksById.get(id))
        .filter((b): b is BookItem => Boolean(b)),
    [savedIds, booksById]
  );

  const notedBooks = useMemo(
    () =>
      Object.entries(notesById)
        .filter(([, n]) => Boolean(n?.text?.trim()))
        .sort((a, b) =>
          (b[1].updatedAt || "").localeCompare(a[1].updatedAt || "")
        )
        .map(([id]) => booksById.get(id))
        .filter((b): b is BookItem => Boolean(b)),
    [notesById, booksById]
  );

  const shelfActiveBooks = useMemo(() => {
    if (shelfFilter === "SAVED") return savedBooks;
    if (shelfFilter === "NOTES") return notedBooks;
    const col = collections.find((c) => c.id === shelfFilter);
    if (!col) return savedBooks;
    return col.bookIds
      .map((id) => booksById.get(id))
      .filter((b): b is BookItem => Boolean(b));
  }, [shelfFilter, savedBooks, notedBooks, collections, booksById]);

  const handleSurpriseMe = () => {
    const source =
      activeTab === "search" && searchResults.length > 0
        ? searchResults
        : !isRootExplore && folderAllBooksFiltered.length > 0
          ? folderAllBooksFiltered
          : books;
    const withCovers = source.filter((b) => Boolean(b.coverId));
    const pool = withCovers.length > 0 ? withCovers : source;
    if (pool.length === 0) return;
    handleOpenDetail(pool[Math.floor(Math.random() * pool.length)]);
  };

  const handleJumpAuthorFromBook = (authorName: string) => {
    const exact = authorDirectory.find(
      (a) => a.name.toLowerCase() === authorName.trim().toLowerCase()
    );
    if (exact) {
      navigateExplorePath(exact.path);
    } else {
      setQuery(authorName);
      setSearchCat("ALL");
      setActiveTab("search");
    }
  };

  const activeQuote = QUOTES[quoteIdx % QUOTES.length];

  if (loading) {
    return (
      <div
        className="min-h-[75vh] flex flex-col items-center justify-center gap-3"
        style={{ backgroundColor: theme.bg, color: theme.muted }}
      >
        <Loader2
          className="w-8 h-8 animate-spin"
          style={{ color: theme.accent }}
        />
        <p className="text-sm font-semibold">
          Loading AnaBook Online Library…
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="min-h-[60vh] flex flex-col items-center justify-center px-4 py-20 text-center space-y-3"
        style={{ backgroundColor: theme.bg, color: theme.ink }}
      >
        <p className="text-lg font-extrabold">Unable to load catalog</p>
        <p className="text-sm" style={{ color: theme.muted }}>
          {error}
        </p>
      </div>
    );
  }

  return (
    <div
      className="min-h-[calc(100vh-5rem)] transition-colors duration-200"
      style={{ backgroundColor: theme.bg, color: theme.ink }}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-8 py-6 sm:py-8 space-y-6">
        {/* Top App-Style Header + Theme Switcher */}
        <section className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div className="space-y-1">
            <h1 className="text-xl sm:text-2xl lg:text-[26px] font-extrabold tracking-tight">
              Bangladesh’s Biggest eLibrary &amp; PDF Book Library
            </h1>
            <p className="text-xs sm:text-sm" style={{ color: theme.muted }}>
              {books.length.toLocaleString()}+ Bangla &amp; English books · Class
              1–12 NCTB ·{" "}
              {summary?.authorsCount.toLocaleString() ?? "4,575"}+ authors ·
              Archive {summary ? formatBytes(summary.totalBytes) : "—"}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* 5 AnaBook Theme Preset Swatches */}
            <div
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-full border"
              style={{
                backgroundColor: theme.surface,
                borderColor: theme.border,
              }}
              role="group"
              aria-label="AnaBook reading themes"
            >
              {THEME_KEYS.map((key) => {
                const def = THEME_PRESETS[key];
                const active = key === presetKey;
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setPresetKey(key)}
                    title={`${def.label} Theme`}
                    aria-label={`${def.label} Theme`}
                    className={`w-5 h-5 rounded-full border transition cursor-pointer ${
                      active
                        ? "scale-110 ring-2 ring-offset-1"
                        : "opacity-80 hover:opacity-100"
                    }`}
                    style={{
                      backgroundColor: def.swatches[2],
                      borderColor: theme.border,
                      boxShadow: active
                        ? `0 0 0 2px ${theme.ink}`
                        : undefined,
                    }}
                  />
                );
              })}

              <span
                className="w-px h-4 mx-0.5"
                style={{ backgroundColor: theme.border }}
              />

              <button
                type="button"
                onClick={toggleThemeMode}
                title={
                  themeMode === "light"
                    ? "Switch to Dark Mode"
                    : "Switch to Light Mode"
                }
                aria-label={
                  themeMode === "light"
                    ? "Switch to Dark Mode"
                    : "Switch to Light Mode"
                }
                className="w-6 h-6 rounded-full flex items-center justify-center transition hover:opacity-80 cursor-pointer"
                style={{
                  backgroundColor: theme.surfaceAlt,
                  color: theme.ink,
                }}
              >
                {themeMode === "light" ? (
                  <Moon className="w-3.5 h-3.5" />
                ) : (
                  <Sun className="w-3.5 h-3.5" />
                )}
              </button>
            </div>

            <button
              type="button"
              onClick={handleSurpriseMe}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full text-xs font-extrabold transition hover:opacity-90 cursor-pointer"
              style={{
                backgroundColor: theme.cream,
                color: theme.creamInk,
              }}
            >
              <Sparkles
                className="w-3.5 h-3.5"
                style={{ color: theme.accent }}
              />
              <span>Surprise Me</span>
            </button>

            <a
              href={getDriveFolderUrl("1fMsplDtUnpUhnNBJGKvYQ1sdZx0QVJWq")}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full border text-xs font-bold transition hover:opacity-85"
              style={{
                backgroundColor: theme.surface,
                borderColor: theme.border,
                color: theme.ink,
              }}
            >
              <HardDrive className="w-3.5 h-3.5" />
              <span>Drive</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </section>

        {/* 5 Segmented Navigation Tabs (Matching AnaBook App + Stats) */}
        <nav
          className="flex items-center gap-2 overflow-x-auto pb-1 no-scrollbar"
          aria-label="Library sections"
        >
          {(
            [
              { key: "explore", label: "Categories", Icon: Compass },
              { key: "search", label: "All Books", Icon: Search },
              {
                key: "authors",
                label: `Authors (${authorDirectory.length.toLocaleString()})`,
                Icon: Users,
              },
              {
                key: "shelf",
                label: `My Shelf (${savedIds.length})`,
                Icon: Library,
              },
              { key: "stats", label: "Stats", Icon: BarChart3 },
            ] as const
          ).map(({ key, label, Icon }) => {
            const active = activeTab === key;
            return (
              <button
                key={key}
                type="button"
                onClick={() => setActiveTab(key)}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-2xl border text-xs sm:text-sm font-extrabold transition shrink-0 cursor-pointer"
                style={{
                  backgroundColor: active ? theme.cream : theme.surface,
                  borderColor: active ? theme.cream : theme.border,
                  color: active ? theme.creamInk : theme.ink,
                }}
              >
                <Icon
                  className="w-4 h-4"
                  style={{ color: active ? theme.accent : theme.muted }}
                />
                <span>{label}</span>
              </button>
            );
          })}
        </nav>

        {/* ==================== TAB 1: CATEGORIES (EXPLORE BENTO) ==================== */}
        {activeTab === "explore" && (
          <div className="space-y-7">
            {/* Drill-down Header + Breadcrumbs + Filter Input */}
            {!isRootExplore ? (
              <div
                className="rounded-3xl border p-4 sm:p-5 space-y-3.5"
                style={{
                  backgroundColor: theme.surface,
                  borderColor: theme.border,
                }}
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    <button
                      type="button"
                      onClick={() =>
                        navigateExplorePath(explorePath.slice(0, -1))
                      }
                      aria-label="Back to parent category"
                      className="w-9 h-9 rounded-full border flex items-center justify-center transition hover:opacity-80 shrink-0 cursor-pointer"
                      style={{
                        backgroundColor: theme.surfaceAlt,
                        borderColor: theme.border,
                        color: theme.ink,
                      }}
                    >
                      <ArrowLeft className="w-4 h-4" />
                    </button>

                    {isViewingAuthor ? (
                      <AuthorAvatar
                        name={currentNode.name}
                        size={38}
                        theme={theme}
                      />
                    ) : (
                      <CategoryIcon
                        name={currentNode.name}
                        size={30}
                        accentColor={theme.accent}
                      />
                    )}

                    <div className="min-w-0">
                      <h2 className="text-lg sm:text-xl font-extrabold truncate">
                        {currentNode.name}
                      </h2>
                      <p
                        className="text-xs font-semibold"
                        style={{ color: theme.accent }}
                      >
                        {currentNode.totalCount.toLocaleString()} books
                        {childSections.length > 0
                          ? ` · ${childSections.length} subsections`
                          : ""}
                      </p>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => {
                      setSearchCat(explorePath[0] || "ALL");
                      setQuery(
                        explorePath.length > 1
                          ? explorePath[explorePath.length - 1]
                          : ""
                      );
                      setActiveTab("search");
                    }}
                    className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-full border text-xs font-bold transition hover:opacity-85 cursor-pointer"
                    style={{
                      backgroundColor: theme.surfaceAlt,
                      borderColor: theme.border,
                      color: theme.ink,
                    }}
                  >
                    <Search className="w-3.5 h-3.5" />
                    <span>Filter in All Books</span>
                  </button>
                </div>

                {/* Breadcrumbs */}
                <div className="flex items-center gap-1.5 overflow-x-auto pb-1 no-scrollbar">
                  <button
                    type="button"
                    onClick={() => navigateExplorePath([])}
                    className="px-3 py-1 rounded-full border text-[11px] font-bold shrink-0 transition cursor-pointer"
                    style={{
                      backgroundColor: theme.surfaceAlt,
                      borderColor: theme.border,
                      color: theme.ink,
                    }}
                  >
                    All Categories
                  </button>
                  {explorePath.map((seg, idx) => {
                    const last = idx === explorePath.length - 1;
                    return (
                      <React.Fragment key={`${seg}-${idx}`}>
                        <ChevronRight
                          className="w-3.5 h-3.5 shrink-0"
                          style={{ color: theme.muted }}
                        />
                        <button
                          type="button"
                          onClick={() =>
                            navigateExplorePath(explorePath.slice(0, idx + 1))
                          }
                          className="px-3 py-1 rounded-full border text-[11px] shrink-0 transition cursor-pointer"
                          style={{
                            backgroundColor: last
                              ? theme.cream
                              : theme.surfaceAlt,
                            borderColor: last ? theme.cream : theme.border,
                            color: last ? theme.creamInk : theme.ink,
                            fontWeight: last ? 800 : 600,
                          }}
                        >
                          {seg}
                        </button>
                      </React.Fragment>
                    );
                  })}
                </div>

                {/* Folder Search Box */}
                <div className="relative">
                  <Search
                    className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2"
                    style={{ color: theme.muted }}
                  />
                  <input
                    type="text"
                    value={folderFilter}
                    onChange={(e) => setFolderFilter(e.target.value)}
                    placeholder={`Search inside ${currentNode.name}…`}
                    className="w-full pl-10 pr-9 py-2.5 rounded-2xl border text-xs sm:text-sm focus:outline-none"
                    style={{
                      backgroundColor: theme.surfaceAlt,
                      borderColor: theme.border,
                      color: theme.ink,
                    }}
                  />
                  {folderFilter && (
                    <button
                      type="button"
                      onClick={() => setFolderFilter("")}
                      aria-label="Clear folder search"
                      className="absolute right-3 top-1/2 -translate-y-1/2 cursor-pointer"
                      style={{ color: theme.muted }}
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            ) : (
              /* Root Search/Jump Box */
              <div className="space-y-3">
                <div className="relative">
                  <Search
                    className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2"
                    style={{ color: theme.muted }}
                  />
                  <input
                    type="text"
                    value={folderFilter}
                    onChange={(e) => setFolderFilter(e.target.value)}
                    placeholder="Filter categories or jump to any folder (e.g. Class 10, হুমায়ূন আহমেদ, Hadith)…"
                    className="w-full pl-11 pr-10 py-3 rounded-2xl border text-xs sm:text-sm focus:outline-none"
                    style={{
                      backgroundColor: theme.surface,
                      borderColor: theme.border,
                      color: theme.ink,
                    }}
                  />
                  {folderFilter && (
                    <button
                      type="button"
                      onClick={() => setFolderFilter("")}
                      aria-label="Clear category filter"
                      className="absolute right-3.5 top-1/2 -translate-y-1/2 cursor-pointer"
                      style={{ color: theme.muted }}
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>

                {rootFolderMatches.length > 0 && (
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className="text-[11px] font-bold uppercase tracking-wider"
                      style={{ color: theme.muted }}
                    >
                      Quick Jump:
                    </span>
                    {rootFolderMatches.map((m) => (
                      <button
                        key={m.label}
                        type="button"
                        onClick={() => navigateExplorePath(m.path)}
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-xs font-bold transition hover:opacity-85 cursor-pointer"
                        style={{
                          backgroundColor: theme.surface,
                          borderColor: theme.border,
                          color: theme.ink,
                        }}
                      >
                        <CategoryIcon
                          name={m.path[m.path.length - 1]}
                          size={15}
                          accentColor={theme.accent}
                        />
                        <span>{m.label}</span>
                        <span style={{ color: theme.accent }}>
                          ({m.count.toLocaleString()})
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Author Profile Banner */}
            {isViewingAuthor && (
              <div
                className="rounded-3xl border p-4 sm:p-5 space-y-3"
                style={{
                  backgroundColor: theme.surface,
                  borderColor: theme.border,
                }}
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3.5 min-w-0">
                    <AuthorAvatar
                      name={currentNode.name}
                      size={58}
                      theme={theme}
                    />
                    <div className="min-w-0">
                      <h3 className="text-base sm:text-lg font-extrabold truncate">
                        {currentNode.name}
                      </h3>
                      <p
                        className="text-xs font-semibold truncate"
                        style={{ color: theme.accent }}
                      >
                        {authorDetail?.shortDesc ||
                          explorePath[1] ||
                          "Author"}{" "}
                        · {currentNode.totalCount.toLocaleString()} books
                      </p>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => setAuthorModalOpen(true)}
                    className="px-4 py-2 rounded-2xl border text-xs font-extrabold transition hover:opacity-85 cursor-pointer"
                    style={{
                      backgroundColor: theme.accentSoft,
                      borderColor: theme.accent,
                      color: theme.accent,
                    }}
                  >
                    Author Details
                  </button>
                </div>

                {authorDetail?.bio ? (
                  <p
                    className="text-xs sm:text-sm leading-relaxed line-clamp-2"
                    style={{ color: theme.muted }}
                  >
                    {authorDetail.bio}
                  </p>
                ) : null}
              </div>
            )}

            {/* ROOT BENTO GRID + PERSONALIZED HOME SHELVES */}
            {isRootExplore ? (
              <>
                {/* Continue Reading Hero Card (if user has started reading) */}
                {currentReadBook && (
                  <section
                    className="rounded-3xl border p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                    style={{
                      backgroundColor: theme.surface,
                      borderColor: theme.border,
                    }}
                  >
                    <div className="flex items-center gap-4 min-w-0">
                      <button
                        type="button"
                        onClick={() => handleOpenDetail(currentReadBook)}
                        className="w-[62px] h-[92px] shrink-0 cursor-pointer"
                      >
                        <BookCover
                          book={currentReadBook}
                          theme={theme}
                          isSaved={savedSet.has(currentReadBook.id)}
                          compact
                          className="w-full h-full"
                        />
                      </button>

                      <div className="min-w-0 space-y-1.5">
                        <span
                          className="text-[10px] font-extrabold uppercase tracking-[0.1em]"
                          style={{ color: theme.accent }}
                        >
                          Continue Reading
                        </span>
                        <h2 className="text-sm sm:text-base font-extrabold line-clamp-1">
                          {currentReadBook.title}
                        </h2>
                        <p
                          className="text-xs line-clamp-1"
                          style={{ color: theme.muted }}
                        >
                          {currentReadBook.author} · {currentReadBook.fmt} ·{" "}
                          {formatBytes(currentReadBook.size)}
                        </p>
                        {progressById[currentReadBook.id] && (
                          <div className="flex items-center gap-2 max-w-xs">
                            <div
                              className="flex-1 h-1.5 rounded-full overflow-hidden"
                              style={{ backgroundColor: theme.surfaceAlt }}
                            >
                              <div
                                className="h-full rounded-full"
                                style={{
                                  width: `${Math.max(
                                    4,
                                    progressById[currentReadBook.id].progressPct
                                  )}%`,
                                  backgroundColor: theme.accent,
                                }}
                              />
                            </div>
                            <span
                              className="text-[11px] font-extrabold tabular-nums"
                              style={{ color: theme.accent }}
                            >
                              {progressById[currentReadBook.id].progressPct}%
                            </span>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        type="button"
                        onClick={() => handleOpenReader(currentReadBook)}
                        className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-full text-xs font-extrabold transition hover:opacity-90 cursor-pointer"
                        style={{
                          backgroundColor: theme.cream,
                          color: theme.creamInk,
                        }}
                      >
                        <BookOpen
                          className="w-3.5 h-3.5"
                          style={{ color: theme.accent }}
                        />
                        <span>Continue</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => handleOpenDetail(currentReadBook)}
                        className="px-4 py-2.5 rounded-full border text-xs font-bold transition hover:opacity-85 cursor-pointer"
                        style={{
                          backgroundColor: theme.surfaceAlt,
                          borderColor: theme.border,
                          color: theme.ink,
                        }}
                      >
                        Details
                      </button>
                    </div>
                  </section>
                )}

                {/* 8 Color-Tinted Bento Categories */}
                <section className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h2 className="text-sm sm:text-base font-extrabold tracking-tight">
                      Explore All Categories
                    </h2>
                    <span
                      className="text-xs font-bold"
                      style={{ color: theme.accent }}
                    >
                      {childSections.length} categories
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 sm:gap-4">
                    {childSections.map((node) => {
                      const pal = getCategoryPalette(node.name, themeMode);
                      const coverFront = node.previews[0];
                      const coverBack = node.previews[1];
                      return (
                        <button
                          key={node.name}
                          type="button"
                          onClick={() => navigateExplorePath([node.name])}
                          className="group relative h-[168px] rounded-[22px] border p-4 flex flex-col justify-between text-left overflow-hidden transition duration-200 hover:-translate-y-0.5 hover:shadow-lg cursor-pointer"
                          style={{
                            backgroundColor: pal.bg,
                            borderColor: pal.border,
                            color: theme.ink,
                          }}
                        >
                          <span
                            className="absolute -right-6 -bottom-7 w-28 h-28 rounded-full pointer-events-none"
                            style={{ backgroundColor: pal.orb }}
                            aria-hidden="true"
                          />

                          <div className="relative z-10 pr-8 space-y-2">
                            <span
                              className="w-9 h-9 rounded-xl inline-flex items-center justify-center"
                              style={{ backgroundColor: pal.badgeBg }}
                            >
                              <CategoryIcon
                                name={node.name}
                                size={22}
                                accentColor={pal.accent}
                              />
                            </span>
                            <h3 className="text-[15px] font-extrabold leading-snug line-clamp-2">
                              {node.name}
                            </h3>
                          </div>

                          <div className="relative z-10 max-w-[65%]">
                            <span
                              className="inline-flex items-center px-2.5 py-1 rounded-xl text-[11px] font-extrabold"
                              style={{
                                backgroundColor: pal.badgeBg,
                                color: pal.accent,
                              }}
                            >
                              {node.totalCount.toLocaleString()} books
                            </span>
                          </div>

                          {coverFront ? (
                            <div
                              className="absolute right-0 bottom-0 w-24 h-24 pointer-events-none"
                              aria-hidden="true"
                            >
                              {coverBack ? (
                                <div className="absolute right-6 -bottom-3 w-[52px] h-[76px] rotate-[4deg] opacity-80">
                                  <BookCover
                                    book={coverBack}
                                    theme={theme}
                                    compact
                                    className="w-full h-full"
                                  />
                                </div>
                              ) : null}
                              <div className="absolute -right-1.5 -bottom-2.5 w-[60px] h-[88px] rotate-[14deg] group-hover:rotate-[11deg] group-hover:scale-105 transition-transform duration-300">
                                <BookCover
                                  book={coverFront}
                                  theme={theme}
                                  compact
                                  className="w-full h-full"
                                />
                              </div>
                            </div>
                          ) : (
                            <div
                              className="absolute right-2 bottom-1 opacity-30 rotate-[12deg] pointer-events-none"
                              aria-hidden="true"
                            >
                              <CategoryIcon
                                name={node.name}
                                size={54}
                                accentColor={pal.accent}
                              />
                            </div>
                          )}
                        </button>
                      );
                    })}
                  </div>
                </section>

                {/* NCTB Class 1-12 Quick Jump Strip */}
                <section className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-sm sm:text-base font-extrabold tracking-tight">
                        NCTB Textbooks (Pre-Primary – Class 12)
                      </h2>
                      <p className="text-xs" style={{ color: theme.muted }}>
                        1-tap jump to official Bangladesh board books by class
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() =>
                        navigateExplorePath(["Education & Textbooks"])
                      }
                      className="text-xs font-extrabold hover:underline cursor-pointer"
                      style={{ color: theme.accent }}
                    >
                      All Education →
                    </button>
                  </div>

                  <div className="flex items-center gap-2.5 overflow-x-auto pb-1.5 no-scrollbar">
                    {NCTB_CLASS_SHORTCUTS.map((item) => (
                      <button
                        key={item.label}
                        type="button"
                        onClick={() => navigateExplorePath(item.path)}
                        className="shrink-0 rounded-2xl border px-3.5 py-2.5 flex items-center gap-2.5 text-left transition hover:-translate-y-0.5 cursor-pointer"
                        style={{
                          backgroundColor: theme.surface,
                          borderColor: theme.border,
                        }}
                      >
                        <CategoryIcon
                          name={item.label}
                          size={22}
                          accentColor={theme.accent}
                        />
                        <div>
                          <p className="text-xs font-extrabold">{item.label}</p>
                          <p
                            className="text-[10px]"
                            style={{ color: theme.muted }}
                          >
                            {item.subtitle}
                          </p>
                        </div>
                      </button>
                    ))}
                  </div>
                </section>

                {/* Suggested For You Horizontal Shelf */}
                {suggestedBooks.length > 0 && (
                  <section className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <h2 className="text-sm sm:text-base font-extrabold tracking-tight">
                          Suggested For You
                        </h2>
                        <p className="text-xs" style={{ color: theme.muted }}>
                          {savedIds.length > 0 || recentIds.length > 0
                            ? "Personalized from your reading history & bookmarks"
                            : "Curated highlighted editions across the archive"}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => setActiveTab("search")}
                        className="text-xs font-extrabold hover:underline cursor-pointer"
                        style={{ color: theme.accent }}
                      >
                        Browse All →
                      </button>
                    </div>

                    <div className="flex items-stretch gap-3.5 overflow-x-auto pb-2 no-scrollbar">
                      {suggestedBooks.map(({ book, reason }) => (
                        <button
                          key={book.id}
                          type="button"
                          onClick={() => handleOpenDetail(book)}
                          className="w-36 shrink-0 rounded-2xl border p-2.5 text-left space-y-2 transition hover:-translate-y-0.5 cursor-pointer"
                          style={{
                            backgroundColor: theme.surface,
                            borderColor: theme.border,
                          }}
                        >
                          <BookCover
                            book={book}
                            theme={theme}
                            isSaved={savedSet.has(book.id)}
                            showFormatBadge
                            className="w-full aspect-[2/3]"
                          />
                          <div>
                            <p className="text-xs font-extrabold line-clamp-2 leading-snug">
                              {book.title}
                            </p>
                            <p
                              className="text-[10px] font-bold line-clamp-1 mt-0.5"
                              style={{ color: theme.accent }}
                            >
                              {reason}
                            </p>
                          </div>
                        </button>
                      ))}
                    </div>
                  </section>
                )}

                {/* Recently Viewed Strip (when non-empty) */}
                {recentBooks.length > 0 && (
                  <section className="space-y-3">
                    <div className="flex items-center gap-2">
                      <History
                        className="w-4 h-4"
                        style={{ color: theme.accent }}
                      />
                      <h2 className="text-sm sm:text-base font-extrabold tracking-tight">
                        Recently Viewed
                      </h2>
                    </div>

                    <div className="flex items-stretch gap-3 overflow-x-auto pb-1.5 no-scrollbar">
                      {recentBooks.map((book) => (
                        <button
                          key={book.id}
                          type="button"
                          onClick={() => handleOpenDetail(book)}
                          className="w-32 shrink-0 rounded-2xl border p-2 text-left space-y-1.5 transition hover:-translate-y-0.5 cursor-pointer"
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
                          <p className="text-[11px] font-extrabold line-clamp-2 leading-snug">
                            {book.title}
                          </p>
                        </button>
                      ))}
                    </div>
                  </section>
                )}

                {/* Featured Authors Strip */}
                <section className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-sm sm:text-base font-extrabold tracking-tight">
                        Featured Authors &amp; Scholars
                      </h2>
                      <p className="text-xs" style={{ color: theme.muted }}>
                        Explore curated shelves from{" "}
                        {authorDirectory.length.toLocaleString()} writers
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => setActiveTab("authors")}
                      className="text-xs font-extrabold hover:underline cursor-pointer"
                      style={{ color: theme.accent }}
                    >
                      Browse All Authors →
                    </button>
                  </div>

                  <div className="flex items-stretch gap-3 overflow-x-auto pb-1.5 no-scrollbar">
                    {FEATURED_AUTHOR_SHORTCUTS.map((item) => (
                      <button
                        key={item.label}
                        type="button"
                        onClick={() => navigateExplorePath(item.path)}
                        className="w-32 shrink-0 rounded-2xl border p-3 flex flex-col items-center text-center gap-2 transition hover:-translate-y-0.5 cursor-pointer"
                        style={{
                          backgroundColor: theme.surface,
                          borderColor: theme.border,
                        }}
                      >
                        <AuthorAvatar
                          name={item.label}
                          size={52}
                          theme={theme}
                        />
                        <span className="text-xs font-extrabold line-clamp-2 leading-snug">
                          {item.label}
                        </span>
                        <span
                          className="text-[10px] font-semibold line-clamp-1"
                          style={{ color: theme.muted }}
                        >
                          {item.subtitle}
                        </span>
                      </button>
                    ))}
                  </div>
                </section>

                {/* Literary Quote Card */}
                <section
                  className="rounded-3xl border p-5 sm:p-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                  style={{
                    backgroundColor: theme.surface,
                    borderColor: theme.border,
                  }}
                >
                  <div className="space-y-1.5 max-w-3xl">
                    <p
                      className="text-[10px] font-extrabold uppercase tracking-[0.12em]"
                      style={{ color: theme.accent }}
                    >
                      Daily Literary Note
                    </p>
                    <p className="text-sm sm:text-base font-bold leading-relaxed">
                      “{activeQuote.text}”
                    </p>
                    <p
                      className="text-xs font-semibold"
                      style={{ color: theme.muted }}
                    >
                      — {activeQuote.author}
                    </p>
                  </div>

                  <button
                    type="button"
                    onClick={() => setQuoteIdx((i) => i + 1)}
                    className="self-start sm:self-center inline-flex items-center gap-1.5 px-4 py-2 rounded-full border text-xs font-bold transition hover:opacity-85 shrink-0 cursor-pointer"
                    style={{
                      backgroundColor: theme.surfaceAlt,
                      borderColor: theme.border,
                      color: theme.ink,
                    }}
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    <span>Next Quote</span>
                  </button>
                </section>
              </>
            ) : (
              /* DRILL-DOWN SUBSECTIONS & BOOKS */
              <div className="space-y-6">
                {childSections.length > 0 && (
                  <section className="space-y-3">
                    {isAuthorsLeafGrid ? (
                      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
                        {childSections
                          .slice(0, visibleSectionCount)
                          .map((subNode) => (
                            <button
                              key={subNode.name}
                              type="button"
                              onClick={() =>
                                navigateExplorePath([
                                  ...explorePath,
                                  subNode.name,
                                ])
                              }
                              className="rounded-2xl border p-4 flex flex-col items-center text-center gap-2.5 transition hover:-translate-y-0.5 cursor-pointer"
                              style={{
                                backgroundColor: theme.surface,
                                borderColor: theme.border,
                              }}
                            >
                              <AuthorAvatar
                                name={subNode.name}
                                size={64}
                                theme={theme}
                              />
                              <span className="text-xs sm:text-sm font-extrabold line-clamp-2 leading-snug">
                                {subNode.name}
                              </span>
                              <span
                                className="px-2.5 py-0.5 rounded-full border text-[11px] font-bold"
                                style={{
                                  backgroundColor: theme.surfaceAlt,
                                  borderColor: theme.border,
                                  color: theme.accent,
                                }}
                              >
                                {subNode.totalCount.toLocaleString()} books
                              </span>
                            </button>
                          ))}
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3.5">
                        {childSections
                          .slice(0, visibleSectionCount)
                          .map((subNode) => {
                            const pal = getCategoryPalette(
                              subNode.name,
                              themeMode
                            );
                            const subCover = subNode.previews[0];
                            return (
                              <button
                                key={subNode.name}
                                type="button"
                                onClick={() =>
                                  navigateExplorePath([
                                    ...explorePath,
                                    subNode.name,
                                  ])
                                }
                                className="group relative min-h-[124px] rounded-[20px] border p-3.5 flex flex-col justify-between text-left overflow-hidden transition hover:-translate-y-0.5 hover:shadow-md cursor-pointer"
                                style={{
                                  backgroundColor: pal.bg,
                                  borderColor: pal.border,
                                  color: theme.ink,
                                }}
                              >
                                <span
                                  className="absolute -right-5 -bottom-6 w-24 h-24 rounded-full pointer-events-none"
                                  style={{ backgroundColor: pal.orb }}
                                  aria-hidden="true"
                                />

                                <h3 className="relative z-10 text-xs sm:text-[13px] font-extrabold leading-snug pr-12 line-clamp-2">
                                  {subNode.name}
                                </h3>

                                <div className="relative z-10 max-w-[72%] mt-3">
                                  <span
                                    className="inline-flex items-center px-2.5 py-0.5 rounded-xl text-[10.5px] font-extrabold"
                                    style={{
                                      backgroundColor: pal.badgeBg,
                                      color: pal.accent,
                                    }}
                                  >
                                    {subNode.totalCount.toLocaleString()} books
                                  </span>
                                </div>

                                {subCover ? (
                                  <div
                                    className="absolute -right-1.5 -bottom-2 w-[48px] h-[70px] rotate-[13deg] group-hover:rotate-[10deg] group-hover:scale-105 transition-transform pointer-events-none"
                                    aria-hidden="true"
                                  >
                                    <BookCover
                                      book={subCover}
                                      theme={theme}
                                      compact
                                      className="w-full h-full"
                                    />
                                  </div>
                                ) : (
                                  <div
                                    className="absolute right-2 bottom-1 opacity-30 rotate-[12deg] pointer-events-none"
                                    aria-hidden="true"
                                  >
                                    <CategoryIcon
                                      name={subNode.name}
                                      size={38}
                                      accentColor={pal.accent}
                                    />
                                  </div>
                                )}
                              </button>
                            );
                          })}
                      </div>
                    )}

                    {visibleSectionCount < childSections.length && (
                      <div className="flex justify-center pt-2">
                        <button
                          type="button"
                          onClick={() =>
                            setVisibleSectionCount(
                              (c) => c + SECTIONS_PAGE_SIZE
                            )
                          }
                          className="px-5 py-2 rounded-full border text-xs font-extrabold transition hover:opacity-85 cursor-pointer"
                          style={{
                            backgroundColor: theme.surface,
                            borderColor: theme.border,
                            color: theme.ink,
                          }}
                        >
                          Show More Sections (
                          {(
                            childSections.length - visibleSectionCount
                          ).toLocaleString()}{" "}
                          remaining)
                        </button>
                      </div>
                    )}
                  </section>
                )}

                {(directBooksFiltered.length > 0 ||
                  folderAllBooksFiltered.length > 0) && (
                  <section className="space-y-3 pt-1">
                    <h3 className="text-sm sm:text-base font-extrabold">
                      {currentNode.directBooks.length > 0
                        ? `Books in ${currentNode.name}`
                        : `Browse Books in ${currentNode.name}`}
                    </h3>
                    <BookCollectionView
                      books={
                        currentNode.directBooks.length > 0
                          ? directBooksFiltered
                          : folderAllBooksFiltered
                      }
                      savedSet={savedSet}
                      theme={theme}
                      progressById={progressById}
                      emptyTitle="No books match this filter"
                      emptySubtitle="Try clearing the folder search box above."
                      onOpenDetail={handleOpenDetail}
                      onQuickRead={handleOpenReader}
                      onToggleSave={toggleSave}
                    />
                  </section>
                )}
              </div>
            )}
          </div>
        )}

        {/* ==================== TAB 2: ALL BOOKS (GLOBAL SEARCH) ==================== */}
        {activeTab === "search" && (
          <div className="space-y-5">
            <div
              className="rounded-3xl border p-4 sm:p-5 space-y-3.5"
              style={{
                backgroundColor: theme.surface,
                borderColor: theme.border,
              }}
            >
              <div className="flex flex-col md:flex-row gap-3">
                <div className="relative flex-1">
                  <Search
                    className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2"
                    style={{ color: theme.muted }}
                  />
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Search 29,178+ Bangla & English books, authors, Class 1–12…"
                    className="w-full pl-11 pr-9 py-2.5 sm:py-3 rounded-full border text-xs sm:text-sm focus:outline-none"
                    style={{
                      backgroundColor: theme.surfaceAlt,
                      borderColor: theme.border,
                      color: theme.ink,
                    }}
                  />
                  {query && (
                    <button
                      type="button"
                      onClick={() => setQuery("")}
                      aria-label="Clear search"
                      className="absolute right-3.5 top-1/2 -translate-y-1/2 cursor-pointer"
                      style={{ color: theme.muted }}
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>

                <select
                  value={searchCat}
                  onChange={(e) => setSearchCat(e.target.value)}
                  aria-label="Filter by category"
                  className="px-4 py-2.5 rounded-full border text-xs font-bold focus:outline-none cursor-pointer"
                  style={{
                    backgroundColor: theme.surfaceAlt,
                    borderColor: theme.border,
                    color: theme.ink,
                  }}
                >
                  <option value="ALL">
                    All Categories ({books.length.toLocaleString()})
                  </option>
                  <option value="SAVED">Saved ({savedIds.length})</option>
                  {(summary?.cats || []).map((c) => (
                    <option key={c} value={c}>
                      {c}
                    </option>
                  ))}
                </select>
              </div>

              {(searchMatchingAuthors.length > 0 ||
                searchMatchingFolders.length > 0) && (
                <div className="space-y-2.5 pt-1">
                  {searchMatchingAuthors.length > 0 && (
                    <div className="flex items-center gap-2 overflow-x-auto pb-1 no-scrollbar">
                      <span
                        className="text-[10px] font-extrabold uppercase tracking-wider shrink-0"
                        style={{ color: theme.muted }}
                      >
                        Authors:
                      </span>
                      {searchMatchingAuthors.map((a) => (
                        <button
                          key={a.key}
                          type="button"
                          onClick={() => navigateExplorePath(a.path)}
                          className="inline-flex items-center gap-2 px-3 py-1 rounded-full border text-xs font-bold shrink-0 transition hover:opacity-85 cursor-pointer"
                          style={{
                            backgroundColor: theme.surfaceAlt,
                            borderColor: theme.border,
                            color: theme.ink,
                          }}
                        >
                          <AuthorAvatar
                            name={a.name}
                            size={20}
                            theme={theme}
                          />
                          <span>{a.name}</span>
                          <span style={{ color: theme.accent }}>
                            ({a.count})
                          </span>
                        </button>
                      ))}
                    </div>
                  )}

                  {searchMatchingFolders.length > 0 && (
                    <div className="flex items-center gap-2 overflow-x-auto pb-1 no-scrollbar">
                      <span
                        className="text-[10px] font-extrabold uppercase tracking-wider shrink-0"
                        style={{ color: theme.muted }}
                      >
                        Folders:
                      </span>
                      {searchMatchingFolders.map((f) => (
                        <button
                          key={f.path.join("/")}
                          type="button"
                          onClick={() => navigateExplorePath(f.path)}
                          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full border text-xs font-bold shrink-0 transition hover:opacity-85 cursor-pointer"
                          style={{
                            backgroundColor: theme.surfaceAlt,
                            borderColor: theme.border,
                            color: theme.ink,
                          }}
                        >
                          <CategoryIcon
                            name={f.name}
                            size={15}
                            accentColor={theme.accent}
                          />
                          <span>{f.name}</span>
                          <span style={{ color: theme.accent }}>
                            ({f.count.toLocaleString()})
                          </span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            <BookCollectionView
              books={searchResults}
              savedSet={savedSet}
              theme={theme}
              progressById={progressById}
              onOpenDetail={handleOpenDetail}
              onQuickRead={handleOpenReader}
              onToggleSave={toggleSave}
            />
          </div>
        )}

        {/* ==================== TAB 3: AUTHORS DIRECTORY ==================== */}
        {activeTab === "authors" && (
          <div className="space-y-5">
            <div
              className="rounded-3xl border p-4 sm:p-5 space-y-3.5"
              style={{
                backgroundColor: theme.surface,
                borderColor: theme.border,
              }}
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="relative flex-1">
                  <Search
                    className="w-4 h-4 absolute left-4 top-1/2 -translate-y-1/2"
                    style={{ color: theme.muted }}
                  />
                  <input
                    type="text"
                    value={authorQuery}
                    onChange={(e) => setAuthorQuery(e.target.value)}
                    placeholder="Search authors & scholars…"
                    className="w-full pl-11 pr-9 py-2.5 rounded-full border text-xs sm:text-sm focus:outline-none"
                    style={{
                      backgroundColor: theme.surfaceAlt,
                      borderColor: theme.border,
                      color: theme.ink,
                    }}
                  />
                  {authorQuery && (
                    <button
                      type="button"
                      onClick={() => setAuthorQuery("")}
                      aria-label="Clear author search"
                      className="absolute right-3.5 top-1/2 -translate-y-1/2 cursor-pointer"
                      style={{ color: theme.muted }}
                    >
                      <X className="w-4 h-4" />
                    </button>
                  )}
                </div>

                <span
                  className="self-start sm:self-auto px-3.5 py-1.5 rounded-full border text-xs font-extrabold"
                  style={{
                    backgroundColor: theme.surfaceAlt,
                    borderColor: theme.border,
                    color: theme.accent,
                  }}
                >
                  {filteredAuthors.length.toLocaleString()} authors
                </span>
              </div>

              <div className="flex items-center gap-2 overflow-x-auto pb-1 no-scrollbar">
                {AUTHOR_GROUP_FILTERS.map((gf) => {
                  const active = authorGroup === gf.key;
                  return (
                    <button
                      key={gf.key}
                      type="button"
                      onClick={() => setAuthorGroup(gf.key)}
                      className="px-3.5 py-1.5 rounded-full border text-xs font-bold shrink-0 transition cursor-pointer"
                      style={{
                        backgroundColor: active
                          ? theme.cream
                          : theme.surfaceAlt,
                        borderColor: active ? theme.cream : theme.border,
                        color: active ? theme.creamInk : theme.ink,
                      }}
                    >
                      {gf.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {filteredAuthors.length === 0 ? (
              <div
                className="rounded-3xl border py-16 px-4 text-center space-y-2"
                style={{
                  backgroundColor: theme.surfaceAlt,
                  borderColor: theme.borderSubtle,
                }}
              >
                <p className="text-base font-extrabold">No authors found</p>
                <p className="text-xs" style={{ color: theme.muted }}>
                  Try a different spelling or switch to All Authors.
                </p>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3.5">
                  {filteredAuthors
                    .slice(0, visibleAuthorCount)
                    .map((item) => (
                      <button
                        key={item.key}
                        type="button"
                        onClick={() => navigateExplorePath(item.path)}
                        className="rounded-2xl border p-4 flex flex-col items-center text-center gap-2 transition hover:-translate-y-0.5 hover:shadow-md cursor-pointer"
                        style={{
                          backgroundColor: theme.surface,
                          borderColor: theme.border,
                        }}
                      >
                        <AuthorAvatar
                          name={item.name}
                          size={68}
                          theme={theme}
                        />
                        <span className="text-xs sm:text-sm font-extrabold line-clamp-2 leading-snug">
                          {item.name}
                        </span>
                        <div className="flex flex-wrap items-center justify-center gap-1">
                          <span
                            className="px-2 py-0.5 rounded-full border text-[10px] font-bold"
                            style={{
                              backgroundColor: theme.surfaceAlt,
                              borderColor: theme.border,
                              color: theme.accent,
                            }}
                          >
                            {item.count.toLocaleString()}{" "}
                            {item.count === 1 ? "book" : "books"}
                          </span>
                          {item.subfolderCount > 0 && (
                            <span
                              className="px-2 py-0.5 rounded-full border text-[10px] font-bold"
                              style={{
                                backgroundColor: theme.accentSoft,
                                borderColor: theme.accent,
                                color: theme.accent,
                              }}
                            >
                              {item.subfolderCount} sec
                            </span>
                          )}
                        </div>
                      </button>
                    ))}
                </div>

                {visibleAuthorCount < filteredAuthors.length && (
                  <div className="flex justify-center pt-2">
                    <button
                      type="button"
                      onClick={() =>
                        setVisibleAuthorCount((c) => c + AUTHORS_PAGE_SIZE)
                      }
                      className="px-6 py-2.5 rounded-full text-xs sm:text-sm font-extrabold transition hover:opacity-90 cursor-pointer"
                      style={{
                        backgroundColor: theme.cream,
                        color: theme.creamInk,
                      }}
                    >
                      Load More Authors (
                      {(
                        filteredAuthors.length - visibleAuthorCount
                      ).toLocaleString()}{" "}
                      remaining)
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* ==================== TAB 4: MY SHELF (READING, COLLECTIONS & NOTES) ==================== */}
        {activeTab === "shelf" && (
          <div className="space-y-8">
            {/* Reading Progress Section */}
            <section className="space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="text-sm sm:text-base font-extrabold">
                  Currently Reading &amp; Progress ({readingShelfItems.length})
                </h2>
                {readingShelfItems.length === 0 && (
                  <button
                    type="button"
                    onClick={() => setActiveTab("explore")}
                    className="text-xs font-extrabold hover:underline cursor-pointer"
                    style={{ color: theme.accent }}
                  >
                    Explore Books →
                  </button>
                )}
              </div>

              {readingShelfItems.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3.5">
                  {readingShelfItems.map(({ book, progress }) => {
                    const pct = progress?.progressPct ?? 0;
                    return (
                      <div
                        key={book.id}
                        className="rounded-2xl border p-3.5 flex gap-3.5 items-center"
                        style={{
                          backgroundColor: theme.surface,
                          borderColor: theme.border,
                        }}
                      >
                        <button
                          type="button"
                          onClick={() => handleOpenDetail(book)}
                          className="w-[62px] h-[92px] shrink-0 cursor-pointer"
                        >
                          <BookCover
                            book={book}
                            theme={theme}
                            isSaved={savedSet.has(book.id)}
                            compact
                            className="w-full h-full"
                          />
                        </button>

                        <div className="flex-1 min-w-0 space-y-2">
                          <div>
                            <h3 className="text-xs sm:text-sm font-extrabold line-clamp-2 leading-snug">
                              {book.title}
                            </h3>
                            <p
                              className="text-[11px] line-clamp-1"
                              style={{ color: theme.muted }}
                            >
                              {book.author}
                            </p>
                          </div>

                          <div className="space-y-1">
                            <div className="flex items-center justify-between text-[10px] font-bold">
                              <span style={{ color: theme.muted }}>
                                {progress
                                  ? `Page ${progress.currentPage} / ${progress.totalPages}`
                                  : "Started reading"}
                              </span>
                              <span style={{ color: theme.accent }}>
                                {pct}%
                              </span>
                            </div>
                            <div
                              className="h-1.5 rounded-full overflow-hidden"
                              style={{ backgroundColor: theme.surfaceAlt }}
                            >
                              <div
                                className="h-full rounded-full"
                                style={{
                                  width: `${Math.max(4, pct)}%`,
                                  backgroundColor: theme.accent,
                                }}
                              />
                            </div>
                          </div>

                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              onClick={() => handleOpenReader(book)}
                              className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-[11px] font-extrabold cursor-pointer"
                              style={{
                                backgroundColor: theme.cream,
                                color: theme.creamInk,
                              }}
                            >
                              <BookOpen className="w-3 h-3" />
                              <span>Continue</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => handleOpenDetail(book)}
                              className="px-3 py-1 rounded-full border text-[11px] font-bold cursor-pointer"
                              style={{
                                backgroundColor: theme.surfaceAlt,
                                borderColor: theme.border,
                                color: theme.ink,
                              }}
                            >
                              Details
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div
                  className="rounded-2xl border p-5 text-xs"
                  style={{
                    backgroundColor: theme.surface,
                    borderColor: theme.border,
                    color: theme.muted,
                  }}
                >
                  Open any book and click <strong>Read Online</strong> or{" "}
                  <strong>Mark Current</strong> to track your reading progress
                  here.
                </div>
              )}
            </section>

            {/* Saved Bookmarks, Study Notes & Custom Reading Lists */}
            <section className="space-y-4">
              <div
                className="rounded-3xl border p-4 sm:p-5 space-y-3.5"
                style={{
                  backgroundColor: theme.surface,
                  borderColor: theme.border,
                }}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <FolderPlus
                      className="w-4 h-4"
                      style={{ color: theme.accent }}
                    />
                    <h2 className="text-sm sm:text-base font-extrabold">
                      Bookmarks, Study Notes &amp; Reading Lists
                    </h2>
                  </div>

                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      if (!newListName.trim()) return;
                      handleCreateCollection(newListName);
                      setNewListName("");
                    }}
                    className="flex items-center gap-2"
                  >
                    <input
                      type="text"
                      value={newListName}
                      onChange={(e) => setNewListName(e.target.value)}
                      placeholder="New reading list name…"
                      className="px-3.5 py-1.5 rounded-full border text-xs focus:outline-none"
                      style={{
                        backgroundColor: theme.surfaceAlt,
                        borderColor: theme.border,
                        color: theme.ink,
                      }}
                    />
                    <button
                      type="submit"
                      className="inline-flex items-center gap-1 px-3.5 py-1.5 rounded-full text-xs font-extrabold cursor-pointer"
                      style={{
                        backgroundColor: theme.cream,
                        color: theme.creamInk,
                      }}
                    >
                      <Plus className="w-3.5 h-3.5" />
                      <span>Create</span>
                    </button>
                  </form>
                </div>

                {/* Filter Pills */}
                <div className="flex items-center gap-2 overflow-x-auto pb-1 no-scrollbar">
                  <button
                    type="button"
                    onClick={() => setShelfFilter("SAVED")}
                    className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full border text-xs font-bold shrink-0 cursor-pointer"
                    style={{
                      backgroundColor:
                        shelfFilter === "SAVED"
                          ? theme.cream
                          : theme.surfaceAlt,
                      borderColor:
                        shelfFilter === "SAVED" ? theme.cream : theme.border,
                      color:
                        shelfFilter === "SAVED" ? theme.creamInk : theme.ink,
                    }}
                  >
                    <Bookmark className="w-3.5 h-3.5" />
                    <span>Saved ({savedBooks.length})</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setShelfFilter("NOTES")}
                    className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full border text-xs font-bold shrink-0 cursor-pointer"
                    style={{
                      backgroundColor:
                        shelfFilter === "NOTES"
                          ? theme.cream
                          : theme.surfaceAlt,
                      borderColor:
                        shelfFilter === "NOTES" ? theme.cream : theme.border,
                      color:
                        shelfFilter === "NOTES" ? theme.creamInk : theme.ink,
                    }}
                  >
                    <NotebookPen className="w-3.5 h-3.5" />
                    <span>With Notes ({notedBooks.length})</span>
                  </button>

                  {collections.map((col) => {
                    const active = shelfFilter === col.id;
                    return (
                      <div
                        key={col.id}
                        className="inline-flex items-center rounded-full border shrink-0 overflow-hidden"
                        style={{
                          backgroundColor: active
                            ? theme.cream
                            : theme.surfaceAlt,
                          borderColor: active ? theme.cream : theme.border,
                        }}
                      >
                        <button
                          type="button"
                          onClick={() => setShelfFilter(col.id)}
                          className="pl-3.5 pr-2 py-1.5 text-xs font-bold cursor-pointer"
                          style={{
                            color: active ? theme.creamInk : theme.ink,
                          }}
                        >
                          {col.name} ({col.bookIds.length})
                        </button>
                        <button
                          type="button"
                          onClick={() => handleDeleteCollection(col.id)}
                          title={`Delete ${col.name}`}
                          aria-label={`Delete ${col.name}`}
                          className="pr-2.5 pl-1 py-1.5 hover:opacity-75 cursor-pointer"
                          style={{
                            color: active ? theme.creamInk : theme.muted,
                          }}
                        >
                          <Trash2 className="w-3 h-3" />
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>

              <BookCollectionView
                books={shelfActiveBooks}
                savedSet={savedSet}
                theme={theme}
                progressById={progressById}
                emptyTitle={
                  shelfFilter === "SAVED"
                    ? "No saved books yet"
                    : shelfFilter === "NOTES"
                      ? "No study notes written yet"
                      : "This reading list is empty"
                }
                emptySubtitle={
                  shelfFilter === "SAVED"
                    ? "Tap the bookmark button on any book to save it to your shelf."
                    : shelfFilter === "NOTES"
                      ? "Open any book and write a personal study note in Book Details or the Reader."
                      : "Open any book's Overview and add it to this reading list."
                }
                onOpenDetail={handleOpenDetail}
                onQuickRead={handleOpenReader}
                onToggleSave={toggleSave}
              />
            </section>
          </div>
        )}

        {/* ==================== TAB 5: STATS & BACKUP ==================== */}
        {activeTab === "stats" && (
          <StatsAndBackupView
            books={books}
            savedIds={savedIds}
            progressById={progressById}
            notesById={notesById}
            collections={collections}
            streak={streak}
            theme={theme}
            onSelectCategory={(cat) => navigateExplorePath([cat])}
            onOpenDetail={handleOpenDetail}
            onRestoreBackup={handleRestoreBackup}
          />
        )}

        {/* ==================== MINIMAL SEO FOOTER ==================== */}
        <footer
          className="border-t mt-10 pt-8 pb-4 space-y-4"
          style={{ borderColor: theme.borderSubtle }}
        >
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div>
              <h2 className="text-sm font-extrabold">
                AnaBook — Bangladesh’s Biggest Online eLibrary &amp; PDF Archive
              </h2>
              <p className="text-xs mt-0.5" style={{ color: theme.muted }}>
                {books.length.toLocaleString()} books ·{" "}
                {summary?.authorsCount.toLocaleString() ?? "4,575"} authors ·{" "}
                {savedIds.length.toLocaleString()} saved · Archive{" "}
                {summary ? formatBytes(summary.totalBytes) : "—"}
              </p>
            </div>
            <span className="text-xs" style={{ color: theme.muted }}>
              PDF · EPUB · MOBI · DOCX · NCTB Class 1–12
            </span>
          </div>

          <p
            className="text-xs leading-relaxed max-w-3xl"
            style={{ color: theme.muted }}
          >
            Browse Bangladesh’s biggest free eLibrary, PDF library, and eBook
            library. Explore categorized Bangla books, English literature,
            Pre-Primary to Class 12 NCTB textbooks, Islamic &amp; comparative
            religion books, authors &amp; scholars, and multi-volume series with
            direct browser reading and offline Google Drive downloads.
          </p>

          <div className="flex flex-wrap items-center gap-2">
            {(summary?.cats || []).map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => navigateExplorePath([c])}
                className="px-3 py-1 rounded-full border text-xs font-semibold transition hover:opacity-85 cursor-pointer"
                style={{
                  backgroundColor: theme.surface,
                  borderColor: theme.border,
                  color: theme.ink,
                }}
              >
                {c}
              </button>
            ))}
          </div>
        </footer>
      </div>

      {/* Floating Back to Top Button */}
      {showScrollTop && (
        <button
          type="button"
          onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
          aria-label="Back to top"
          title="Back to top"
          className="fixed bottom-5 right-5 z-40 w-11 h-11 rounded-full border shadow-lg flex items-center justify-center transition hover:scale-105 cursor-pointer"
          style={{
            backgroundColor: theme.cream,
            borderColor: theme.border,
            color: theme.creamInk,
          }}
        >
          <ArrowUp className="w-4 h-4" />
        </button>
      )}

      {/* Modals */}
      <BookDetailModal
        book={detailBook}
        progress={detailBook ? progressById[detailBook.id] : undefined}
        note={detailBook ? notesById[detailBook.id] : undefined}
        collections={collections}
        isCurrentRead={Boolean(detailBook && currentReadId === detailBook.id)}
        isSaved={Boolean(detailBook && savedSet.has(detailBook.id))}
        theme={theme}
        onClose={() => setDetailBook(null)}
        onReadOnline={(b) => {
          setDetailBook(null);
          handleOpenReader(b);
        }}
        onToggleSave={toggleSave}
        onSetCurrentlyReading={handleSetCurrentlyReading}
        onUpdateProgress={handleUpdateProgress}
        onSaveNote={handleSaveNote}
        onToggleCollectionBook={handleToggleCollectionBook}
        onCreateCollection={handleCreateCollection}
        onNavigateFolder={navigateExplorePath}
        onFilterAuthor={handleJumpAuthorFromBook}
      />

      <ReaderPreviewModal
        book={previewBook}
        isSaved={Boolean(previewBook && savedSet.has(previewBook.id))}
        progress={previewBook ? progressById[previewBook.id] : undefined}
        note={previewBook ? notesById[previewBook.id] : undefined}
        theme={theme}
        onToggleSave={toggleSave}
        onUpdateProgress={handleUpdateProgress}
        onSaveNote={handleSaveNote}
        onLogReadingMinute={handleLogReadingMinute}
        onClose={() => setPreviewBook(null)}
      />

      <AuthorDetailModal
        visible={authorModalOpen}
        authorName={currentNode.name}
        group={authorDetail?.group || explorePath[1] || "Authors & Scholars"}
        bookCount={currentNode.totalCount}
        subfolderCount={currentNode.children.size}
        shortDesc={authorDetail?.shortDesc}
        bio={authorDetail?.bio}
        wikiUrl={authorDetail?.wikiUrl}
        theme={theme}
        onClose={() => setAuthorModalOpen(false)}
      />
    </div>
  );
}
