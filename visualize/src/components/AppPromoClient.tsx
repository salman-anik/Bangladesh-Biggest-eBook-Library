"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  Download,
  Github,
  Globe,
  Layers,
  Lock,
  Mail,
  Moon,
  Palette,
  SlidersHorizontal,
  Smartphone,
  Sparkles,
  Sun,
  Users,
  WifiOff,
} from "lucide-react";

const APK_URL =
  "https://github.com/salman-anik/Bangladesh-Biggest-eBook-Library/raw/main/App/Bangladesh-eBook-Library.apk";
const REPO_URL =
  "https://github.com/salman-anik/Bangladesh-Biggest-eBook-Library";

type PresetId = "espresso" | "matcha" | "midnight" | "sepia" | "rosewood";

const THEME_PRESETS: Record<
  PresetId,
  {
    label: string;
    subtitle: string;
    dark: { bg: string; card: string; accent: string; ink: string; muted: string; border: string };
    light: { bg: string; card: string; accent: string; ink: string; muted: string; border: string };
    swatches: [string, string, string];
  }
> = {
  espresso: {
    label: "Espresso",
    subtitle: "Obsidian & Terracotta",
    swatches: ["#11100F", "#2D2826", "#C6927A"],
    dark: { bg: "#11100F", card: "#2D2826", accent: "#C6927A", ink: "#F7F3EE", muted: "#9E9590", border: "#3D3532" },
    light: { bg: "#FAF7F4", card: "#FFFFFF", accent: "#B56E52", ink: "#171412", muted: "#6E6560", border: "#E5DDD5" },
  },
  matcha: {
    label: "Matcha",
    subtitle: "Japanese Book Café",
    swatches: ["#0F1613", "#1E2B24", "#8DB596"],
    dark: { bg: "#0F1613", card: "#1E2B24", accent: "#8DB596", ink: "#F3F7F2", muted: "#8FA396", border: "#2D3F35" },
    light: { bg: "#F5F8F4", card: "#FFFFFF", accent: "#4C7A5B", ink: "#142018", muted: "#5D6E62", border: "#D4E0D2" },
  },
  midnight: {
    label: "Midnight",
    subtitle: "Indigo & Soft Gold",
    swatches: ["#0C101C", "#1B2236", "#D8B26E"],
    dark: { bg: "#0C101C", card: "#1B2236", accent: "#D8B26E", ink: "#F5F7FC", muted: "#8E99B5", border: "#2B3552" },
    light: { bg: "#F4F6FC", card: "#FFFFFF", accent: "#4A5D9E", ink: "#12182B", muted: "#5D6782", border: "#D5DDF0" },
  },
  sepia: {
    label: "Sepia",
    subtitle: "Leather & Parchment",
    swatches: ["#17120E", "#2C2119", "#D49B54"],
    dark: { bg: "#17120E", card: "#2C2119", accent: "#D49B54", ink: "#F9F1E4", muted: "#A89886", border: "#423327" },
    light: { bg: "#F7EFE2", card: "#FFFBF3", accent: "#8B5A2B", ink: "#241A10", muted: "#756352", border: "#DECBB0" },
  },
  rosewood: {
    label: "Rosewood",
    subtitle: "Plum & Dusty Rose",
    swatches: ["#161014", "#2A1F26", "#D48E9B"],
    dark: { bg: "#161014", card: "#2A1F26", accent: "#D48E9B", ink: "#FAF2F4", muted: "#A38F96", border: "#403039" },
    light: { bg: "#FBF5F7", card: "#FFFFFF", accent: "#A65568", ink: "#24171C", muted: "#78626A", border: "#E6D3DA" },
  },
};

const FEATURES = [
  {
    icon: WifiOff,
    title: "100% Offline After Sync",
    desc: "Caches all 22,166+ books locally, plus 1-tap single-book or full-section offline downloads (e.g. entire Class 7 or Humayun Ahmed).",
  },
  {
    icon: Layers,
    title: "Quick Class 1–12 & 3D Icons",
    desc: "Instant 1-tap Class 1–12 pills inside Education & Textbooks paired with 30 custom 3D category icons hosted on Google Drive.",
  },
  {
    icon: Lock,
    title: "Full-Screen Lock & Side Scroll Rail",
    desc: "Drag the right-edge scroll rail to jump anywhere in a book, and tap Lock to block accidental mistouches while scrolling.",
  },
  {
    icon: Palette,
    title: "5 Themes · Dark & White Modes",
    desc: "Switch live across Espresso, Matcha, Midnight, Sepia, and Rosewood palettes in both Dark and White modes with custom font sizes.",
  },
  {
    icon: Users,
    title: "131+ Author Portraits & Avatars",
    desc: "Explore Bangladeshi and international writers with Drive-hosted portraits and minimalist Pinterest-inspired illustrated avatars.",
  },
  {
    icon: Sparkles,
    title: "Suggested For You & Reading Stats",
    desc: "Personalized book suggestions on Home alongside reading streaks, completed books, pages logged, and live app storage usage.",
  },
];

