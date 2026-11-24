"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  ChevronDown,
  Download,
  Github,
  Globe,
  Layers,
  Lock,
  Mail,
  Moon,
  Search,
  ShieldCheck,
  Smartphone,
  Sparkles,
  Star,
  Sun,
  WifiOff,
  Zap,
} from "lucide-react";
import { useWebTheme } from "@/context/WebThemeContext";
import { THEME_PRESETS, ThemePresetKey } from "@/lib/anabookTheme";

const APK_URL =
  "https://github.com/salman-anik/AnaBook/releases/latest/download/AnaBook.apk";
const REPO_URL =
  "https://github.com/salman-anik/Bangladesh-Biggest-eBook-Library";

interface AppVersionInfo {
  latestVersion: string;
  releaseNotes?: string;
}

const THEMES: Record<
  ThemePresetKey,
  { name: string; darkBg: string; lightBg: string; accent: string }
> = {
  espresso: {
    name: "Espresso",
    darkBg: "#2D2826",
    lightBg: "#FAF6F3",
    accent: "#A86E56",
  },
  matcha: {
    name: "Matcha",
    darkBg: "#1E2B24",
    lightBg: "#F3F8F5",
    accent: "#4E8260",
  },
  midnight: {
    name: "Midnight",
    darkBg: "#1B2236",
    lightBg: "#F4F6FB",
    accent: "#4C6399",
  },
  sepia: {
    name: "Sepia",
    darkBg: "#2C2119",
    lightBg: "#FBF7EE",
    accent: "#A97434",
  },
  rosewood: {
    name: "Rosewood",
    darkBg: "#2A1F26",
    lightBg: "#FBF4F7",
    accent: "#A65A6D",
  },
};

const FEATURED_COVERS = [
  {
    id: "1FIcC7bE27-dPRVQo0pjbcstXIFw94OPd",
    title: "আলাতচক্র",
    author: "আহমদ ছফা",
  },
  {
    id: "1vDtlwfiNpS6R_yO6qQ4lQn2EzkQXucRn",
    title: "Dielectric Dilemma",
    author: "Robert S. Eisenberg",
  },
  {
    id: "12GJV1hO9GI_D8vqE9CwIdBehEbQNJGCO",
    title: "King of Sword and Sky",
    author: "C. L. Wilson",
  },
];

const FEATURED_AUTHORS = [
  { id: "1WEdNeNZtPRsmqlggkTwgLzLQsjNzM2yu", name: "হুমায়ূন আহমেদ" },
  { id: "1iK6EXNkCZBXEq4I0bA2mnztSnPZ9VOxo", name: "রবীন্দ্রনাথ ঠাকুর" },
  { id: "1j6QuVuqpZZvAVHD-ZHj9hGDI2FuPKTNo", name: "মুহম্মদ জাফর ইকবাল" },
  { id: "1qjca_bX_khgCNhdJL10HBbp14MLVBcIL", name: "কাজী নজরুল ইসলাম" },
];

const CATEGORY_ICONS = [
  { id: "1BelQZheZSHflNlIPXwRj36VhWbizvB5t", label: "Education" },
  { id: "1xJPt1BZHYma0HWQyLG4a4vxll6ek2LxV", label: "Bangla" },
  { id: "1pIqsYKnvGbPgO7UnVQ8ZSCMUsmG0RGBw", label: "Science" },
  { id: "1bQx_iNkOAT7g2X9lPXDFT7NHEvqUek9D", label: "Religion" },
];

const POPULAR_SERIES = [
  {
    title: "হিমু সিরিজ",
    author: "হুমায়ূন আহমেদ",
    query: "হিমু",
    tag: "Classic Fiction",
  },
  {
    title: "মিসির আলি সিরিজ",
    author: "হুমায়ূন আহমেদ",
    query: "মিসির আলি",
    tag: "Mystery",
  },
  {
    title: "ফেলুদা সিরিজ",
    author: "সত্যজিৎ রায়",
    query: "ফেলুদা",
    tag: "Detective",
  },
  {
    title: "প্রফেসর শঙ্কু",
    author: "সত্যজিৎ রায়",
    query: "শঙ্কু",
    tag: "Sci-Fi",
  },
  {
    title: "তিন গোয়েন্দা",
    author: "রকিব হাসান",
    query: "তিন গোয়েন্দা",
    tag: "Adventure",
  },
  {
    title: "কাকাবাবু সিরিজ",
    author: "সুনীল গঙ্গোপাধ্যায়",
    query: "কাকাবাবু",
    tag: "Thriller",
  },
];

