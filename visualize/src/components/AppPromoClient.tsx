"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  Download,
  Github,
  Globe,
  Layers,
  Lock,
  Mail,
  ShieldCheck,
  Smartphone,
  Star,
  WifiOff,
  Zap,
} from "lucide-react";

const APK_URL =
  "https://github.com/salman-anik/Bangladesh-Biggest-eBook-Library/raw/main/App/Bangladesh-eBook-Library.apk";
const REPO_URL =
  "https://github.com/salman-anik/Bangladesh-Biggest-eBook-Library";

type ThemeChoice = "espresso" | "matcha" | "midnight" | "sepia" | "rosewood";

const THEMES: Record<ThemeChoice, { name: string; swatch: string; accent: string }> = {
  espresso: { name: "Espresso", swatch: "#2D2826", accent: "#C6927A" },
  matcha: { name: "Matcha", swatch: "#1E2B24", accent: "#8DB596" },
  midnight: { name: "Midnight", swatch: "#1B2236", accent: "#D8B26E" },
  sepia: { name: "Sepia", swatch: "#2C2119", accent: "#D49B54" },
  rosewood: { name: "Rosewood", swatch: "#2A1F26", accent: "#D48E9B" },
};

export function AppPromoClient() {
  const [selectedTheme, setSelectedTheme] = useState<ThemeChoice>("espresso");

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

          {/* Right Phone Mockup with Subtle Circular Halo & Lime-Green Header */}
          <div className="lg:col-span-6 flex justify-center relative">
            {/* Subtle circular halo behind phone */}
            <div className="relative flex items-center justify-center">
              <div className="absolute w-[310px] h-[310px] sm:w-[350px] sm:h-[350px] rounded-full border-[14px] border-dashed border-[#F3F4F6]" />
              <div className="absolute w-[260px] h-[260px] sm:w-[295px] sm:h-[295px] rounded-full border border-[#ECEEF2]" />

              {/* Phone Frame */}
              <div className="relative z-10 w-[248px] sm:w-[266px] rounded-[36px] border-[7px] border-[#0F1115] bg-white shadow-2xl overflow-hidden">
                {/* Notch */}
                <div className="bg-[#C6F353] pt-3 pb-4 px-4">
                  <div className="w-16 h-3.5 bg-[#0F1115] rounded-full mx-auto mb-3" />
                  <p className="text-[11px] font-bold text-[#0F1115]/80 mb-2">
                    Your offline library is ready.
                  </p>

                  {/* Dark Featured Book Card inside Lime Header */}
                  <div className="rounded-2xl bg-[#111214] text-white p-3.5 space-y-2.5 shadow-lg">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-bold text-[#C6F353] uppercase tracking-wider">
                        Continue Reading
                      </span>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-white/15">
                        72%
                      </span>
                    </div>
                    <div className="text-sm font-extrabold leading-snug">
                      সঞ্চয়িতা · রবীন্দ্রনাথ ঠাকুর
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-neutral-400">
                      <span>Bangla Classics · PDF</span>
                      <span className="text-[#C6F353] font-bold">Saved Offline</span>
                    </div>
                  </div>
                </div>

                {/* Clean White List Below */}
                <div className="p-4 space-y-2.5 bg-white">
                  <div className="flex items-center justify-between text-[11px] font-bold text-[#0F1115]">
                    <span>Quick Classes</span>
                    <span className="text-[#5F6672] font-medium">NCTB 1–12</span>
                  </div>

                  {[
                    { name: "Class 1 – Class 5", meta: "Primary · 209 books", pct: "w-3/4" },
                    { name: "Class 6 – Class 10", meta: "Secondary · 813 books", pct: "w-5/6" },
                    { name: "Humayun Ahmed", meta: "Author · 325 books", pct: "w-2/3" },
                  ].map((row) => (
                    <div key={row.name} className="space-y-1">
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="font-bold text-[#0F1115]">{row.name}</span>
                        <span className="text-[10px] text-[#5F6672]">{row.meta.split("·")[1]}</span>
                      </div>
                      <div className="h-1.5 rounded-full bg-[#F1F2F5] overflow-hidden">
                        <div className={`h-full rounded-full bg-[#0F1115] ${row.pct}`} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
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
          {/* Left Soft Gray Phone Box */}
          <div className="md:col-span-6 rounded-3xl bg-[#F5F6F8] p-8 flex justify-center">
            <div className="w-[238px] rounded-[32px] border-[6px] border-[#0F1115] bg-white shadow-xl overflow-hidden">
              <div
                className="p-4 text-white space-y-2 transition-colors duration-300"
                style={{ backgroundColor: THEMES[selectedTheme].swatch }}
              >
                <div className="flex items-center justify-between text-[10px] font-bold">
                  <span style={{ color: THEMES[selectedTheme].accent }}>ANABOOK READER</span>
                  <Lock className="w-3.5 h-3.5" style={{ color: THEMES[selectedTheme].accent }} />
                </div>
                <p className="text-xs font-bold leading-relaxed">
                  5 curated book themes in both Light &amp; Dark modes, with live font scaling and app storage tracking.
                </p>
              </div>
              <div className="p-4 space-y-3">
                <div className="text-[11px] font-bold text-[#0F1115]">Pick a Theme</div>
                <div className="flex flex-wrap gap-1.5">
                  {(Object.keys(THEMES) as ThemeChoice[]).map((k) => (
                    <button
                      key={k}
                      type="button"
                      onClick={() => setSelectedTheme(k)}
                      className={`px-2.5 py-1 rounded-full text-[10px] font-bold border transition ${
                        selectedTheme === k
                          ? "bg-[#0F1115] text-white border-[#0F1115]"
                          : "bg-[#F5F6F8] text-[#0F1115] border-transparent hover:border-neutral-300"
                      }`}
                    >
                      {THEMES[k].name}
                    </button>
                  ))}
                </div>
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
              src="/developer-profile.png"
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
          <span className="font-semibold text-[#0F1115]">
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