export function AppPromoClient() {
  const [preset, setPreset] = useState<PresetId>("espresso");
  const [mode, setMode] = useState<"dark" | "light">("dark");
  const activeColors = THEME_PRESETS[preset][mode];

  return (
    <div className="min-h-screen bg-[#11100F] text-[#F7F3EE]">
      {/* Hero Section */}
      <section className="relative overflow-hidden border-b border-[#26211F]">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-14 sm:py-20 grid lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-7 space-y-6">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#C6927A]/15 border border-[#C6927A]/40 text-[#C6927A] text-xs font-bold tracking-wide">
              <Smartphone className="w-3.5 h-3.5" />
              ANDROID OFFLINE READER · v1.0.0 · 23.7 MB APK
            </div>

            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tight leading-[1.07] text-[#F7F3EE]">
              22,166+ Bangla &amp; Academic Books.{" "}
              <span className="text-[#C6927A]">Read Anywhere Offline.</span>
            </h1>

            <p className="text-base sm:text-lg text-[#9E9590] max-w-2xl leading-relaxed">
              The official offline-first Android app for Bangladesh&apos;s Biggest eBook Library — featuring Class 1–12 NCTB textbooks, university courses, Bangla classics, 1-tap full-section downloads, and distraction-free reading.
            </p>

            <div className="flex flex-wrap items-center gap-3 pt-1">
              <a
                href={APK_URL}
                className="inline-flex items-center gap-2.5 px-6 py-3.5 rounded-2xl bg-[#F2ECE6] hover:bg-white text-[#171412] font-extrabold text-sm sm:text-base shadow-xl transition"
              >
                <Download className="w-5 h-5" />
                Download Android APK
              </a>
              <Link
                href="/library"
                className="inline-flex items-center gap-2 px-6 py-3.5 rounded-2xl bg-[#2D2826] hover:bg-[#3A3330] border border-[#3D3532] text-[#F7F3EE] font-bold text-sm sm:text-base transition"
              >
                <BookOpen className="w-5 h-5 text-[#C6927A]" />
                Open Online Library
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>

            <div className="grid grid-cols-3 gap-4 pt-4 border-t border-[#26211F] max-w-lg">
              <div>
                <div className="text-2xl font-black text-[#F7F3EE]">22,166+</div>
                <div className="text-xs text-[#9E9590]">Books &amp; Textbooks</div>
              </div>
              <div>
                <div className="text-2xl font-black text-[#C6927A]">316.8 GB</div>
                <div className="text-xs text-[#9E9590]">Open Drive Archive</div>
              </div>
              <div>
                <div className="text-2xl font-black text-[#5F7A6F]">23.7 MB</div>
                <div className="text-xs text-[#9E9590]">Lightweight APK</div>
              </div>
            </div>
          </div>

          {/* Live Interactive Theme-Switchable Phone Preview */}
          <div className="lg:col-span-5 flex flex-col items-center gap-4">
            <div
              className="w-full max-w-[332px] rounded-[36px] border-2 p-4 shadow-2xl space-y-3.5 transition-colors duration-300"
              style={{
                backgroundColor: activeColors.bg,
                borderColor: activeColors.border,
                color: activeColors.ink,
              }}
            >
              <div className="flex items-center justify-between px-1">
                <span className="text-xs font-extrabold tracking-wider">BANGLA LIBRARY</span>
                <span
                  className="text-[10px] font-bold px-2.5 py-0.5 rounded-full border"
                  style={{
                    backgroundColor: activeColors.card,
                    borderColor: activeColors.border,
                    color: activeColors.accent,
                  }}
                >
                  {THEME_PRESETS[preset].label}
                </span>
              </div>

              <div
                className="rounded-2xl border p-4 space-y-2.5"
                style={{ backgroundColor: activeColors.card, borderColor: activeColors.border }}
              >
                <div
                  className="text-[10px] font-extrabold uppercase tracking-wider"
                  style={{ color: activeColors.accent }}
                >
                  CONTINUE READING
                </div>
                <div className="text-sm font-extrabold leading-snug">
                  সঞ্চয়িতা · রবীন্দ্রনাথ ঠাকুর
                </div>
                <div className="flex items-center justify-between pt-1">
                  <div className="flex items-center gap-2">
                    <span
                      className="w-9 h-9 rounded-full border-2 flex items-center justify-center text-[11px] font-bold"
                      style={{ borderColor: activeColors.accent }}
                    >
                      72%
                    </span>
                    <span
                      className="px-3 py-1.5 rounded-xl text-xs font-extrabold"
                      style={{
                        backgroundColor: activeColors.accent,
                        color: mode === "dark" ? "#171412" : "#FFFFFF",
                      }}
                    >
                      Read Offline
                    </span>
                  </div>
                  <span className="text-[10px] font-bold px-2 py-1 rounded-md bg-[#5F7A6F] text-white">
                    OFFLINE
                  </span>
                </div>
              </div>

              <div className="space-y-2">
                <div className="text-xs font-bold px-1">Quick Class Access</div>
                <div className="flex gap-1.5 overflow-hidden">
                  {["Class 1", "Class 3", "Class 7", "Class 10", "HSC"].map((c, idx) => (
                    <span
                      key={c}
                      className="px-2.5 py-1 rounded-lg text-[10px] font-bold whitespace-nowrap border"
                      style={
                        idx === 2
                          ? {
                              backgroundColor: activeColors.accent,
                              borderColor: activeColors.accent,
                              color: mode === "dark" ? "#171412" : "#FFFFFF",
                            }
                          : {
                              backgroundColor: activeColors.card,
                              borderColor: activeColors.border,
                              color: activeColors.ink,
                            }
                      }
                    >
                      {c}
                    </span>
                  ))}
                </div>
              </div>

              <div
                className="grid grid-cols-5 items-center pt-2.5 border-t text-center text-[10px]"
                style={{ borderColor: activeColors.border, color: activeColors.muted }}
              >
                <span style={{ color: activeColors.ink, fontWeight: 800 }}>Home</span>
                <span>Library</span>
                <span
                  className="mx-auto w-9 h-9 rounded-full flex items-center justify-center font-black text-sm"
                  style={{
                    backgroundColor: activeColors.accent,
                    color: mode === "dark" ? "#171412" : "#FFFFFF",
                  }}
                >
                  ⊞
                </span>
                <span>Stats</span>
                <span>Settings</span>
              </div>
            </div>

            {/* Interactive Mode + Theme Preview Controls */}
            <div className="flex flex-wrap items-center justify-center gap-2">
              <button
                type="button"
                onClick={() => setMode((m) => (m === "dark" ? "light" : "dark"))}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#2D2826] border border-[#3D3532] text-xs font-bold text-[#F2ECE6] hover:border-[#C6927A] transition"
              >
                {mode === "dark" ? <Sun className="w-3.5 h-3.5 text-[#C6927A]" /> : <Moon className="w-3.5 h-3.5 text-[#C6927A]" />}
                {mode === "dark" ? "Preview White" : "Preview Dark"}
              </button>

              {(Object.keys(THEME_PRESETS) as PresetId[]).map((key) => {
                const p = THEME_PRESETS[key];
                const selected = preset === key;
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setPreset(key)}
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl border text-xs font-bold transition ${
                      selected
                        ? "bg-[#C6927A]/20 border-[#C6927A] text-[#F7F3EE]"
                        : "bg-[#1D1A18] border-[#3D3532] text-[#9E9590] hover:text-[#F7F3EE]"
                    }`}
                  >
                    <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: p.swatches[2] }} />
                    {p.label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section id="features" className="max-w-6xl mx-auto px-4 sm:px-6 py-16 space-y-8">
        <div className="space-y-2">
          <span className="text-xs font-extrabold uppercase tracking-widest text-[#C6927A]">
            APP HIGHLIGHTS
          </span>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-[#F7F3EE]">
            Built for Effortless Offline Study &amp; Reading
          </h2>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {FEATURES.map((feat) => {
            const Icon = feat.icon;
            return (
              <div
                key={feat.title}
                className="rounded-2xl bg-[#1D1A18] border border-[#3D3532] p-5 space-y-3 hover:border-[#C6927A]/60 transition"
              >
                <div className="w-10 h-10 rounded-xl bg-[#C6927A]/15 text-[#C6927A] flex items-center justify-center">
                  <Icon className="w-5 h-5" />
                </div>
                <h3 className="font-extrabold text-base text-[#F7F3EE]">{feat.title}</h3>
                <p className="text-sm text-[#9E9590] leading-relaxed">{feat.desc}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* Download Steps + Developer Section */}
      <section className="border-t border-[#26211F] bg-[#1D1A18]/40">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-16 grid lg:grid-cols-12 gap-8 items-start">
          <div className="lg:col-span-7 rounded-3xl bg-[#2D2826] border border-[#3D3532] p-7 sm:p-8 space-y-5">
            <div className="inline-flex items-center gap-2 text-xs font-extrabold uppercase tracking-widest text-[#C6927A]">
              <SlidersHorizontal className="w-4 h-4" />
              QUICK INSTALL GUIDE
            </div>
            <h2 className="text-2xl font-black text-[#F7F3EE]">
              Install on Any Android Device in Seconds
            </h2>
            <ul className="space-y-3 text-sm text-[#F2ECE6]/90">
              <li className="flex items-start gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-[#C6927A] shrink-0 mt-0.5" />
                <span>
                  Tap <strong>Download Android APK</strong> to save <code>Bangladesh-eBook-Library.apk</code> (23.7 MB).
                </span>
              </li>
              <li className="flex items-start gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-[#C6927A] shrink-0 mt-0.5" />
                <span>
                  Open the APK file and allow installation from your browser if prompted.
                </span>
              </li>
              <li className="flex items-start gap-2.5">
                <CheckCircle2 className="w-4 h-4 text-[#C6927A] shrink-0 mt-0.5" />
                <span>
                  Launch the app once online to cache all 22,166+ books — or use the{" "}
                  <Link href="/library" className="text-[#C6927A] underline font-bold">
                    Online Library
                  </Link>{" "}
                  directly in your browser.
                </span>
              </li>
            </ul>
            <div className="flex flex-wrap gap-3 pt-2">
              <a
                href={APK_URL}
                className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-[#C6927A] hover:bg-[#d5a38c] text-[#171412] font-extrabold text-sm transition"
              >
                <Download className="w-4 h-4" />
                Download APK (23.7 MB)
              </a>
              <Link
                href="/library"
                className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-[#11100F] hover:bg-[#1D1A18] border border-[#3D3532] text-[#F7F3EE] font-bold text-sm transition"
              >
                <Globe className="w-4 h-4 text-[#C6927A]" />
                Open Online Library
              </Link>
            </div>
          </div>

          <div className="lg:col-span-5 rounded-3xl bg-[#1D1A18] border border-[#3D3532] p-7 space-y-4">
            <span className="text-xs font-extrabold uppercase tracking-widest text-[#C6927A]">
              DEVELOPER &amp; CURATOR
            </span>
            <div className="flex items-center gap-4">
              <img
                src="/developer-profile.png"
                alt="Salman Anik"
                className="w-16 h-16 rounded-full object-cover border-2 border-[#C6927A]"
              />
              <div>
                <h3 className="text-lg font-extrabold text-[#F7F3EE]">Salman Anik</h3>
                <p className="text-xs text-[#9E9590]">
                  CSE Student · East West University, Dhaka
                </p>
              </div>
            </div>
            <p className="text-sm text-[#9E9590] leading-relaxed">
              Computer Science &amp; Engineering student focused on Python, Data Science, and building practical open-source projects — including Bangladesh&apos;s Biggest eBook Library and AnaPharm.
            </p>
            <div className="flex flex-wrap gap-2 pt-1">
              <a
                href="https://salmananik.vercel.app/"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-[#C6927A] text-[#171412] text-xs font-extrabold transition hover:bg-[#d5a38c]"
              >
                <Globe className="w-3.5 h-3.5" />
                Portfolio
              </a>
              <a
                href="https://github.com/salman-anik"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-[#2D2826] border border-[#3D3532] text-[#F2ECE6] text-xs font-bold hover:border-[#C6927A] transition"
              >
                <Github className="w-3.5 h-3.5" />
                GitHub
              </a>
              <a
                href="mailto:salmananik.bd@gmail.com"
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-[#2D2826] border border-[#3D3532] text-[#F2ECE6] text-xs font-bold hover:border-[#C6927A] transition"
              >
                <Mail className="w-3.5 h-3.5" />
                Email
              </a>
            </div>
          </div>
        </div>
      </section>

      <footer className="border-t border-[#26211F] py-7">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-[#9E9590]">
          <span>
            Bangladesh&apos;s Biggest eBook Library · Built by Salman Anik
          </span>
          <div className="flex items-center gap-4">
            <Link href="/library" className="hover:text-[#F7F3EE]">
              Online Library
            </Link>
            <a href={APK_URL} className="text-[#C6927A] font-semibold hover:underline">
              Download APK
            </a>
            <a href={REPO_URL} target="_blank" rel="noopener noreferrer" className="hover:text-[#F7F3EE]">
              GitHub
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
