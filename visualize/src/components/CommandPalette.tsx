"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import {
  BarChart3,
  BookOpen,
  Compass,
  Download,
  Library,
  Loader2,
  Moon,
  Palette,
  Search,
  Sparkles,
  Sun,
  X,
} from "lucide-react";
import { useWebTheme } from "@/context/WebThemeContext";
import { THEME_PRESETS } from "@/lib/anabookTheme";
import { loadCatalogOnce } from "@/lib/catalogClient";
import {
  AuthorItem,
  extractAuthorDirectory,
  NCTB_CLASS_SHORTCUTS,
} from "@/lib/libraryTree";
import { BookItem, formatBytes } from "@/types/library";
import { AuthorAvatar } from "./library/AuthorAvatar";
import { BookCover } from "./library/BookCover";
import { CategoryIcon } from "./library/CategoryIcon";

const APK_URL =
  "https://github.com/salman-anik/AnaBook/releases/latest/download/AnaBook.apk";

export interface AnaBookNavDetail {
  tab?: "explore" | "search" | "authors" | "shelf" | "stats";
  cat?: string;
  path?: string[];
  q?: string;
  bookId?: string;
}

interface PaletteRow {
  id: string;
  group: string;
  label: string;
  subtitle?: string;
  kind: "action" | "category" | "author" | "book";
  book?: BookItem;
  author?: AuthorItem;
  onSelect: () => void;
}

/**
 * Global Ctrl+K / Cmd+K Command Palette for instant search across 29,178+ books,
 * 360+ authors, NCTB Class 1-12 folders, and quick theme/navigation actions.
 */
