"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Download,
  Github,
  Globe,
  Layers,
  Lock,
  Mail,
  Moon,
  ShieldCheck,
  Smartphone,
  Star,
  Sun,
  WifiOff,
  Zap,
} from "lucide-react";

const APK_URL =
  "https://github.com/salman-anik/Bangladesh-Biggest-eBook-Library/raw/main/App/Bangladesh-eBook-Library.apk";
const REPO_URL =
  "https://github.com/salman-anik/Bangladesh-Biggest-eBook-Library";

type ThemeChoice = "espresso" | "matcha" | "midnight" | "sepia" | "rosewood";

const THEMES: Record<
  ThemeChoice,
  { name: string; darkBg: string; lightBg: string; accent: string }
> = {
  espresso: { name: "Espresso", darkBg: "#2D2826", lightBg: "#FAF6F3", accent: "#A86E56" },
  matcha: { name: "Matcha", darkBg: "#1E2B24", lightBg: "#F3F8F5", accent: "#4E8260" },
  midnight: { name: "Midnight", darkBg: "#1B2236", lightBg: "#F4F6FB", accent: "#4C6399" },
  sepia: { name: "Sepia", darkBg: "#2C2119", lightBg: "#FBF7EE", accent: "#A97434" },
  rosewood: { name: "Rosewood", darkBg: "#2A1F26", lightBg: "#FBF4F7", accent: "#A65A6D" },
};