const FAQ_ITEMS = [
  {
    q: "Is AnaBook free to use as an online eLibrary and PDF library?",
    a: "Yes. All 29,178+ Bangla & English books, NCTB Class 1–12 textbooks, and Series Collections are 100% free to browse, read directly in your browser, or download via Google Drive.",
  },
  {
    q: "Can I jump directly to NCTB Class 1–12 board textbooks?",
    a: "Yes. Inside the Online Library, use the NCTB Quick Jump strip or open Education & Textbooks to browse Pre-Primary, Primary (Class 1–5), Secondary (Class 6–10), HSC (Class 12), Madrasa, and University resources.",
  },
  {
    q: "How do study notes, custom reading lists, and JSON backups work?",
    a: "Everything you bookmark, track, or annotate in the web library saves locally in your browser. Visit the Stats tab anytime to export a portable .json backup file or import it on another device.",
  },
  {
    q: "What extra features does the AnaBook Android APK provide?",
    a: "The offline-first Android app caches all 29,178+ catalog entries locally, supports 1-tap full-folder offline downloads, 5 reading themes, and a full-screen mistouch lock while reading.",
  },
];

export function AppPromoClient() {
  const router = useRouter();
  const {
    presetKey,
    themeMode,
    theme,
    hydrated,
    setPresetKey,
    setThemeMode,
    setCommandOpen,
  } = useWebTheme();

  const [heroQuery, setHeroQuery] = useState("");
  const [releaseInfo, setReleaseInfo] = useState<AppVersionInfo | null>(null);
  const [showReleaseNotes, setShowReleaseNotes] = useState(false);
  const [openFaq, setOpenFaq] = useState<number | null>(0);

  const isDarkPreview = themeMode === "dark";
  const isDarkPage = hydrated && themeMode === "dark";

  useEffect(() => {
    const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";
    fetch(`${basePath}/app-version.json`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data && data.latestVersion) {
          setReleaseInfo(data as AppVersionInfo);
        }
      })
      .catch(() => {
        // Non-fatal
      });
  }, []);

  const handleHeroSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = heroQuery.trim();
    if (trimmed) {
      router.push(`/library/?q=${encodeURIComponent(trimmed)}`);
    } else {
      router.push("/library/");
    }
  };

  return (
    <div
      className="min-h-screen transition-colors duration-200"
      style={
        isDarkPage
          ? { backgroundColor: theme.bg, color: theme.ink }
          : { backgroundColor: "#FFFFFF", color: "#0F1115" }
      }
    >
      {/* Hero Section */}
      <section className="max-w-6xl mx-auto px-4 sm:px-8 pt-8 pb-12 sm:pt-14 sm:pb-20">
        <div className="grid lg:grid-cols-12 gap-8 lg:gap-12 items-center">
          {/* Left Copy + Live Release Pill + Instant Search + Dual Pill CTAs */}
          <div className="lg:col-span-6 space-y-4 sm:space-y-6 text-center lg:text-left">
            {releaseInfo && (
              <div className="inline-flex flex-col items-center lg:items-start gap-2">
                <button
                  type="button"
                  onClick={() => setShowReleaseNotes((s) => !s)}
                  className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border text-xs font-bold transition hover:opacity-85 cursor-pointer"
                  style={
                    isDarkPage
                      ? {
                          backgroundColor: theme.surface,
                          borderColor: theme.border,
                          color: theme.ink,
                        }
                      : {
                          backgroundColor: "#F5F6F8",
                          borderColor: "#E5E7EB",
                          color: "#0F1115",
                        }
                  }
                >
                  <span className="w-2 h-2 rounded-full bg-[#C6F353] ring-2 ring-[#0F1115]/15" />
                  <span>v{releaseInfo.latestVersion} · What&apos;s New</span>
                  <ChevronDown
                    className={`w-3.5 h-3.5 transition-transform ${
                      showReleaseNotes ? "rotate-180" : ""
                    }`}
                  />
                </button>
                {showReleaseNotes && releaseInfo.releaseNotes && (
                  <p
                    className="text-xs rounded-2xl border px-3.5 py-2.5 max-w-md text-left"
                    style={
                      isDarkPage
                        ? {
                            backgroundColor: theme.surface,
                            borderColor: theme.border,
                            color: theme.muted,
                          }
                        : {
                            backgroundColor: "#F5F6F8",
                            borderColor: "#E5E7EB",
                            color: "#5F6672",
                          }
                    }
                  >
                    {releaseInfo.releaseNotes}
                  </p>
                )}
              </div>
            )}

            <h1 className="text-3xl sm:text-5xl lg:text-[52px] font-extrabold tracking-tight leading-[1.12]">
              Read your favorite books easily with AnaBook.
            </h1>

            <p
              className="text-sm sm:text-lg max-w-md mx-auto lg:mx-0 leading-relaxed"
              style={{ color: isDarkPage ? theme.muted : "#5F6672" }}
            >
              Bangladesh&apos;s biggest eLibrary &amp; PDF archive — carry
              29,178+ Bangla, English &amp; NCTB Class 1–12 books in your pocket
              or read directly in your browser.
            </p>

            {/* Instant Hero Search Bar */}
            <form
              onSubmit={handleHeroSearch}
              className="max-w-lg mx-auto lg:mx-0 flex items-center gap-2 p-1.5 rounded-full border shadow-xs"
              style={
                isDarkPage
                  ? {
                      backgroundColor: theme.surface,
                      borderColor: theme.border,
                    }
                  : {
                      backgroundColor: "#F5F6F8",
                      borderColor: "#E5E7EB",
                    }
              }
            >
              <Search
                className="w-4 h-4 ml-3 shrink-0"
                style={{ color: isDarkPage ? theme.muted : "#5F6672" }}
              />
              <input
                type="text"
                value={heroQuery}
                onChange={(e) => setHeroQuery(e.target.value)}
                placeholder="Search 29,178+ books, authors, Class 1–12…"
                aria-label="Search AnaBook library"
                className="flex-1 min-w-0 bg-transparent text-xs sm:text-sm focus:outline-none py-1.5"
              />
              <button
                type="button"
                onClick={() => setCommandOpen(true)}
                className="hidden sm:inline-flex items-center px-2 py-1 rounded-full border text-[10px] font-bold cursor-pointer"
                style={
                  isDarkPage
                    ? {
                        backgroundColor: theme.surfaceAlt,
                        borderColor: theme.border,
                        color: theme.muted,
                      }
                    : {
                        backgroundColor: "#FFFFFF",
                        borderColor: "#E5E7EB",
                        color: "#5F6672",
                      }
                }
              >
                ⌘K
              </button>
              <button
                type="submit"
                className="px-4 py-2 rounded-full bg-[#0F1115] hover:bg-neutral-800 text-white text-xs font-extrabold transition shrink-0 cursor-pointer"
              >
                Search
              </button>
            </form>

            <div className="flex flex-wrap items-center justify-center lg:justify-start gap-2.5 sm:gap-3 pt-1">
              <a
                href={APK_URL}
                className="inline-flex items-center gap-2.5 sm:gap-3 px-4 sm:px-5 py-2.5 sm:py-3 rounded-full bg-[#0F1115] hover:bg-neutral-800 text-white transition shadow-md"
              >
                <Smartphone className="w-4 h-4 sm:w-5 sm:h-5 text-[#C6F353]" />
                <div className="text-left leading-tight">
                  <span className="block text-[9px] sm:text-[10px] text-neutral-300 font-medium">
                    Download for
                  </span>
                  <span className="block text-xs sm:text-sm font-bold">
                    Android APK
                  </span>
                </div>
              </a>

              <Link
                href="/library"
                className="inline-flex items-center gap-2.5 sm:gap-3 px-4 sm:px-5 py-2.5 sm:py-3 rounded-full bg-[#0F1115] hover:bg-neutral-800 text-white transition shadow-md"
              >
                <Globe className="w-4 h-4 sm:w-5 sm:h-5 text-[#C6F353]" />
                <div className="text-left leading-tight">
                  <span className="block text-[9px] sm:text-[10px] text-neutral-300 font-medium">
                    Browse in browser
                  </span>
                  <span className="block text-xs sm:text-sm font-bold">
                    Online Library
                  </span>
                </div>
              </Link>
            </div>
          </div>

          {/* Right Real Book Cover, Author Portrait & 3D Category Bento Showcase */}
          <div className="lg:col-span-6">
            <div className="grid grid-cols-2 gap-3.5 max-w-[490px] w-full mx-auto">
              {/* Tile 1: Real Book Cover Shelf */}
              <Link
                href="/library"
                className="col-span-2 group rounded-3xl p-5 sm:p-6 transition block"
                style={
                  isDarkPage
                    ? { backgroundColor: theme.surface }
                    : { backgroundColor: "#F5F6F8" }
                }
              >
                <div className="flex items-center justify-between mb-5">
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white text-[11px] font-bold text-[#0F1115] shadow-sm">
                    <span className="w-2 h-2 rounded-full bg-[#C6F353] ring-2 ring-[#0F1115]/10" />
                    Live Open Library
                  </span>
                  <span className="inline-flex items-center gap-1 text-xs font-extrabold group-hover:translate-x-0.5 transition-transform">
                    29,178+ Books
                    <ArrowRight className="w-3.5 h-3.5" />
                  </span>
                </div>

                <div className="flex items-end justify-center gap-3 sm:gap-4 pt-2 pb-1">
                  {FEATURED_COVERS.map((book, idx) => {
                    const poseClass =
                      idx === 0
                        ? "-rotate-3 group-hover:-rotate-6 group-hover:-translate-y-1"
                        : idx === 1
                          ? "-translate-y-1.5 scale-105 z-10 group-hover:-translate-y-2.5"
                          : "rotate-3 group-hover:rotate-6 group-hover:-translate-y-1";
                    return (
                      <div
                        key={book.id}
                        className={`w-24 sm:w-28 aspect-[2/3] rounded-xl overflow-hidden bg-neutral-200 shadow-lg ring-1 ring-black/5 transition-all duration-300 ${poseClass}`}
                      >
                        <img
                          src={`https://drive.google.com/thumbnail?id=${book.id}&sz=w400`}
                          alt={`${book.title} — ${book.author}`}
                          referrerPolicy="no-referrer"
                          className="w-full h-full object-cover"
                        />
                      </div>
                    );
                  })}
                </div>
              </Link>

              {/* Tile 2: Popular Author Portraits Card */}
              <Link
                href="/library?cat=Authors%20%26%20Scholars"
                className="rounded-3xl bg-[#C6F353] p-5 flex flex-col justify-between gap-4 transition hover:-translate-y-0.5"
              >
                <div className="flex items-center -space-x-2.5">
                  {FEATURED_AUTHORS.map((author) => (
                    <img
                      key={author.id}
                      src={`https://drive.google.com/thumbnail?id=${author.id}&sz=w160`}
                      alt={author.name}
                      referrerPolicy="no-referrer"
                      className="w-10 h-10 rounded-full object-cover ring-2 ring-[#C6F353] bg-white"
                    />
                  ))}
                </div>
                <div className="space-y-0.5">
                  <div className="text-base sm:text-lg font-extrabold text-[#0F1115] leading-tight">
                    131+ Authors
                  </div>
                  <p className="text-xs text-[#0F1115]/75 leading-snug">
                    Humayun, Tagore, Nazrul &amp; more
                  </p>
                </div>
              </Link>

              {/* Tile 3: 3D Category Icons & NCTB Classes Card */}
              <Link
                href="/library?cat=Education%20%26%20Textbooks"
                className="rounded-3xl bg-[#0F1115] text-white p-5 flex flex-col justify-between gap-4 transition hover:-translate-y-0.5"
              >
                <div className="flex items-center gap-1.5">
                  {CATEGORY_ICONS.map((icon) => (
                    <div
                      key={icon.id}
                      className="w-9 h-9 rounded-xl bg-white/10 p-1.5 flex items-center justify-center"
                    >
                      <img
                        src={`https://drive.google.com/thumbnail?id=${icon.id}&sz=w160`}
                        alt={icon.label}
                        referrerPolicy="no-referrer"
                        className="w-full h-full object-contain"
                      />
                    </div>
                  ))}
                </div>
                <div className="space-y-2">
                  <div className="text-base sm:text-lg font-extrabold leading-snug">
                    Class 1–12 &amp; 8 Shelf Types
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5">
                    {["NCTB", "HSC", "Offline"].map((tag) => (
                      <span
                        key={tag}
                        className="px-2 py-0.5 rounded-full bg-white/10 text-[#C6F353] text-[10px] font-bold"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Soft Metrics Strip */}
      <section className="max-w-5xl mx-auto px-4 sm:px-8 pb-12 sm:pb-16">
        <div
          className="rounded-3xl px-4 sm:px-6 py-6 sm:py-8 grid grid-cols-1 sm:grid-cols-3 gap-6 sm:gap-8 text-center border"
          style={
            isDarkPage
              ? { backgroundColor: theme.surface, borderColor: theme.border }
              : { backgroundColor: "#F5F6F8", borderColor: "transparent" }
          }
        >
          <div className="space-y-1.5">
            <div className="flex items-center justify-center gap-0.5 text-amber-500">
              {Array.from({ length: 5 }).map((_, i) => (
                <Star key={i} className="w-4 h-4 fill-current" />
              ))}
            </div>
            <p
              className="text-xs font-medium"
              style={{ color: isDarkPage ? theme.muted : "#5F6672" }}
            >
              29,178+ Verified Resources
            </p>
            <p className="text-lg font-extrabold">Bangla &amp; English</p>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-center gap-0.5 text-amber-500">
              {Array.from({ length: 5 }).map((_, i) => (
                <Star key={i} className="w-4 h-4 fill-current" />
              ))}
            </div>
            <p
              className="text-xs font-medium"
              style={{ color: isDarkPage ? theme.muted : "#5F6672" }}
            >
              319+ GB Open Drive Archive
            </p>
            <p className="text-lg font-extrabold">Class 1–12 &amp; Univ</p>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-center gap-0.5 text-amber-500">
              {Array.from({ length: 5 }).map((_, i) => (
                <Star key={i} className="w-4 h-4 fill-current" />
              ))}
            </div>
            <p
              className="text-xs font-medium"
              style={{ color: isDarkPage ? theme.muted : "#5F6672" }}
            >
              100% Free · PWA &amp; Android APK
            </p>
            <p className="text-lg font-extrabold">Offline Ready</p>
          </div>
        </div>
      </section>

      {/* Signature 3 Pastel Feature Cards Section */}
      <section
        id="features"
        className="max-w-5xl mx-auto px-4 sm:px-8 py-8 sm:py-12 space-y-8 sm:space-y-12"
      >
        <div className="text-center max-w-xl mx-auto space-y-2">
          <h2 className="text-2xl sm:text-4xl font-extrabold tracking-tight leading-tight">
            Unleash the true potential for offline reading.
          </h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 sm:gap-6">
          <div className="rounded-3xl bg-[#FFE98A] p-6 sm:p-7 flex flex-col justify-between gap-6 sm:gap-8 min-h-[250px] sm:min-h-[280px]">
            <div className="space-y-4">
              <div className="w-11 h-11 rounded-full bg-white text-[#0F1115] flex items-center justify-center shadow-sm">
                <WifiOff className="w-5 h-5" />
              </div>
              <div className="space-y-2">
                <h3 className="text-base sm:text-lg font-extrabold text-[#0F1115]">
                  100% Offline Reader
                </h3>
                <p className="text-xs sm:text-sm text-[#0F1115]/75 leading-relaxed">
                  Caches all 29,178+ books locally, plus 1-tap full-section
                  downloads for any class or author.
                </p>
              </div>
            </div>
            <div>
              <Link
                href="/library"
                className="inline-flex items-center gap-1.5 px-4 sm:px-5 py-2 sm:py-2.5 rounded-full bg-[#0F1115] hover:bg-neutral-800 text-white text-xs font-bold transition"
              >
                Explore Library
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>

          <div className="rounded-3xl bg-[#C7BEFF] p-6 sm:p-7 flex flex-col justify-between gap-6 sm:gap-8 min-h-[250px] sm:min-h-[280px]">
            <div className="space-y-4">
              <div className="w-11 h-11 rounded-full bg-white text-[#0F1115] flex items-center justify-center shadow-sm">
                <Zap className="w-5 h-5" />
              </div>
              <div className="space-y-2">
                <h3 className="text-base sm:text-lg font-extrabold text-[#0F1115]">
                  Class 1–12 &amp; Authors
                </h3>
                <p className="text-xs sm:text-sm text-[#0F1115]/75 leading-relaxed">
                  Instant NCTB class chips, 30 custom 3D category icons, and
                  131+ Drive-hosted author portraits.
                </p>
              </div>
            </div>
            <div>
              <Link
                href="/library?cat=Education%20%26%20Textbooks"
                className="inline-flex items-center gap-1.5 px-4 sm:px-5 py-2 sm:py-2.5 rounded-full bg-[#0F1115] hover:bg-neutral-800 text-white text-xs font-bold transition"
              >
                Browse Classes
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>

          <div className="rounded-3xl bg-[#FFD2C6] p-6 sm:p-7 flex flex-col justify-between gap-6 sm:gap-8 min-h-[250px] sm:min-h-[280px]">
            <div className="space-y-4">
              <div className="w-11 h-11 rounded-full bg-white text-[#0F1115] flex items-center justify-center shadow-sm">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div className="space-y-2">
                <h3 className="text-base sm:text-lg font-extrabold text-[#0F1115]">
                  Full-Screen Mistouch Lock
                </h3>
                <p className="text-xs sm:text-sm text-[#0F1115]/75 leading-relaxed">
                  Fast right-edge scroll rail paired with a lock toggle that
                  blocks accidental taps while reading.
                </p>
              </div>
            </div>
            <div>
              <a
                href={APK_URL}
                className="inline-flex items-center gap-1.5 px-4 sm:px-5 py-2 sm:py-2.5 rounded-full bg-[#0F1115] hover:bg-neutral-800 text-white text-xs font-bold transition"
              >
                Download APK
                <Download className="w-3.5 h-3.5" />
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Popular Book Series Showcase */}
      <section className="max-w-5xl mx-auto px-4 sm:px-8 py-8 space-y-5">
        <div className="flex items-end justify-between gap-3">
          <div>
            <span
              className="inline-flex items-center gap-1 text-[11px] font-extrabold uppercase tracking-wider"
              style={{ color: isDarkPage ? theme.accent : "#5F6672" }}
            >
              <Sparkles className="w-3.5 h-3.5" />
              Iconic Bengali Series
            </span>
            <h2 className="text-xl sm:text-3xl font-extrabold tracking-tight mt-1">
              Jump straight into legendary collections.
            </h2>
          </div>
          <Link
            href="/library?cat=Series%20%26%20Collections"
            className="text-xs font-extrabold hover:underline shrink-0"
            style={{ color: isDarkPage ? theme.accent : "#0F1115" }}
          >
            All Series →
          </Link>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {POPULAR_SERIES.map((ser) => (
            <Link
              key={ser.title}
              href={`/library/?q=${encodeURIComponent(ser.query)}`}
              className="rounded-2xl border p-4 flex flex-col justify-between gap-3 transition hover:-translate-y-0.5"
              style={
                isDarkPage
                  ? {
                      backgroundColor: theme.surface,
                      borderColor: theme.border,
                    }
                  : { backgroundColor: "#F5F6F8", borderColor: "#E5E7EB" }
              }
            >
              <span
                className="self-start px-2 py-0.5 rounded-full text-[10px] font-bold"
                style={
                  isDarkPage
                    ? {
                        backgroundColor: theme.accentSoft,
                        color: theme.accent,
                      }
                    : { backgroundColor: "#FFFFFF", color: "#0F1115" }
                }
              >
                {ser.tag}
              </span>
              <div>
                <p className="text-sm font-extrabold leading-snug">
                  {ser.title}
                </p>
                <p
                  className="text-[11px] mt-0.5"
                  style={{ color: isDarkPage ? theme.muted : "#5F6672" }}
                >
                  {ser.author}
                </p>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* Split Feature Showcase: Reader Theme Studio (Synced with Global Theme!) */}
      <section className="max-w-5xl mx-auto px-4 sm:px-8 py-10 sm:py-14">
        <div className="grid md:grid-cols-12 gap-8 sm:gap-10 items-center">
          <div
            className="md:col-span-6 rounded-3xl p-5 sm:p-7 space-y-4 sm:space-y-5 border"
            style={
              isDarkPage
                ? { backgroundColor: theme.surface, borderColor: theme.border }
                : { backgroundColor: "#F5F6F8", borderColor: "transparent" }
            }
          >
            <div className="flex items-center justify-between gap-3">
              <span className="text-sm font-extrabold">
                Reader Theme Studio
              </span>
              <div
                className="inline-flex items-center rounded-full bg-white p-1 border border-neutral-200/80 shadow-xs"
                role="group"
                aria-label="Preview color mode"
              >
                <button
                  type="button"
                  onClick={() => setThemeMode("light")}
                  className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold transition cursor-pointer ${
                    !isDarkPreview
                      ? "bg-[#0F1115] text-white"
                      : "text-[#5F6672] hover:text-[#0F1115]"
                  }`}
                >
                  <Sun className="w-3 h-3" />
                  Light
                </button>
                <button
                  type="button"
                  onClick={() => setThemeMode("dark")}
                  className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold transition cursor-pointer ${
                    isDarkPreview
                      ? "bg-[#0F1115] text-white"
                      : "text-[#5F6672] hover:text-[#0F1115]"
                  }`}
                >
                  <Moon className="w-3 h-3" />
                  Dark
                </button>
              </div>
            </div>

            <div
              className={`rounded-2xl p-5 border transition-colors duration-300 shadow-sm space-y-4 ${
                isDarkPreview
                  ? "border-white/10 text-white"
                  : "border-black/10 text-[#18181B]"
              }`}
              style={{
                backgroundColor: isDarkPreview
                  ? THEMES[presetKey].darkBg
                  : THEMES[presetKey].lightBg,
              }}
            >
              <div className="flex items-center justify-between gap-2">
                <span
                  className={`text-[10px] font-extrabold uppercase tracking-wider ${
                    isDarkPreview
                      ? "bg-white/95 px-2 py-0.5 rounded-full"
                      : ""
                  }`}
                  style={{ color: THEMES[presetKey].accent }}
                >
                  ANABOOK READER · {THEME_PRESETS[presetKey].label}
                </span>
                <span
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold ${
                    isDarkPreview
                      ? "bg-white/10 text-white/90"
                      : "bg-white/90 text-[#18181B] border border-black/5"
                  }`}
                >
                  <Lock className="w-3 h-3" />
                  Synced Live
                </span>
              </div>

              <div className="space-y-1.5">
                <h3 className="text-base sm:text-lg font-extrabold leading-snug">
                  সঞ্চয়িতা · রবীন্দ্রনাথ ঠাকুর
                </h3>
                <p
                  className={`text-xs leading-relaxed ${
                    isDarkPreview ? "text-white/80" : "text-[#18181B]/75"
                  }`}
                >
                  5 curated palette themes in Light &amp; Dark modes—any theme
                  you choose here persists across the entire Online Library.
                </p>
              </div>

              <div className="space-y-1.5 pt-1">
                <div className="flex items-center justify-between text-[11px] font-bold">
                  <span
                    className={
                      isDarkPreview ? "text-white/75" : "text-[#18181B]/70"
                    }
                  >
                    Reading Progress
                  </span>
                  <span>72%</span>
                </div>
                <div
                  className={`h-2 rounded-full overflow-hidden ${
                    isDarkPreview ? "bg-white/15" : "bg-black/10"
                  }`}
                >
                  <div
                    className="h-full rounded-full transition-all duration-300"
                    style={{
                      width: "72%",
                      backgroundColor: THEMES[presetKey].accent,
                    }}
                  />
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <div
                className="text-[11px] font-bold uppercase tracking-wider"
                style={{ color: isDarkPage ? theme.muted : "#5F6672" }}
              >
                Pick a Theme (Applies Everywhere)
              </div>
              <div className="flex flex-wrap gap-2">
                {(Object.keys(THEMES) as ThemePresetKey[]).map((k) => {
                  const active = presetKey === k;
                  return (
                    <button
                      key={k}
                      type="button"
                      onClick={() => setPresetKey(k)}
                      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold border transition cursor-pointer ${
                        active
                          ? "bg-[#0F1115] text-white border-[#0F1115] shadow-xs"
                          : "bg-white text-[#0F1115] border-neutral-200/80 hover:border-neutral-400"
                      }`}
                    >
                      <span
                        className="w-2.5 h-2.5 rounded-full ring-1 ring-black/15"
                        style={{ backgroundColor: THEMES[k].darkBg }}
                      />
                      {THEMES[k].name}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="md:col-span-6 space-y-4 sm:space-y-5 text-center md:text-left">
            <h2 className="text-2xl sm:text-4xl font-extrabold tracking-tight leading-tight">
              Personalized reading, notes, lists &amp; stats in one place.
            </h2>
            <p
              className="text-xs sm:text-base leading-relaxed"
              style={{ color: isDarkPage ? theme.muted : "#5F6672" }}
            >
              Track your daily reading streak, write study notes inside the
              fullscreen reader, organize custom lists, and export portable JSON
              backups. Switch between Espresso, Matcha, Midnight, Sepia, and
              Rosewood themes in Light or Dark mode.
            </p>
            <div className="flex flex-wrap items-center justify-center md:justify-start gap-2.5 sm:gap-3 pt-1">
              <a
                href={APK_URL}
                className="inline-flex items-center gap-2 sm:gap-2.5 pl-4 sm:pl-5 pr-1.5 sm:pr-2 py-1.5 sm:py-2 rounded-full bg-[#0F1115] hover:bg-neutral-800 text-white text-xs sm:text-sm font-semibold transition"
              >
                <span>Download AnaBook APK</span>
                <span className="w-6 h-6 sm:w-7 sm:h-7 rounded-full bg-[#C6F353] text-[#0F1115] flex items-center justify-center shrink-0">
                  <Download className="w-3 h-3 sm:w-3.5 sm:h-3.5 stroke-[2.5]" />
                </span>
              </a>
              <Link
                href="/library"
                className="inline-flex items-center gap-1.5 px-4 sm:px-5 py-2 sm:py-2.5 rounded-full bg-[#F5F6F8] hover:bg-neutral-200 text-[#0F1115] text-xs sm:text-sm font-bold transition"
              >
                <Layers className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
                Online Library
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Interactive FAQ Accordion */}
      <section className="max-w-4xl mx-auto px-4 sm:px-8 py-6 sm:py-10 space-y-5">
        <div className="text-center space-y-1.5">
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">
            Frequently Asked Questions
          </h2>
          <p
            className="text-xs sm:text-sm"
            style={{ color: isDarkPage ? theme.muted : "#5F6672" }}
          >
            Everything about Bangladesh&apos;s biggest online eLibrary, PDF
            downloads, and reading tools
          </p>
        </div>

        <div className="space-y-2.5">
          {FAQ_ITEMS.map((item, idx) => {
            const isOpen = openFaq === idx;
            return (
              <div
                key={item.q}
                className="rounded-2xl border overflow-hidden"
                style={
                  isDarkPage
                    ? {
                        backgroundColor: theme.surface,
                        borderColor: theme.border,
                      }
                    : { backgroundColor: "#F5F6F8", borderColor: "#E5E7EB" }
                }
              >
                <button
                  type="button"
                  onClick={() => setOpenFaq(isOpen ? null : idx)}
                  aria-expanded={isOpen}
                  className="w-full px-5 py-4 flex items-center justify-between gap-3 text-left text-xs sm:text-sm font-extrabold cursor-pointer"
                >
                  <span>{item.q}</span>
                  <ChevronDown
                    className={`w-4 h-4 shrink-0 transition-transform ${
                      isOpen ? "rotate-180" : ""
                    }`}
                  />
                </button>
                {isOpen && (
                  <div
                    className="px-5 pb-4 text-xs sm:text-sm leading-relaxed"
                    style={{ color: isDarkPage ? theme.muted : "#5F6672" }}
                  >
                    {item.a}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* About Developer Band */}
      <section
        id="about"
        className="max-w-5xl mx-auto px-4 sm:px-8 py-8 sm:py-12"
      >
        <div
          className="rounded-3xl p-6 sm:p-9 flex flex-col sm:flex-row items-center sm:items-center justify-between gap-6 text-center sm:text-left border"
          style={
            isDarkPage
              ? { backgroundColor: theme.surface, borderColor: theme.border }
              : { backgroundColor: "#F5F6F8", borderColor: "transparent" }
          }
        >
          <div className="flex flex-col sm:flex-row items-center gap-3.5 sm:gap-4">
            <img
              src={`${process.env.NEXT_PUBLIC_BASE_PATH || ""}/developer-profile.png`}
              alt="Salman Anik"
              className="w-16 h-16 rounded-full object-cover border-2 border-[#0F1115] shrink-0"
            />
            <div>
              <span
                className="text-[11px] font-bold uppercase tracking-wider"
                style={{ color: isDarkPage ? theme.muted : "#5F6672" }}
              >
                Built &amp; Curated By
              </span>
              <h3 className="text-lg sm:text-xl font-extrabold">Salman Anik</h3>
              <p
                className="text-xs sm:text-sm"
                style={{ color: isDarkPage ? theme.muted : "#5F6672" }}
              >
                CSE Student at East West University, Dhaka · Creator of AnaBook
                &amp; AnaPharm
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-center sm:justify-end gap-2">
            <a
              href="https://salmananik.vercel.app/"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3.5 sm:px-4 py-2 rounded-full bg-[#0F1115] text-white text-xs font-bold hover:bg-neutral-800 transition"
            >
              <Globe className="w-3.5 h-3.5 text-[#C6F353]" />
              Portfolio
            </a>
            <a
              href="https://github.com/salman-anik"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3.5 sm:px-4 py-2 rounded-full bg-white border border-neutral-200 text-[#0F1115] text-xs font-bold hover:border-neutral-400 transition"
            >
              <Github className="w-3.5 h-3.5" />
              GitHub
            </a>
            <a
              href="mailto:salmananik.bd@gmail.com"
              className="inline-flex items-center gap-1.5 px-3.5 sm:px-4 py-2 rounded-full bg-white border border-neutral-200 text-[#0F1115] text-xs font-bold hover:border-neutral-400 transition"
            >
              <Mail className="w-3.5 h-3.5" />
              Email
            </a>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer
        className="border-t py-6 sm:py-8 mt-4"
        style={{ borderColor: isDarkPage ? theme.border : "#F5F5F5" }}
      >
        <div
          className="max-w-6xl mx-auto px-4 sm:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-center sm:text-left"
          style={{ color: isDarkPage ? theme.muted : "#5F6672" }}
        >
          <span
            className="inline-flex items-center gap-2 font-semibold"
            style={{ color: isDarkPage ? theme.ink : "#0F1115" }}
          >
            <img
              src={`${process.env.NEXT_PUBLIC_BASE_PATH || ""}/logo.png`}
              alt="AnaBook Logo"
              className="w-5 h-5 sm:w-6 sm:h-6 rounded-lg object-cover"
            />
            AnaBook · Bangladesh&apos;s Biggest eLibrary &amp; eBook Library
          </span>
          <div className="flex flex-wrap justify-center items-center gap-4 sm:gap-5 font-medium">
            <Link href="/library" className="hover:opacity-80">
              Online Library
            </Link>
            <a href={APK_URL} className="hover:opacity-80">
              Download APK
            </a>
            <a
              href={REPO_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:opacity-80"
            >
              GitHub
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