export function CommandPalette() {
  const router = useRouter();
  const pathname = usePathname();
  const isLibrary = pathname?.startsWith("/library");
  const {
    commandOpen,
    setCommandOpen,
    theme,
    themeMode,
    toggleThemeMode,
    cyclePreset,
    presetKey,
  } = useWebTheme();

  const [query, setQuery] = useState("");
  const [books, setBooks] = useState<BookItem[]>([]);
  const [cats, setCats] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!commandOpen) {
      setQuery("");
      setActiveIndex(0);
      return;
    }

    const timer = setTimeout(() => inputRef.current?.focus(), 30);

    if (books.length === 0) {
      setLoading(true);
      loadCatalogOnce()
        .then(({ books: loaded, summary }) => {
          setBooks(loaded);
          setCats(summary.cats);
          setLoading(false);
        })
        .catch(() => setLoading(false));
    }

    return () => clearTimeout(timer);
  }, [commandOpen, books.length]);

  const authors = useMemo(
    () => (books.length > 0 ? extractAuthorDirectory(books, new Set()) : []),
    [books]
  );

  const goToLibrary = (detail: AnaBookNavDetail) => {
    setCommandOpen(false);
    const params = new URLSearchParams();
    if (detail.bookId) params.set("book", detail.bookId);
    else if (detail.path && detail.path.length > 0)
      params.set("path", detail.path.join("/"));
    else if (detail.cat) params.set("cat", detail.cat);
    if (detail.q) params.set("q", detail.q);
    if (detail.tab && detail.tab !== "explore") params.set("tab", detail.tab);

    const qs = params.toString();
    const target = qs ? `/library/?${qs}` : "/library/";

    if (isLibrary) {
      window.history.replaceState(null, "", target);
      window.dispatchEvent(
        new CustomEvent<AnaBookNavDetail>("anabook:navigate", { detail })
      );
    } else {
      router.push(target);
    }
  };

  const rows = useMemo<PaletteRow[]>(() => {
    const q = query.trim().toLowerCase();
    const list: PaletteRow[] = [];

    if (!q) {
      list.push(
        {
          id: "act-explore",
          group: "Quick Actions",
          label: "Browse All Categories (Bento Explorer)",
          subtitle: "Bangla, English, NCTB Class 1–12, Religion & Series",
          kind: "action",
          onSelect: () => goToLibrary({ tab: "explore", path: [] }),
        },
        {
          id: "act-shelf",
          group: "Quick Actions",
          label: "Open My Shelf & Saved Bookmarks",
          subtitle: "Reading progress, notes & custom lists",
          kind: "action",
          onSelect: () => goToLibrary({ tab: "shelf" }),
        },
        {
          id: "act-stats",
          group: "Quick Actions",
          label: "View Reading Stats & Backup",
          subtitle: "Daily streak, archive breakdown & JSON export",
          kind: "action",
          onSelect: () => goToLibrary({ tab: "stats" }),
        },
        {
          id: "act-mode",
          group: "Appearance",
          label:
            themeMode === "light"
              ? "Switch to Dark Mode"
              : "Switch to Light Mode",
          subtitle: "Applies across Online Library & Navbar",
          kind: "action",
          onSelect: () => {
            toggleThemeMode();
            setCommandOpen(false);
          },
        },
        {
          id: "act-preset",
          group: "Appearance",
          label: `Cycle Theme Preset (Current: ${THEME_PRESETS[presetKey].label})`,
          subtitle: "Espresso · Matcha · Midnight · Sepia · Rosewood",
          kind: "action",
          onSelect: () => {
            cyclePreset();
          },
        },
        {
          id: "act-apk",
          group: "Downloads",
          label: "Download AnaBook Android APK",
          subtitle: "Offline reader app with mistouch lock",
          kind: "action",
          onSelect: () => {
            setCommandOpen(false);
            window.open(APK_URL, "_blank", "noopener,noreferrer");
          },
        }
      );
      return list;
    }

    // 1. Matching categories & NCTB classes
    for (const c of cats) {
      if (c.toLowerCase().includes(q)) {
        list.push({
          id: `cat-${c}`,
          group: "Categories",
          label: c,
          subtitle: "Open category folder",
          kind: "category",
          onSelect: () => goToLibrary({ tab: "explore", path: [c] }),
        });
      }
    }
    for (const cls of NCTB_CLASS_SHORTCUTS) {
      if (
        cls.label.toLowerCase().includes(q) ||
        cls.subtitle.toLowerCase().includes(q)
      ) {
        list.push({
          id: `nctb-${cls.label}`,
          group: "NCTB Textbooks",
          label: `${cls.label} (${cls.subtitle})`,
          subtitle: "Education & Textbooks",
          kind: "category",
          onSelect: () => goToLibrary({ tab: "explore", path: cls.path }),
        });
      }
    }

    // 2. Matching authors
    let authorCount = 0;
    for (const a of authors) {
      if (a.name.toLowerCase().includes(q)) {
        list.push({
          id: `auth-${a.key}`,
          group: "Authors & Scholars",
          label: a.name,
          subtitle: `${a.group} · ${a.count.toLocaleString()} books`,
          kind: "author",
          author: a,
          onSelect: () => goToLibrary({ tab: "explore", path: a.path }),
        });
        authorCount++;
        if (authorCount >= 5) break;
      }
    }

    // 3. Matching books (multi-term AND)
    const terms = q.split(/\s+/).filter(Boolean);
    const matchedBooks: BookItem[] = [];
    for (const b of books) {
      let ok = true;
      for (const t of terms) {
        if (!b.searchBlob.includes(t)) {
          ok = false;
          break;
        }
      }
      if (ok) {
        matchedBooks.push(b);
        if (matchedBooks.length >= 10) break;
      }
    }

    for (const b of matchedBooks) {
      list.push({
        id: `book-${b.id}`,
        group: "Books",
        label: b.title,
        subtitle: `${b.author} · ${b.fmt} · ${formatBytes(b.size)}`,
        kind: "book",
        book: b,
        onSelect: () => goToLibrary({ bookId: b.id }),
      });
    }

    // 4. Fallback global search row
    list.push({
      id: "search-all-fallback",
      group: "Search All Books",
      label: `Search all books for “${query.trim()}”`,
      subtitle: "Open full filterable results in All Books",
      kind: "action",
      onSelect: () => goToLibrary({ tab: "search", q: query.trim() }),
    });

    return list;
  }, [query, cats, authors, books, themeMode, presetKey]);

  useEffect(() => {
    setActiveIndex(0);
  }, [query, commandOpen]);

  useEffect(() => {
    if (!commandOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setCommandOpen(false);
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIndex((i) => (rows.length ? (i + 1) % rows.length : 0));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIndex((i) =>
          rows.length ? (i - 1 + rows.length) % rows.length : 0
        );
      } else if (e.key === "Enter" && rows[activeIndex]) {
        e.preventDefault();
        rows[activeIndex].onSelect();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [commandOpen, rows, activeIndex, setCommandOpen]);

  if (!commandOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[70] bg-black/65 backdrop-blur-sm flex items-start justify-center pt-[10vh] px-3 sm:px-6"
      onClick={() => setCommandOpen(false)}
      role="dialog"
      aria-modal="true"
      aria-label="Global Command Palette"
    >
      <div
        className="w-full max-w-2xl rounded-3xl border overflow-hidden shadow-2xl flex flex-col max-h-[76vh]"
        style={{
          backgroundColor: theme.surface,
          borderColor: theme.border,
          color: theme.ink,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Header */}
        <div
          className="px-4 py-3.5 border-b flex items-center gap-3"
          style={{ borderColor: theme.border }}
        >
          <Search className="w-4 h-4 shrink-0" style={{ color: theme.accent }} />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Jump to any of 29,178+ books, authors, Class 1–12, or actions…"
            className="flex-1 bg-transparent text-sm font-medium focus:outline-none"
            style={{ color: theme.ink }}
          />
          {loading ? (
            <Loader2
              className="w-4 h-4 animate-spin shrink-0"
              style={{ color: theme.accent }}
            />
          ) : null}
          {query ? (
            <button
              type="button"
              onClick={() => setQuery("")}
              aria-label="Clear search"
              className="p-1 rounded-full hover:opacity-75 cursor-pointer"
              style={{ color: theme.muted }}
            >
              <X className="w-4 h-4" />
            </button>
          ) : (
            <kbd
              className="hidden sm:inline-block px-2 py-0.5 rounded-md border text-[10px] font-bold"
              style={{
                backgroundColor: theme.surfaceAlt,
                borderColor: theme.border,
                color: theme.muted,
              }}
            >
              ESC
            </kbd>
          )}
        </div>

        {/* Results List */}
        <div className="overflow-y-auto p-2.5 space-y-1">
          {rows.map((row, idx) => {
            const active = idx === activeIndex;
            const prevGroup = idx > 0 ? rows[idx - 1].group : "";
            const showGroup = row.group !== prevGroup;

            return (
              <React.Fragment key={row.id}>
                {showGroup && (
                  <p
                    className="px-3 pt-2 pb-1 text-[10px] font-extrabold uppercase tracking-wider"
                    style={{ color: theme.muted }}
                  >
                    {row.group}
                  </p>
                )}
                <button
                  type="button"
                  onMouseEnter={() => setActiveIndex(idx)}
                  onClick={row.onSelect}
                  className="w-full px-3 py-2 rounded-2xl flex items-center gap-3 text-left transition cursor-pointer"
                  style={{
                    backgroundColor: active
                      ? theme.surfaceAlt
                      : "transparent",
                  }}
                >
                  {row.kind === "book" && row.book ? (
                    <BookCover
                      book={row.book}
                      theme={theme}
                      compact
                      className="w-8 h-12 shrink-0"
                    />
                  ) : row.kind === "author" && row.author ? (
                    <AuthorAvatar
                      name={row.author.name}
                      size={32}
                      theme={theme}
                    />
                  ) : row.kind === "category" ? (
                    <span
                      className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0"
                      style={{ backgroundColor: theme.surfaceAlt }}
                    >
                      <CategoryIcon
                        name={row.label}
                        size={18}
                        accentColor={theme.accent}
                      />
                    </span>
                  ) : (
                    <span
                      className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0"
                      style={{
                        backgroundColor: theme.accentSoft,
                        color: theme.accent,
                      }}
                    >
                      {row.id === "act-explore" ? (
                        <Compass className="w-4 h-4" />
                      ) : row.id === "act-shelf" ? (
                        <Library className="w-4 h-4" />
                      ) : row.id === "act-stats" ? (
                        <BarChart3 className="w-4 h-4" />
                      ) : row.id === "act-mode" ? (
                        themeMode === "light" ? (
                          <Moon className="w-4 h-4" />
                        ) : (
                          <Sun className="w-4 h-4" />
                        )
                      ) : row.id === "act-preset" ? (
                        <Palette className="w-4 h-4" />
                      ) : row.id === "act-apk" ? (
                        <Download className="w-4 h-4" />
                      ) : (
                        <Sparkles className="w-4 h-4" />
                      )}
                    </span>
                  )}

                  <div className="min-w-0 flex-1">
                    <p className="text-xs sm:text-sm font-bold truncate">
                      {row.label}
                    </p>
                    {row.subtitle ? (
                      <p
                        className="text-[11px] truncate"
                        style={{ color: theme.muted }}
                      >
                        {row.subtitle}
                      </p>
                    ) : null}
                  </div>

                  {row.kind === "book" && (
                    <BookOpen
                      className="w-3.5 h-3.5 shrink-0"
                      style={{ color: theme.accent }}
                    />
                  )}
                </button>
              </React.Fragment>
            );
          })}
        </div>

        {/* Footer Hints */}
        <div
          className="px-4 py-2 border-t flex items-center justify-between text-[11px]"
          style={{
            backgroundColor: theme.surfaceAlt,
            borderColor: theme.border,
            color: theme.muted,
          }}
        >
          <span>↑↓ to navigate · Enter to open</span>
          <span>
            {books.length > 0
              ? `${books.length.toLocaleString()} indexed titles`
              : "Loading catalog…"}
          </span>
        </div>
      </div>
    </div>
  );
}
