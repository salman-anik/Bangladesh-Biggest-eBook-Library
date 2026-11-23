"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  Bookmark,
  BookOpen,
  Download,
  ExternalLink,
  HardDrive,
  Loader2,
  Search,
  Sparkles,
  X,
} from "lucide-react";
import {
  BookItem,
  CompactCatalog,
  formatBytes,
  getCoverUrl,
  getDownloadUrl,
  getDriveFolderUrl,
  getPreviewUrl,
  inflateCatalog,
  LibrarySummary,
} from "@/types/library";

const PAGE_SIZE = 48;
const SAVED_KEY = "anabook_saved_v1";

const CLASS_CHIPS = [
  "Pre-Primary",
  "Class 1",
  "Class 2",
  "Class 3",
  "Class 4",
  "Class 5",
  "Class 6",
  "Class 7",
  "Class 8",
  "Class 9",
  "Class 10",
  "Class 12",
];

function CoverThumb({ book }: { book: BookItem }) {
  const [stage, setStage] = useState<"primary" | "fallback" | "none">(
    getCoverUrl(book, false) ? "primary" : "none"
  );

  const src =
    stage === "primary"
      ? getCoverUrl(book, false)
      : stage === "fallback"
      ? getCoverUrl(book, true)
      : "";

  if (!src) {
    return (
      <div className="w-full h-full bg-[#F5F6F8] p-3 flex flex-col justify-between text-left">
        <span className="text-[10px] font-bold uppercase tracking-wider text-[#5F6672] line-clamp-1">
          {(book.sub || book.cat).split("/").pop()}
        </span>
        <span className="text-xs font-extrabold text-[#0F1115] line-clamp-4 leading-snug">
          {book.title}
        </span>
        <span className="text-[10px] text-[#5F6672] line-clamp-1 border-t border-neutral-200 pt-1.5">
          {book.author}
        </span>
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={book.title}
      loading="lazy"
      className="w-full h-full object-cover"
      onError={() => setStage((s) => (s === "primary" ? "fallback" : "none"))}
    />
  );
}

export function LibraryExplorer() {
  const [books, setBooks] = useState<BookItem[]>([]);
  const [summary, setSummary] = useState<LibrarySummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [query, setQuery] = useState("");
  const [selectedCat, setSelectedCat] = useState("ALL");
  const [selectedClass, setSelectedClass] = useState("");
  const [selectedFmt, setSelectedFmt] = useState("ALL");
  const [sortMode, setSortMode] = useState<"covers" | "title" | "size">("covers");
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);
  const [savedIds, setSavedIds] = useState<string[]>([]);
  const [previewBook, setPreviewBook] = useState<BookItem | null>(null);

  useEffect(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      const q = params.get("q");
      const cat = params.get("cat") || params.get("category");
      if (q) setQuery(q);
      if (cat) setSelectedCat(cat);
      const stored = JSON.parse(localStorage.getItem(SAVED_KEY) || "[]");
      if (Array.isArray(stored)) setSavedIds(stored);
    } catch {
      // Ignore URL/storage error
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetch("/books.json")
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<CompactCatalog>;
      })
      .then((raw) => {
        if (cancelled) return;
        const { books: inflated, summary: meta } = inflateCatalog(raw);
        setBooks(inflated);
        setSummary(meta);
        setLoading(false);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load catalog");
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const savedSet = useMemo(() => new Set(savedIds), [savedIds]);

  const toggleSave = (id: string) => {
    setSavedIds((prev) => {
      const next = prev.includes(id) ? prev.filter((x) => x !== id) : [id, ...prev];
      try {
        localStorage.setItem(SAVED_KEY, JSON.stringify(next));
      } catch {
        // Ignore
      }
      return next;
    });
  };

  const filtered = useMemo(() => {
    const terms = query.trim().toLowerCase().split(/\s+/).filter(Boolean);
    const list = books.filter((b) => {
      if (selectedCat === "SAVED" && !savedSet.has(b.id)) return false;
      if (selectedCat !== "ALL" && selectedCat !== "SAVED" && b.cat !== selectedCat) return false;
      if (selectedClass) {
        const leaf = (b.sub || "").split("/").pop()?.toLowerCase() || "";
        if (leaf !== selectedClass.toLowerCase()) return false;
      }
      if (selectedFmt !== "ALL" && b.fmt !== selectedFmt) return false;
      for (const t of terms) {
        if (!b.searchBlob.includes(t)) return false;
      }
      return true;
    });

    if (sortMode === "covers") {
      list.sort((a, b) => Number(Boolean(b.coverId)) - Number(Boolean(a.coverId)) || a.title.localeCompare(b.title));
    } else if (sortMode === "size") {
      list.sort((a, b) => b.size - a.size);
    } else {
      list.sort((a, b) => a.title.localeCompare(b.title));
    }
    return list;
  }, [books, query, selectedCat, selectedClass, selectedFmt, sortMode, savedSet]);

  useEffect(() => {
    setVisibleCount(PAGE_SIZE);
  }, [query, selectedCat, selectedClass, selectedFmt, sortMode]);

  const shown = filtered.slice(0, visibleCount);

  const surpriseBook = () => {
    const pool = filtered.filter((b) => Boolean(b.coverId));
    const list = pool.length ? pool : filtered;
    if (!list.length) return;
    setPreviewBook(list[Math.floor(Math.random() * list.length)]);
  };

  if (loading) {
    return (
      <div className="min-h-[70vh] flex flex-col items-center justify-center gap-3 text-[#5F6672] bg-white">
        <Loader2 className="w-8 h-8 animate-spin text-[#0F1115]" />
        <p className="text-sm font-semibold">Loading AnaBook Online Library…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-xl mx-auto px-4 py-20 text-center space-y-3">
        <p className="text-lg font-bold text-[#0F1115]">Unable to load catalog</p>
        <p className="text-sm text-[#5F6672]">{error}</p>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-5 sm:px-8 py-8 space-y-6 bg-white">
      {/* Search + Filters Panel */}
      <div className="rounded-3xl bg-[#F5F6F8] p-5 space-y-4">
        <div className="flex flex-col md:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-[#5F6672] absolute left-4 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search 22,166+ Bangla & English books, authors, Class 1–12…"
              className="w-full pl-11 pr-9 py-3 rounded-full bg-white border border-neutral-200 text-sm text-[#0F1115] placeholder:text-[#5F6672] focus:outline-none focus:border-[#0F1115]"
            />
            {query ? (
              <button
                type="button"
                onClick={() => setQuery("")}
                className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[#5F6672] hover:text-[#0F1115]"
              >
                <X className="w-4 h-4" />
              </button>
            ) : null}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <select
              value={selectedFmt}
              onChange={(e) => setSelectedFmt(e.target.value)}
              className="px-3.5 py-2.5 rounded-full bg-white border border-neutral-200 text-xs font-bold text-[#0F1115] focus:outline-none"
            >
              <option value="ALL">All Formats</option>
              <option value="PDF">PDF</option>
              <option value="EPUB">EPUB</option>
              <option value="MOBI">MOBI</option>
              <option value="DOCX">DOCX</option>
            </select>

            <select
              value={sortMode}
              onChange={(e) => setSortMode(e.target.value as "covers" | "title" | "size")}
              className="px-3.5 py-2.5 rounded-full bg-white border border-neutral-200 text-xs font-bold text-[#0F1115] focus:outline-none"
            >
              <option value="covers">Covers First</option>
              <option value="title">Title A–Z</option>
              <option value="size">Largest First</option>
            </select>

            <button
              type="button"
              onClick={surpriseBook}
              className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-full bg-[#0F1115] hover:bg-neutral-800 text-white text-xs font-bold transition"
            >
              <Sparkles className="w-3.5 h-3.5 text-[#C6F353]" />
              Surprise Me
            </button>

            <a
              href={getDriveFolderUrl("1fMsplDtUnpUhnNBJGKvYQ1sdZx0QVJWq")}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-full bg-white border border-neutral-200 hover:border-[#0F1115] text-xs font-bold text-[#0F1115] transition"
            >
              <HardDrive className="w-3.5 h-3.5" />
              Drive
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        </div>

        {/* Category Pills */}
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => {
              setSelectedCat("ALL");
              setSelectedClass("");
            }}
            className={`px-3.5 py-1.5 rounded-full text-xs font-bold border transition ${
              selectedCat === "ALL"
                ? "bg-[#0F1115] text-white border-[#0F1115]"
                : "bg-white text-[#0F1115] border-neutral-200 hover:border-[#0F1115]"
            }`}
          >
            All ({books.length.toLocaleString()})
          </button>

          <button
            type="button"
            onClick={() => {
              setSelectedCat("SAVED");
              setSelectedClass("");
            }}
            className={`inline-flex items-center gap-1 px-3.5 py-1.5 rounded-full text-xs font-bold border transition ${
              selectedCat === "SAVED"
                ? "bg-[#C6F353] text-[#0F1115] border-[#0F1115]"
                : "bg-white text-[#0F1115] border-neutral-200 hover:border-[#0F1115]"
            }`}
          >
            <Bookmark className="w-3.5 h-3.5" />
            Saved ({savedIds.length})
          </button>

          {(summary?.cats || []).map((c) => {
            const active = selectedCat === c;
            return (
              <button
                key={c}
                type="button"
                onClick={() => {
                  setSelectedCat(c);
                  if (c !== "Education & Textbooks") setSelectedClass("");
                }}
                className={`px-3.5 py-1.5 rounded-full text-xs font-bold border transition ${
                  active
                    ? "bg-[#0F1115] text-[#C6F353] border-[#0F1115]"
                    : "bg-white text-[#5F6672] border-neutral-200 hover:text-[#0F1115]"
                }`}
              >
                {c}
              </button>
            );
          })}
        </div>

        {/* 1-Tap Class 1-12 Chips */}
        {selectedCat === "Education & Textbooks" ? (
          <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-neutral-200">
            <button
              type="button"
              onClick={() => setSelectedClass("")}
              className={`px-3 py-1 rounded-full text-[11px] font-bold border transition ${
                !selectedClass
                  ? "bg-[#0F1115] text-white border-[#0F1115]"
                  : "bg-white text-[#5F6672] border-neutral-200"
              }`}
            >
              All Education
            </button>
            {CLASS_CHIPS.map((cls) => (
              <button
                key={cls}
                type="button"
                onClick={() => setSelectedClass(selectedClass === cls ? "" : cls)}
                className={`px-3 py-1 rounded-full text-[11px] font-bold border transition ${
                  selectedClass === cls
                    ? "bg-[#C6F353] text-[#0F1115] border-[#0F1115]"
                    : "bg-white text-[#0F1115] border-neutral-200 hover:border-[#0F1115]"
                }`}
              >
                {cls}
              </button>
            ))}
          </div>
        ) : null}
      </div>

      {/* Results Count */}
      <div className="flex items-center justify-between text-xs text-[#5F6672] px-1">
        <span>
          Showing <strong className="text-[#0F1115]">{shown.length.toLocaleString()}</strong> of{" "}
          <strong className="text-[#0F1115]">{filtered.length.toLocaleString()}</strong> books
        </span>
        {summary ? <span>Archive: {formatBytes(summary.totalBytes)}</span> : null}
      </div>

      {/* Book Grid */}
      {shown.length === 0 ? (
        <div className="rounded-3xl bg-[#F5F6F8] py-16 text-center space-y-2">
          <p className="text-base font-bold text-[#0F1115]">No matching books found</p>
          <p className="text-xs text-[#5F6672]">Try clearing a filter or searching another keyword.</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {shown.map((book) => {
            const isSaved = savedSet.has(book.id);
            return (
              <div
                key={book.id}
                className="group rounded-2xl bg-white border border-neutral-200 hover:border-[#0F1115] overflow-hidden flex flex-col transition shadow-xs"
              >
                <button
                  type="button"
                  onClick={() => setPreviewBook(book)}
                  className="aspect-[2/3] w-full bg-[#F5F6F8] overflow-hidden relative"
                >
                  <CoverThumb book={book} />
                  <span className="absolute top-2 left-2 px-2 py-0.5 rounded-full bg-[#0F1115]/85 text-[10px] font-bold text-white">
                    {book.fmt}
                  </span>
                </button>

                <div className="p-3 flex-1 flex flex-col justify-between gap-2">
                  <div>
                    <h3
                      className="text-xs font-extrabold text-[#0F1115] line-clamp-2 leading-snug"
                      title={book.title}
                    >
                      {book.title}
                    </h3>
                    <p className="text-[11px] text-[#5F6672] line-clamp-1 mt-0.5">{book.author}</p>
                  </div>

                  <div className="flex items-center gap-1.5 pt-1">
                    <button
                      type="button"
                      onClick={() => setPreviewBook(book)}
                      className="flex-1 inline-flex items-center justify-center gap-1 py-1.5 rounded-full bg-[#0F1115] hover:bg-neutral-800 text-white text-[11px] font-bold transition"
                    >
                      <BookOpen className="w-3.5 h-3.5 text-[#C6F353]" />
                      Read
                    </button>

                    <a
                      href={getDownloadUrl(book.id)}
                      target="_blank"
                      rel="noopener noreferrer"
                      title={`Download (${formatBytes(book.size)})`}
                      className="w-7 h-7 rounded-full bg-[#F5F6F8] hover:bg-[#C6F353] text-[#0F1115] flex items-center justify-center transition"
                    >
                      <Download className="w-3.5 h-3.5" />
                    </a>

                    <button
                      type="button"
                      onClick={() => toggleSave(book.id)}
                      title={isSaved ? "Remove bookmark" : "Bookmark"}
                      className={`w-7 h-7 rounded-full flex items-center justify-center transition ${
                        isSaved
                          ? "bg-[#C6F353] text-[#0F1115]"
                          : "bg-[#F5F6F8] text-[#5F6672] hover:text-[#0F1115]"
                      }`}
                    >
                      <Bookmark className="w-3.5 h-3.5" fill={isSaved ? "currentColor" : "none"} />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Load More */}
      {visibleCount < filtered.length ? (
        <div className="flex justify-center pt-4">
          <button
            type="button"
            onClick={() => setVisibleCount((c) => c + PAGE_SIZE)}
            className="px-6 py-3 rounded-full bg-[#0F1115] hover:bg-neutral-800 text-sm font-bold text-white transition"
          >
            Load More Books ({(filtered.length - visibleCount).toLocaleString()} remaining)
          </button>
        </div>
      ) : null}

      {/* In-Page Reader Preview Modal */}
      {previewBook ? (
        <div
          className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-3 sm:p-6"
          onClick={() => setPreviewBook(null)}
        >
          <div
            className="w-full max-w-5xl h-[88vh] rounded-3xl bg-white border border-neutral-200 overflow-hidden flex flex-col shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-5 py-3.5 border-b border-neutral-200 flex items-center justify-between gap-3 bg-white">
              <div className="min-w-0">
                <h3 className="text-sm font-extrabold text-[#0F1115] truncate">{previewBook.title}</h3>
                <p className="text-[11px] text-[#5F6672] truncate">
                  {previewBook.author} · {previewBook.fmt} · {formatBytes(previewBook.size)}
                </p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <a
                  href={getDownloadUrl(previewBook.id)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-[#0F1115] text-white text-xs font-bold"
                >
                  <Download className="w-3.5 h-3.5 text-[#C6F353]" />
                  Download
                </a>
                <button
                  type="button"
                  onClick={() => setPreviewBook(null)}
                  className="w-8 h-8 rounded-full bg-[#F5F6F8] text-[#0F1115] flex items-center justify-center"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            </div>
            <iframe
              src={getPreviewUrl(previewBook.id)}
              title={previewBook.title}
              className="flex-1 w-full bg-[#F5F6F8]"
              allow="autoplay"
            />
          </div>
        </div>
      ) : null}
    </div>
  );
}
