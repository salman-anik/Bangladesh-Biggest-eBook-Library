import Link from "next/link";
import {
  ArrowRight,
  BookOpen,
  Download,
  Github,
  Globe,
  Layers,
  Lock,
  Palette,
  SlidersHorizontal,
  Smartphone,
  Sparkles,
  Users,
  WifiOff,
} from "lucide-react";

const APK_URL =
  "https://github.com/salman-anik/Bangladesh-Biggest-eBook-Library/raw/main/App/Bangladesh-eBook-Library.apk";
const REPO_URL =
  "https://github.com/salman-anik/Bangladesh-Biggest-eBook-Library";

const THEMES = [
  { name: "Espresso", desc: "Warm Obsidian & Terracotta", colors: ["#11100F", "#2D2826", "#C6927A"] },
  { name: "Matcha", desc: "Japanese Book Café", colors: ["#0F1613", "#1E2B24", "#8DB596"] },
  { name: "Midnight", desc: "Indigo Velvet & Gold", colors: ["#0C101C", "#1B2236", "#D8B26E"] },
  { name: "Sepia", desc: "Vintage Leather & Parchment", colors: ["#17120E", "#2C2119", "#D49B54"] },
  { name: "Rosewood", desc: "Literary Plum & Rose", colors: ["#161014", "#2A1F26", "#D48E9B"] },
];

const FEATURES = [
  {
    icon: WifiOff,
    title: "100% Offline After Sync",
    desc: "Caches all 22,166+ books locally, plus 1-tap single-book or full-section offline downloads (e.g. entire Class 7 or Humayun Ahmed).",
  },
  {
    icon: Layers,
    title: "Quick Class 1–12 & 3D Category Icons",
    desc: "Jump directly into Pre-Primary through Class 12 NCTB books, University courses, or Literature with 3D category artwork.",
  },
  {
    icon: Lock,
    title: "Full-Screen Lock & Side Scroll Rail",
    desc: "Drag the rapid side scrollbar to jump to any page instantly, and tap Lock to block accidental taps while scrolling.",
  },
  {
    icon: Palette,
    title: "5 Themes · Dark & White Modes",
    desc: "Switch effortlessly between Espresso, Matcha, Midnight, Sepia, and Rosewood palettes with custom font scaling.",
  },
  {
    icon: Users,
    title: "131+ Author Portraits & Avatars",
    desc: "Browse popular Bangla & international writers with Drive-hosted portraits and illustrated editorial avatars.",
  },
  {
    icon: Sparkles,
    title: "Suggested For You & Reading Tracker",
    desc: "Personalized book suggestions on Home alongside daily streaks, pages read, completion status, and storage breakdown.",
  },
];