const FEATURED_COVERS = [
  { id: "1FIcC7bE27-dPRVQo0pjbcstXIFw94OPd", title: "আলাতচক্র", author: "আহমদ ছফা" },
  { id: "1vDtlwfiNpS6R_yO6qQ4lQn2EzkQXucRn", title: "Dielectric Dilemma", author: "Robert S. Eisenberg" },
  { id: "12GJV1hO9GI_D8vqE9CwIdBehEbQNJGCO", title: "King of Sword and Sky", author: "C. L. Wilson" },
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

export function AppPromoClient() {
  const [selectedTheme, setSelectedTheme] = useState<ThemeChoice>("espresso");
  const [isDarkPreview, setIsDarkPreview] = useState(false);

  return (
    <div className="min-h-screen bg-white text-[#0F1115]">
      {/* Hero Section */}
      <section className="max-w-6xl mx-auto px-5 sm:px-8 pt-12 pb-16 sm:pt-16 sm:pb-20">
        <div className="grid lg:grid-cols-12 gap-12 items-center">
          {/* Left Copy + Dual Black Pill Badges */}
          <div className="lg:col-span-6 space-y-6">
            <h1 className="text-4xl sm:text-5xl lg:text-[54px] font-extrabold tracking-tight leading-[1.08] text-[#0F1115]">
              Read your favorite books easily with AnaBook.
            </h1>

            <p className="text-base sm:text-lg text-[#5F6672] max-w-md leading-relaxed">
              Carry 22,166+ Bangla, English &amp; NCTB Class 1–12 books in your pocket with the cleanest offline mobile library.
            </p>

            <div className="flex flex-wrap items-center gap-3 pt-2">
              <a
                href={APK_URL}
                className="inline-flex items-center gap-3 px-5 py-3 rounded-full bg-[#0F1115] hover:bg-neutral-800 text-white transition shadow-md"
              >
                <Smartphone className="w-5 h-5 text-[#C6F353]" />
                <div className="text-left leading-tight">
                  <span className="block text-[10px] text-neutral-300 font-medium">Download for</span>
                  <span className="block text-sm font-bold">Android APK</span>
                </div>
              </a>

              <Link
                href="/library"
                className="inline-flex items-center gap-3 px-5 py-3 rounded-full bg-[#0F1115] hover:bg-neutral-800 text-white transition shadow-md"
              >
                <Globe className="w-5 h-5 text-[#C6F353]" />
                <div className="text-left leading-tight">
                  <span className="block text-[10px] text-neutral-300 font-medium">Browse in browser</span>
                  <span className="block text-sm font-bold">Online Library</span>
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
                className="col-span-2 group rounded-3xl bg-[#F5F6F8] p-5 sm:p-6 transition hover:bg-[#EFEFF2] block"
              >
                <div className="flex items-center justify-between mb-5">
                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white text-[11px] font-bold text-[#0F1115] shadow-sm">
                    <span className="w-2 h-2 rounded-full bg-[#C6F353] ring-2 ring-[#0F1115]/10" />
                    Live Open Library
                  </span>
                  <span className="inline-flex items-center gap-1 text-xs font-extrabold text-[#0F1115] group-hover:translate-x-0.5 transition-transform">
                    22,166+ Books
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
                    Class 1–12 &amp; 9 Shelf Types
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

      {/* Soft Light-Gray 3-Column Metrics Strip */}
      <section className="max-w-5xl mx-auto px-5 sm:px-8 pb-16">
        <div className="rounded-3xl bg-[#F5F6F8] px-6 py-8 grid sm:grid-cols-3 gap-8 text-center">
          <div className="space-y-1.5">
            <div className="flex items-center justify-center gap-0.5 text-amber-500">
              {Array.from({ length: 5 }).map((_, i) => (
                <Star key={i} className="w-4 h-4 fill-current" />
              ))}
            </div>
            <p className="text-xs font-medium text-[#5F6672]">22,166+ Verified Resources</p>
            <p className="text-lg font-extrabold text-[#0F1115]">Bangla &amp; English</p>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-center gap-0.5 text-amber-500">
              {Array.from({ length: 5 }).map((_, i) => (
                <Star key={i} className="w-4 h-4 fill-current" />
              ))}
            </div>
            <p className="text-xs font-medium text-[#5F6672]">316.8 GB Open Drive Archive</p>
            <p className="text-lg font-extrabold text-[#0F1115]">Class 1–12 &amp; Univ</p>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-center gap-0.5 text-amber-500">
              {Array.from({ length: 5 }).map((_, i) => (
                <Star key={i} className="w-4 h-4 fill-current" />
              ))}
            </div>
            <p className="text-xs font-medium text-[#5F6672]">100% Free · 23.7 MB APK</p>
            <p className="text-lg font-extrabold text-[#0F1115]">Offline Ready</p>
          </div>
        </div>
      </section>

      {/* Signature 3 Pastel Feature Cards Section */}
      <section id="features" className="max-w-5xl mx-auto px-5 sm:px-8 py-12 space-y-12">
        <div className="text-center max-w-xl mx-auto space-y-2">
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-[#0F1115] leading-tight">
            Unleash the true potential for offline reading.
          </h2>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {/* Card 1: Pastel Yellow */}
          <div className="rounded-3xl bg-[#FFE98A] p-7 flex flex-col justify-between gap-8 min-h-[280px]">
            <div className="space-y-4">
              <div className="w-11 h-11 rounded-full bg-white text-[#0F1115] flex items-center justify-center shadow-sm">
                <WifiOff className="w-5 h-5" />
              </div>
              <div className="space-y-2">
                <h3 className="text-lg font-extrabold text-[#0F1115]">100% Offline Reader</h3>
                <p className="text-sm text-[#0F1115]/75 leading-relaxed">
                  Caches all 22,166+ books locally, plus 1-tap full-section downloads for any class or author.
                </p>
              </div>
            </div>
            <div>
              <Link
                href="/library"
                className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-full bg-[#0F1115] hover:bg-neutral-800 text-white text-xs font-bold transition"
              >
                Explore Library
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>

          {/* Card 2: Pastel Lavender */}
          <div className="rounded-3xl bg-[#C7BEFF] p-7 flex flex-col justify-between gap-8 min-h-[280px]">
            <div className="space-y-4">
              <div className="w-11 h-11 rounded-full bg-white text-[#0F1115] flex items-center justify-center shadow-sm">
                <Zap className="w-5 h-5" />
              </div>
              <div className="space-y-2">
                <h3 className="text-lg font-extrabold text-[#0F1115]">Class 1–12 &amp; Authors</h3>
                <p className="text-sm text-[#0F1115]/75 leading-relaxed">
                  Instant NCTB class chips, 30 custom 3D category icons, and 131+ Drive-hosted author portraits.
                </p>
              </div>
            </div>
            <div>
              <Link
                href="/library?cat=Education%20%26%20Textbooks"
                className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-full bg-[#0F1115] hover:bg-neutral-800 text-white text-xs font-bold transition"
              >
                Browse Classes
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          </div>

          {/* Card 3: Pastel Peach */}
          <div className="rounded-3xl bg-[#FFD2C6] p-7 flex flex-col justify-between gap-8 min-h-[280px]">
            <div className="space-y-4">
              <div className="w-11 h-11 rounded-full bg-white text-[#0F1115] flex items-center justify-center shadow-sm">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div className="space-y-2">
                <h3 className="text-lg font-extrabold text-[#0F1115]">Full-Screen Mistouch Lock</h3>
                <p className="text-sm text-[#0F1115]/75 leading-relaxed">
                  Fast right-edge scroll rail paired with a lock toggle that blocks accidental taps while reading.
                </p>
              </div>
            </div>
            <div>
              <a
                href={APK_URL}
                className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-full bg-[#0F1115] hover:bg-neutral-800 text-white text-xs font-bold transition"
              >
                Download APK
                <Download className="w-3.5 h-3.5" />
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Split Feature Showcase (Mirrors Lower Section of Reference) */}
      <section className="max-w-5xl mx-auto px-5 sm:px-8 py-14">
        <div className="grid md:grid-cols-12 gap-10 items-center">
          {/* Left Interactive Theme Studio Card (No Phone Frame) */}
          <div className="md:col-span-6 rounded-3xl bg-[#F5F6F8] p-6 sm:p-7 space-y-5">
            {/* Top Row: Studio Heading + Light / Dark Segmented Pill Toggle */}
            <div className="flex items-center justify-between gap-3">
              <span className="text-sm font-extrabold text-[#0F1115]">
                Reader Theme Studio
              </span>
              <div
                className="inline-flex items-center rounded-full bg-white p-1 border border-neutral-200/80 shadow-xs"
                role="group"
                aria-label="Preview color mode"
              >
                <button
                  type="button"
                  onClick={() => setIsDarkPreview(false)}
                  className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold transition ${
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
                  onClick={() => setIsDarkPreview(true)}
                  className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-bold transition ${
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

            {/* Flat Live-Styled Book Page Preview Card */}
            <div
              className={`rounded-2xl p-5 border transition-colors duration-300 shadow-sm space-y-4 ${
                isDarkPreview ? "border-white/10 text-white" : "border-black/10 text-[#18181B]"
              }`}
              style={{
                backgroundColor: isDarkPreview
                  ? THEMES[selectedTheme].darkBg
                  : THEMES[selectedTheme].lightBg,
              }}
            >
              <div className="flex items-center justify-between gap-2">
                <span
                  className={`text-[10px] font-extrabold uppercase tracking-wider ${
                    isDarkPreview ? "bg-white/95 px-2 py-0.5 rounded-full" : ""
                  }`}
                  style={{ color: THEMES[selectedTheme].accent }}
                >
                  ANABOOK READER
                </span>
                <span
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold ${
                    isDarkPreview
                      ? "bg-white/10 text-white/90"
                      : "bg-white/90 text-[#18181B] border border-black/5"
                  }`}
                >
                  <Lock className="w-3 h-3" />
                  Mistouch Lock
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
                  5 curated palette themes in Light &amp; Dark modes, with live font scaling, right-edge scroll rail, and full offline storage tracking.
                </p>
              </div>

              {/* Clean Reading Progress Bar */}
              <div className="space-y-1.5 pt-1">
                <div className="flex items-center justify-between text-[11px] font-bold">
                  <span className={isDarkPreview ? "text-white/75" : "text-[#18181B]/70"}>
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
                      backgroundColor: THEMES[selectedTheme].accent,
                    }}
                  />
                </div>
              </div>
            </div>

            {/* Bottom Theme Swatch Pills */}
            <div className="space-y-2">
              <div className="text-[11px] font-bold text-[#5F6672] uppercase tracking-wider">
                Pick a Theme
              </div>
              <div className="flex flex-wrap gap-2">
                {(Object.keys(THEMES) as ThemeChoice[]).map((k) => {
                  const active = selectedTheme === k;
                  return (
                    <button
                      key={k}
                      type="button"
                      onClick={() => setSelectedTheme(k)}
                      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold border transition ${
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

          {/* Right Clean Copy */}
          <div className="md:col-span-6 space-y-5">
            <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-[#0F1115] leading-tight">
              Personalized reading, themes &amp; stats in one place.
            </h2>
            <p className="text-sm sm:text-base text-[#5F6672] leading-relaxed">
              Track your daily reading streak, completed books, pages read, and exact local storage usage. Switch between Espresso, Matcha, Midnight, Sepia, and Rosewood themes in Light or Dark mode.
            </p>
            <div className="flex flex-wrap items-center gap-3 pt-1">
              <a
                href={APK_URL}
                className="inline-flex items-center gap-2.5 pl-5 pr-2 py-2 rounded-full bg-[#0F1115] hover:bg-neutral-800 text-white text-sm font-semibold transition"
              >
                <span>Download AnaBook APK</span>
                <span className="w-7 h-7 rounded-full bg-[#C6F353] text-[#0F1115] flex items-center justify-center">
                  <Download className="w-3.5 h-3.5 stroke-[2.5]" />
                </span>
              </a>
              <Link
                href="/library"
                className="inline-flex items-center gap-1.5 px-5 py-2.5 rounded-full bg-[#F5F6F8] hover:bg-neutral-200 text-[#0F1115] text-sm font-bold transition"
              >
                <Layers className="w-4 h-4" />
                Online Library
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* About Developer Band */}
      <section id="about" className="max-w-5xl mx-auto px-5 sm:px-8 py-12">
        <div className="rounded-3xl bg-[#F5F6F8] p-7 sm:p-9 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <img
              src={`${process.env.NEXT_PUBLIC_BASE_PATH || ""}/developer-profile.png`}
              alt="Salman Anik"
              className="w-16 h-16 rounded-full object-cover border-2 border-[#0F1115]"
            />
            <div>
              <span className="text-[11px] font-bold uppercase tracking-wider text-[#5F6672]">
                Built &amp; Curated By
              </span>
              <h3 className="text-xl font-extrabold text-[#0F1115]">Salman Anik</h3>
              <p className="text-xs sm:text-sm text-[#5F6672]">
                CSE Student at East West University, Dhaka · Creator of AnaBook &amp; AnaPharm
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <a
              href="https://salmananik.vercel.app/"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-[#0F1115] text-white text-xs font-bold hover:bg-neutral-800 transition"
            >
              <Globe className="w-3.5 h-3.5 text-[#C6F353]" />
              Portfolio
            </a>
            <a
              href="https://github.com/salman-anik"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-white border border-neutral-200 text-[#0F1115] text-xs font-bold hover:border-neutral-400 transition"
            >
              <Github className="w-3.5 h-3.5" />
              GitHub
            </a>
            <a
              href="mailto:salmananik.bd@gmail.com"
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full bg-white border border-neutral-200 text-[#0F1115] text-xs font-bold hover:border-neutral-400 transition"
            >
              <Mail className="w-3.5 h-3.5" />
              Email
            </a>
          </div>
        </div>
      </section>

      {/* Clean White Footer */}
      <footer className="border-t border-neutral-100 py-8 mt-4">
        <div className="max-w-6xl mx-auto px-5 sm:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-[#5F6672]">
          <span className="inline-flex items-center gap-2 font-semibold text-[#0F1115]">
            <img
              src={`${process.env.NEXT_PUBLIC_BASE_PATH || ""}/logo.png`}
              alt="AnaBook Logo"
              className="w-6 h-6 rounded-lg object-cover"
            />
            AnaBook · Bangladesh&apos;s Biggest eBook Library
          </span>
          <div className="flex items-center gap-5 font-medium">
            <Link href="/library" className="hover:text-[#0F1115]">
              Online Library
            </Link>
            <a href={APK_URL} className="hover:text-[#0F1115]">
              Download APK
            </a>
            <a href={REPO_URL} target="_blank" rel="noopener noreferrer" className="hover:text-[#0F1115]">
              GitHub
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
