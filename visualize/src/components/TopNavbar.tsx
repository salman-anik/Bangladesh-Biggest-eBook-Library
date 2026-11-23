"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Download, Github, Globe, Smartphone } from "lucide-react";

const APK_URL =
  "https://github.com/salman-anik/Bangladesh-Biggest-eBook-Library/raw/main/App/Bangladesh-eBook-Library.apk";
const REPO_URL =
  "https://github.com/salman-anik/Bangladesh-Biggest-eBook-Library";

export function TopNavbar() {
  const pathname = usePathname();
  const isLibrary = pathname?.startsWith("/library");

  return (
    <header className="sticky top-0 z-50 border-b border-[#3D3532]/85 bg-[#11100F]/95 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
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

        <nav className="flex items-center gap-1.5 sm:gap-2">
          <Link
            href="/"
            className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs sm:text-sm font-bold transition ${
              !isLibrary
                ? "bg-[#2D2826] text-[#F7F3EE] border border-[#C6927A]/60"
                : "text-[#9E9590] hover:text-[#F7F3EE] hover:bg-[#1D1A18]"
            }`}
          >
            <Smartphone className="w-4 h-4 text-[#C6927A]" />
            <span className="hidden xs:inline">App</span>
          </Link>

          <Link
            href="/library"
            className={`inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs sm:text-sm font-bold transition ${
              isLibrary
                ? "bg-[#C6927A] text-[#171412]"
                : "bg-[#2D2826] hover:bg-[#3A3330] text-[#F2ECE6] border border-[#3D3532]"
            }`}
          >
            <Globe className={`w-4 h-4 ${isLibrary ? "text-[#171412]" : "text-[#C6927A]"}`} />
            Online Library
          </Link>

          <a
            href={APK_URL}
            className="hidden sm:inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#F2ECE6] hover:bg-white text-[#171412] text-xs sm:text-sm font-extrabold transition"
          >
            <Download className="w-4 h-4" />
            Download APK
          </a>

          <a
            href={REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            aria-label="GitHub Repository"
            className="hidden md:inline-flex items-center justify-center w-9 h-9 rounded-xl bg-[#1D1A18] hover:bg-[#2D2826] border border-[#3D3532] text-[#F2ECE6] transition"
          >
            <Github className="w-4 h-4" />
          </a>
        </nav>
      </div>
    </header>
  );
}