export default function AppPromoHomePage() {
  return (
    <div className="min-h-screen bg-[#11100F] text-[#F7F3EE] selection:bg-[#C6927A]/30">
      {/* Sticky Top Navbar with Prominent Online Library Option */}
      <header className="sticky top-0 z-50 border-b border-[#3D3532]/80 bg-[#11100F]/90 backdrop-blur-md">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
          <Link href="/" className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#C6927A] text-[#171412] font-black text-sm flex items-center justify-center shadow-lg shadow-[#C6927A]/20">
              BL
            </div>
            <div>
              <span className="font-extrabold text-sm sm:text-base tracking-tight text-[#F7F3EE] block leading-none">
                Bangladesh eBook Library
              </span>
              <span className="text-[11px] text-[#C6927A] font-medium">
                বাংলাদেশের বৃহত্তম ই-বুক লাইব্রেরি
              </span>
            </div>
          </Link>

          <nav className="hidden md:flex items-center gap-6 text-sm font-medium text-[#9E9590]">
            <a href="#features" className="hover:text-[#F7F3EE] transition">
              Features
            </a>
            <a href="#themes" className="hover:text-[#F7F3EE] transition">
              Themes
            </a>
            <a href="#download" className="hover:text-[#F7F3EE] transition">
              APK
            </a>
            <a href={REPO_URL} target="_blank" rel="noopener noreferrer" className="hover:text-[#F7F3EE] transition">
              GitHub
            </a>
          </nav>

          <div className="flex items-center gap-2.5">
            <Link
              href="/library"
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-[#2D2826] hover:bg-[#3A3330] border border-[#3D3532] text-[#F2ECE6] text-xs sm:text-sm font-bold transition"
            >
              <Globe className="w-4 h-4 text-[#C6927A]" />
              Online Library
            </Link>
            <a
              href={APK_URL}
              className="hidden sm:inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#C6927A] hover:bg-[#d5a38c] text-[#171412] text-xs sm:text-sm font-extrabold transition"
            >
              <Download className="w-4 h-4" />
              Get APK
            </a>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main>
        <section className="relative overflow-hidden border-b border-[#26211F]">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 py-14 sm:py-20 grid lg:grid-cols-12 gap-10 items-center">
            <div className="lg:col-span-7 space-y-6">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#C6927A]/15 border border-[#C6927A]/40 text-[#C6927A] text-xs font-bold tracking-wide">
                <Smartphone className="w-3.5 h-3.5" />
                ANDROID OFFLINE READER · v1.0.0 APK
              </div>

              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black tracking-tight leading-[1.08] text-[#F7F3EE]">
                22,166+ Bangla &amp; Academic Books.{" "}
                <span className="text-[#C6927A]">In Your Pocket.</span>
              </h1>

              <p className="text-base sm:text-lg text-[#9E9590] max-w-2xl leading-relaxed">
                A fast, warm, offline-first mobile library built for Bangladeshi readers and students — featuring Class 1–12 NCTB textbooks, university references, Bangla literature, 1-tap full-section downloads, and distraction-free reading.
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
                  <div className="text-2xl font-black text-[#C6927A]">316+ GB</div>
                  <div className="text-xs text-[#9E9590]">Open Drive Archive</div>
                </div>
                <div>
                  <div className="text-2xl font-black text-[#5F7A6F]">100%</div>
                  <div className="text-xs text-[#9E9590]">Offline Search &amp; Read</div>
                </div>
              </div>
            </div>

            {/* Interactive Phone Mockup Card */}
            <div className="lg:col-span-5 flex justify-center">
              <div className="w-full max-w-[330px] rounded-[34px] border-2 border-[#3D3532] bg-[#1D1A18] p-4 shadow-2xl space-y-4">
                <div className="flex items-center justify-between px-1">
                  <span className="text-xs font-extrabold tracking-wider text-[#F7F3EE]">BANGLA LIBRARY</span>
                  <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-[#2D2826] text-[#C6927A] border border-[#3D3532]">
                    5 THEMES
                  </span>
                </div>

                <div className="rounded-2xl bg-[#2D2826] border border-[#3D3532] p-4 space-y-3">
                  <div className="text-[10px] font-extrabold uppercase tracking-wider text-[#C6927A]">
                    CONTINUE READING
                  </div>
                  <div className="text-sm font-extrabold text-[#F7F3EE] leading-snug">
                    সঞ্চয়িতা · রবীন্দ্রনাথ ঠাকুর
                  </div>
                  <div className="flex items-center justify-between pt-1">
                    <div className="flex items-center gap-2">
                      <span className="w-9 h-9 rounded-full border-2 border-[#C6927A] flex items-center justify-center text-[11px] font-bold text-[#F7F3EE]">
                        72%
                      </span>
                      <span className="px-3 py-1.5 rounded-xl bg-[#F2ECE6] text-[#171412] text-xs font-extrabold">
                        Read Offline
                      </span>
                    </div>
                    <span className="text-[10px] font-bold px-2 py-1 rounded-md bg-[#5F7A6F] text-[#F7F3EE]">
                      OFFLINE
                    </span>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="text-xs font-bold text-[#F7F3EE] px-1">Quick Class Access</div>
                  <div className="flex gap-1.5 overflow-hidden">
                    {["Class 1", "Class 6", "Class 7", "Class 10", "HSC"].map((c, idx) => (
                      <span
                        key={c}
                        className={`px-2.5 py-1 rounded-lg text-[10px] font-bold whitespace-nowrap ${
                          idx === 2
                            ? "bg-[#C6927A] text-[#171412]"
                            : "bg-[#2D2826] text-[#F2ECE6] border border-[#3D3532]"
                        }`}
                      >
                        {c}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-5 items-center pt-2 border-t border-[#3D3532] text-center text-[10px] text-[#9E9590]">
                  <span className="text-[#F7F3EE] font-bold">Home</span>
                  <span>Library</span>
                  <span className="mx-auto w-9 h-9 rounded-full bg-[#C6927A] text-[#171412] flex items-center justify-center font-black">
                    ⊞
                  </span>
                  <span>Stats</span>
                  <span>Settings</span>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Features Grid */}
        <section id="features" className="max-w-6xl mx-auto px-4 sm:px-6 py-16 space-y-8">
          <div className="space-y-2">
            <span className="text-xs font-extrabold uppercase tracking-widest text-[#C6927A]">
              DESIGNED FOR READERS
            </span>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-[#F7F3EE]">
              Everything Needed to Study &amp; Read Offline
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

        {/* Themes Showcase */}
        <section id="themes" className="border-y border-[#26211F] bg-[#1D1A18]/50">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 py-14 space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3">
              <div>
                <span className="text-xs font-extrabold uppercase tracking-widest text-[#C6927A]">
                  MODE &amp; THEMES
                </span>
                <h2 className="text-2xl sm:text-3xl font-extrabold text-[#F7F3EE] mt-1">
                  5 Book-Inspired Palettes · Dark &amp; White Modes
                </h2>
              </div>
              <div className="inline-flex items-center gap-2 text-xs font-semibold text-[#9E9590]">
                <SlidersHorizontal className="w-4 h-4 text-[#C6927A]" />
                Small · Normal · Large typography scaling
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
              {THEMES.map((t) => (
                <div
                  key={t.name}
                  className="rounded-2xl bg-[#11100F] border border-[#3D3532] p-4 space-y-3"
                >
                  <div className="flex items-center gap-1.5">
                    {t.colors.map((c) => (
                      <span
                        key={c}
                        className="w-5 h-5 rounded-full border border-[#3D3532]"
                        style={{ backgroundColor: c }}
                      />
                    ))}
                  </div>
                  <div>
                    <div className="font-bold text-sm text-[#F7F3EE]">{t.name}</div>
                    <div className="text-[11px] text-[#9E9590]">{t.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Download & Online Library CTA */}
        <section id="download" className="max-w-6xl mx-auto px-4 sm:px-6 py-16">
          <div className="rounded-3xl bg-[#2D2826] border border-[#3D3532] p-8 sm:p-10 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-6">
            <div className="space-y-2 max-w-2xl">
              <h2 className="text-2xl sm:text-3xl font-black text-[#F7F3EE]">
                Install the Android App or Browse Inline Online
              </h2>
              <p className="text-sm sm:text-base text-[#F2ECE6]/80">
                Download the signed standalone Android APK directly from the GitHub App folder, or launch the inline web catalog to search and preview every book right in your browser.
              </p>
            </div>
            <div className="flex flex-wrap gap-3">
              <a
                href={APK_URL}
                className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-[#C6927A] hover:bg-[#d5a38c] text-[#171412] font-extrabold text-sm transition"
              >
                <Download className="w-4 h-4" />
                Download APK
              </a>
              <Link
                href="/library"
                className="inline-flex items-center gap-2 px-5 py-3 rounded-xl bg-[#11100F] hover:bg-[#1D1A18] border border-[#3D3532] text-[#F7F3EE] font-bold text-sm transition"
              >
                <Globe className="w-4 h-4 text-[#C6927A]" />
                Online Library
              </Link>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-[#26211F] py-8">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-[#9E9590]">
          <div>
            Curated &amp; built by{" "}
            <a
              href="https://salmananik.vercel.app/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[#F7F3EE] font-bold hover:text-[#C6927A]"
            >
              Salman Anik
            </a>{" "}
            · East West University, Dhaka
          </div>
          <div className="flex items-center gap-4">
            <a href={REPO_URL} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 hover:text-[#F7F3EE]">
              <Github className="w-3.5 h-3.5" />
              GitHub
            </a>
            <Link href="/library" className="hover:text-[#F7F3EE]">
              Online Library
            </Link>
            <a href={APK_URL} className="text-[#C6927A] font-semibold hover:underline">
              App APK
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
