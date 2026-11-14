"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  BookOpen,
  Building2,
  ExternalLink,
  Filter,
  FolderTree,
  Github,
  HardDrive,
  Menu,
  RotateCcw,
  Search,
  Users,
  X,
} from "lucide-react";
import {
  BookRecord,
  cleanCategoryLabel,
  formatBytes,
  getDriveFolderUrl,
  TaxonomyData,
} from "@/types/library";
import { FolderTreeSidebar } from "./FolderTreeSidebar";
import { FolderBrowserGrid } from "./FolderBrowserGrid";
import { BookCard } from "./BookCard";
import { PreviewModal } from "./PreviewModal";

const PAGE_SIZE = 60;

type SortMode = "title" | "size_desc" | "size_asc" | "category";

export function LibraryExplorer() {
  const [books, setBooks] = useState<BookRecord[]>([]);
  const [taxonomy, setTaxonomy] = useState<TaxonomyData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [activePath, setActivePath] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedTopCategory, setSelectedTopCategory] = useState<string>("");
  const [selectedLeafPath, setSelectedLeafPath] = useState<string>("");
  const [selectedAuthor, setSelectedAuthor] = useState<string>("");
  const [selectedPublication, setSelectedPublication] = useState<string>("");
  const [sortMode, setSortMode] = useState<SortMode>("title");
  const [page, setPage] = useState<number>(1);
  const [previewBook, setPreviewBook] = useState<BookRecord | null>(null);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState<boolean>(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [booksRes, taxRes] = await Promise.all([
          fetch("/books.json"),
          fetch("/taxonomy.json"),
        ]);
        if (!booksRes.ok || !taxRes.ok) {
          throw new Error("Failed to load library catalog JSON files.");
        }
        const [booksData, taxData] = await Promise.all([
          booksRes.json() as Promise<BookRecord[]>,
          taxRes.json() as Promise<TaxonomyData>,
        ]);
        if (!cancelled) {
          setBooks(booksData);
          setTaxonomy(taxData);
          setLoading(false);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load catalog");
          setLoading(false);
        }
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  // Precompute stats & hierarchical folder counts
  const {
    totalSize,
    pathCounts,
    pathSizes,
    subfoldersByLeaf,
    topCategories,
    leafOptions,
    authorOptions,
    publicationOptions,
  } = useMemo(() => {
    let sizeSum = 0;
    const pCounts: Record<string, number> = {};
    const pSizes: Record<string, number> = {};
    const subMap: Record<string, Record<string, { count: number; size: number }>> = {};
    const authors: Record<string, number> = {};
    const pubs: Record<string, number> = {};
    const leafMap: Record<string, { leaf_path: string; label: string; count: number }> = {};

    for (const b of books) {
      const sz = b.size || 0;
      sizeSum += sz;

      // Top category
      pCounts[b.top_category] = (pCounts[b.top_category] || 0) + 1;
      pSizes[b.top_category] = (pSizes[b.top_category] || 0) + sz;

      // Intermediate path (e.g. 01_Religion_ধর্ম/Islam_ইসলাম)
      const parts = b.leaf_path.split("/");
      if (parts.length === 3) {
        const midPath = `${parts[0]}/${parts[1]}`;
        pCounts[midPath] = (pCounts[midPath] || 0) + 1;
        pSizes[midPath] = (pSizes[midPath] || 0) + sz;
      }

      // Leaf path
      pCounts[b.leaf_path] = (pCounts[b.leaf_path] || 0) + 1;
      pSizes[b.leaf_path] = (pSizes[b.leaf_path] || 0) + sz;

      if (!leafMap[b.leaf_path]) {
        leafMap[b.leaf_path] = {
          leaf_path: b.leaf_path,
          label: cleanCategoryLabel(b.leaf_category),
          count: 0,
        };
      }
      leafMap[b.leaf_path].count += 1;

      if (b.subfolder) {
        const fullSub = `${b.leaf_path}/${b.subfolder}`;
        pCounts[fullSub] = (pCounts[fullSub] || 0) + 1;
        pSizes[fullSub] = (pSizes[fullSub] || 0) + sz;
        if (!subMap[b.leaf_path]) subMap[b.leaf_path] = {};
        if (!subMap[b.leaf_path][b.subfolder]) {
          subMap[b.leaf_path][b.subfolder] = { count: 0, size: 0 };
        }
        subMap[b.leaf_path][b.subfolder].count += 1;
        subMap[b.leaf_path][b.subfolder].size += sz;
      }

      if (b.author) authors[b.author] = (authors[b.author] || 0) + 1;
      if (b.publication) pubs[b.publication] = (pubs[b.publication] || 0) + 1;
    }

    const sortedSubsByLeaf: Record<string, { name: string; count: number; size: number }[]> = {};
    for (const [lp, map] of Object.entries(subMap)) {
      sortedSubsByLeaf[lp] = Object.entries(map)
        .map(([name, val]) => ({ name, count: val.count, size: val.size }))
        .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
    }

    const tCats = taxonomy ? Object.keys(taxonomy.tree) : Object.keys(pCounts).filter((k) => !k.includes("/")).sort();
    const lOpts = Object.values(leafMap).sort((a, b) => a.leaf_path.localeCompare(b.leaf_path));
    const aOpts = Object.entries(authors)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));
    const pubOpts = Object.entries(pubs)
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name));

    return {
      totalSize: sizeSum,
      pathCounts: pCounts,
      pathSizes: pSizes,
      subfoldersByLeaf: sortedSubsByLeaf,
      topCategories: tCats,
      leafOptions: lOpts,
      authorOptions: aOpts,
      publicationOptions: pubOpts,
    };
  }, [books, taxonomy]);

  const filteredLeafOptions = useMemo(() => {
    if (!selectedTopCategory) return leafOptions;
    return leafOptions.filter((l) => l.leaf_path.startsWith(`${selectedTopCategory}/`));
  }, [leafOptions, selectedTopCategory]);

  // Reset page when filters change
  useEffect(() => {
    setPage(1);
  }, [
    activePath,
    searchQuery,
    selectedTopCategory,
    selectedLeafPath,
    selectedAuthor,
    selectedPublication,
    sortMode,
  ]);

  const filteredBooks = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    const result = books.filter((b) => {
      if (activePath) {
        const bookFullPath = b.subfolder ? `${b.leaf_path}/${b.subfolder}` : b.leaf_path;
        const matchesPath =
          b.top_category === activePath ||
          b.leaf_path === activePath ||
          b.leaf_path.startsWith(`${activePath}/`) ||
          bookFullPath === activePath;
        if (!matchesPath) return false;
      }
      if (selectedTopCategory && b.top_category !== selectedTopCategory) return false;
      if (selectedLeafPath && b.leaf_path !== selectedLeafPath) return false;
      if (selectedAuthor && b.author !== selectedAuthor) return false;
      if (selectedPublication && b.publication !== selectedPublication) return false;

      if (q) {
        const hay = `${b.name} ${b.author} ${b.publication} ${b.leaf_path} ${b.subfolder || ""}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });

    result.sort((a, b) => {
      if (sortMode === "size_desc") return (b.size || 0) - (a.size || 0);
      if (sortMode === "size_asc") return (a.size || 0) - (b.size || 0);
      if (sortMode === "category") {
        return a.leaf_path.localeCompare(b.leaf_path) || a.name.localeCompare(b.name);
      }
      return a.name.localeCompare(b.name);
    });

    return result;
  }, [
    books,
    activePath,
    searchQuery,
    selectedTopCategory,
    selectedLeafPath,
    selectedAuthor,
    selectedPublication,
    sortMode,
  ]);

  const totalPages = Math.max(1, Math.ceil(filteredBooks.length / PAGE_SIZE));
  const currentPage = Math.min(page, totalPages);
  const pageItems = filteredBooks.slice((currentPage - 1) * PAGE_SIZE, currentPage * PAGE_SIZE);

  const handleResetFilters = () => {
    setActivePath("");
    setSearchQuery("");
    setSelectedTopCategory("");
    setSelectedLeafPath("");
    setSelectedAuthor("");
    setSelectedPublication("");
    setSortMode("title");
    setPage(1);
  };

  const hasActiveFilters =
    !!activePath ||
    !!searchQuery ||
    !!selectedTopCategory ||
    !!selectedLeafPath ||
    !!selectedAuthor ||
    !!selectedPublication;

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 p-6 text-center">
        <div className="w-12 h-12 rounded-full border-4 border-emerald-500/30 border-t-emerald-400 animate-spin" />
        <div>
          <h1 className="text-lg font-bold text-white">Loading Bangladesh&apos;s Biggest E-Book Library...</h1>
          <p className="text-sm text-slate-400 mt-1">Indexing thousands of Bangla, NCTB, Islamic, Academic &amp; World e-books</p>
        </div>
      </div>
    );
  }

  if (error || !taxonomy) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-3 p-6 text-center">
        <p className="text-rose-400 font-semibold">{error || "Unable to load catalog."}</p>
        <button
          type="button"
          onClick={() => window.location.reload()}
          className="px-4 py-2 rounded-lg bg-emerald-600 text-white text-sm font-semibold"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header Banner */}
      <header className="bg-gradient-to-br from-emerald-950/80 via-slate-900 to-slate-950 border-b border-slate-800">
        <div className="max-w-[1480px] mx-auto px-4 sm:px-6 py-6">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs font-semibold mb-2">
                <BookOpen className="w-3.5 h-3.5" />
                বাংলাদেশের বৃহত্তম ই-বুক লাইব্রেরি • 25 Clean Categories
              </div>
              <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-white">
                Bangladesh&apos;s Biggest E-Book Library
              </h1>
              <p className="text-sm text-slate-300 mt-1 max-w-3xl">
                Explore, preview, and download thousands of Bangla &amp; English PDF/EPUB books, NCTB textbooks (Class 1–12), Islamic classics, literature, science, engineering, and competitive exam resources directly from Google Drive.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2.5 shrink-0">
              <a
                href={getDriveFolderUrl(taxonomy.root_drive_id)}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs sm:text-sm font-semibold shadow-lg shadow-emerald-950/50 transition"
              >
                <HardDrive className="w-4 h-4" />
                Google Drive Root
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
              <a
                href="https://github.com/salman-anik/Bangladesh-Biggest-eBook-Library"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-100 text-xs sm:text-sm font-semibold border border-slate-700 transition"
              >
                <Github className="w-4 h-4" />
                GitHub Repository
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          </div>

          {/* Live Library Stats Pills */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5 mt-5">
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl px-3.5 py-2.5 flex items-center gap-2.5">
              <BookOpen className="w-4 h-4 text-emerald-400 shrink-0" />
              <div>
                <div className="text-base font-bold text-white leading-tight">{books.length.toLocaleString()}</div>
                <div className="text-[11px] text-slate-400">Total Books</div>
              </div>
            </div>
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl px-3.5 py-2.5 flex items-center gap-2.5">
              <HardDrive className="w-4 h-4 text-sky-400 shrink-0" />
              <div>
                <div className="text-base font-bold text-white leading-tight">{formatBytes(totalSize)}</div>
                <div className="text-[11px] text-slate-400">Total Archive</div>
              </div>
            </div>
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl px-3.5 py-2.5 flex items-center gap-2.5">
              <FolderTree className="w-4 h-4 text-amber-400 shrink-0" />
              <div>
                <div className="text-base font-bold text-white leading-tight">{topCategories.length}</div>
                <div className="text-[11px] text-slate-400">Main Categories</div>
              </div>
            </div>
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl px-3.5 py-2.5 flex items-center gap-2.5">
              <Users className="w-4 h-4 text-rose-400 shrink-0" />
              <div>
                <div className="text-base font-bold text-white leading-tight">{authorOptions.length.toLocaleString()}</div>
                <div className="text-[11px] text-slate-400">Authors</div>
              </div>
            </div>
            <div className="bg-slate-900/70 border border-slate-800 rounded-xl px-3.5 py-2.5 flex items-center gap-2.5 col-span-2 sm:col-span-1">
              <Building2 className="w-4 h-4 text-purple-400 shrink-0" />
              <div>
                <div className="text-base font-bold text-white leading-tight">{publicationOptions.length.toLocaleString()}</div>
                <div className="text-[11px] text-slate-400">Publications</div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Layout */}
      <div className="max-w-[1480px] w-full mx-auto px-4 sm:px-6 py-5 flex-1 flex flex-col lg:flex-row gap-5">
        {/* Mobile Sidebar Toggle */}
        <div className="lg:hidden flex items-center justify-between bg-slate-900 border border-slate-800 rounded-xl p-3">
          <span className="text-xs font-semibold text-slate-300 flex items-center gap-2">
            <FolderTree className="w-4 h-4 text-emerald-400" />
            Category Explorer
          </span>
          <button
            type="button"
            onClick={() => setMobileSidebarOpen((v) => !v)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 text-xs font-medium text-white border border-slate-700"
          >
            {mobileSidebarOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
            {mobileSidebarOpen ? "Hide Tree" : "Browse Folders"}
          </button>
        </div>

        {/* Left Sidebar Tree */}
        <div className={`${mobileSidebarOpen ? "block" : "hidden"} lg:block lg:w-80 shrink-0`}>
          <FolderTreeSidebar
            taxonomy={taxonomy}
            activePath={activePath}
            onSelectPath={(p) => {
              setActivePath(p);
              setSelectedTopCategory("");
              setSelectedLeafPath("");
            }}
            pathCounts={pathCounts}
            subfoldersByLeaf={subfoldersByLeaf}
          />
        </div>

        {/* Right Main Browser & Results */}
        <main className="flex-1 min-w-0 space-y-4">
          {/* Interactive Folder Grid & Breadcrumbs */}
          <FolderBrowserGrid
            taxonomy={taxonomy}
            activePath={activePath}
            onSelectPath={(p) => {
              setActivePath(p);
              setSelectedTopCategory("");
              setSelectedLeafPath("");
            }}
            pathCounts={pathCounts}
            pathSizes={pathSizes}
            subfoldersByLeaf={subfoldersByLeaf}
          />

          {/* Search & Multi-Faceted Filter Bar */}
          <section className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 space-y-3">
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="search"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="বই, লেখক, প্রকাশনী বা বিষয় লিখুন... (Search title, author, publication, NCTB, category)"
                  className="w-full bg-slate-950 border border-slate-800 focus:border-emerald-500 rounded-xl pl-10 pr-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 outline-none transition"
                />
              </div>

              {hasActiveFilters && (
                <button
                  type="button"
                  onClick={handleResetFilters}
                  className="inline-flex items-center justify-center gap-1.5 px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 transition shrink-0 cursor-pointer"
                >
                  <RotateCcw className="w-3.5 h-3.5 text-amber-400" />
                  Reset Filters
                </button>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-2.5">
              {/* Top Category */}
              <select
                value={selectedTopCategory}
                onChange={(e) => {
                  setSelectedTopCategory(e.target.value);
                  setSelectedLeafPath("");
                }}
                aria-label="Filter by top category"
                className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 outline-none focus:border-emerald-500"
              >
                <option value="">All 25 Categories ({books.length.toLocaleString()})</option>
                {topCategories.map((tc) => (
                  <option key={tc} value={tc}>
                    {cleanCategoryLabel(tc)} ({(pathCounts[tc] || 0).toLocaleString()})
                  </option>
                ))}
              </select>

              {/* Subcategory */}
              <select
                value={selectedLeafPath}
                onChange={(e) => setSelectedLeafPath(e.target.value)}
                aria-label="Filter by subcategory"
                className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 outline-none focus:border-emerald-500"
              >
                <option value="">All Subcategories</option>
                {filteredLeafOptions.map((lf) => (
                  <option key={lf.leaf_path} value={lf.leaf_path}>
                    {lf.label} ({lf.count.toLocaleString()})
                  </option>
                ))}
              </select>

              {/* Author */}
              <select
                value={selectedAuthor}
                onChange={(e) => setSelectedAuthor(e.target.value)}
                aria-label="Filter by author"
                className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 outline-none focus:border-emerald-500"
              >
                <option value="">All Authors ({authorOptions.length.toLocaleString()})</option>
                {authorOptions.map((a) => (
                  <option key={a.name} value={a.name}>
                    {a.name} ({a.count.toLocaleString()})
                  </option>
                ))}
              </select>

              {/* Publication */}
              <select
                value={selectedPublication}
                onChange={(e) => setSelectedPublication(e.target.value)}
                aria-label="Filter by publication"
                className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 outline-none focus:border-emerald-500"
              >
                <option value="">All Publications ({publicationOptions.length.toLocaleString()})</option>
                {publicationOptions.map((p) => (
                  <option key={p.name} value={p.name}>
                    {p.name} ({p.count.toLocaleString()})
                  </option>
                ))}
              </select>

              {/* Sort */}
              <select
                value={sortMode}
                onChange={(e) => setSortMode(e.target.value as SortMode)}
                aria-label="Sort books"
                className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 outline-none focus:border-emerald-500"
              >
                <option value="title">Sort: Title (A–Z)</option>
                <option value="size_desc">Sort: Size (Largest First)</option>
                <option value="size_asc">Sort: Size (Smallest First)</option>
                <option value="category">Sort: Category</option>
              </select>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-400 pt-1">
              <div className="flex items-center gap-1.5">
                <Filter className="w-3.5 h-3.5 text-emerald-400" />
                Showing <span className="font-bold text-slate-100">{filteredBooks.length.toLocaleString()}</span> matching books
                {totalPages > 1 && (
                  <span>
                    • Page {currentPage} of {totalPages}
                  </span>
                )}
              </div>
              {selectedAuthor && (
                <button
                  type="button"
                  onClick={() => setSelectedAuthor("")}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-amber-500/15 text-amber-300 border border-amber-500/30"
                >
                  Author: {selectedAuthor} <X className="w-3 h-3" />
                </button>
              )}
              {selectedPublication && (
                <button
                  type="button"
                  onClick={() => setSelectedPublication("")}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-purple-500/15 text-purple-300 border border-purple-500/30"
                >
                  Publication: {selectedPublication} <X className="w-3 h-3" />
                </button>
              )}
            </div>
          </section>

          {/* Books Grid */}
          {pageItems.length === 0 ? (
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-10 text-center space-y-2">
              <p className="text-slate-300 font-semibold">No books match your active search/filter criteria.</p>
              <button
                type="button"
                onClick={handleResetFilters}
                className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold cursor-pointer"
              >
                Show All Books
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
              {pageItems.map((book) => (
                <BookCard
                  key={book.file_id}
                  book={book}
                  onPreview={setPreviewBook}
                  onFilterAuthor={(author) => setSelectedAuthor(author)}
                  onFilterPublication={(pub) => setSelectedPublication(pub)}
                  onNavigatePath={(path) => {
                    setActivePath(path);
                    setSelectedTopCategory("");
                    setSelectedLeafPath("");
                  }}
                />
              ))}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex flex-wrap items-center justify-center gap-2 pt-2 pb-6">
              <button
                type="button"
                disabled={currentPage <= 1}
                onClick={() => setPage(1)}
                className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-semibold text-slate-300 disabled:opacity-40 hover:bg-slate-800 cursor-pointer"
              >
                First
              </button>
              <button
                type="button"
                disabled={currentPage <= 1}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-semibold text-slate-300 disabled:opacity-40 hover:bg-slate-800 cursor-pointer"
              >
                Previous
              </button>
              <span className="px-3 py-1.5 text-xs text-slate-400 font-medium">
                Page <strong className="text-white">{currentPage}</strong> / {totalPages}
              </span>
              <button
                type="button"
                disabled={currentPage >= totalPages}
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-semibold text-slate-300 disabled:opacity-40 hover:bg-slate-800 cursor-pointer"
              >
                Next
              </button>
              <button
                type="button"
                disabled={currentPage >= totalPages}
                onClick={() => setPage(totalPages)}
                className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-semibold text-slate-300 disabled:opacity-40 hover:bg-slate-800 cursor-pointer"
              >
                Last
              </button>
            </div>
          )}
        </main>
      </div>

      <PreviewModal book={previewBook} onClose={() => setPreviewBook(null)} />
    </div>
  );
}
