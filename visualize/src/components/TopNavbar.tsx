"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Download } from "lucide-react";

const APK_URL =
  "https://github.com/salman-anik/Bangladesh-Biggest-eBook-Library/raw/main/App/Bangladesh-eBook-Library.apk";
const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || "";

export function TopNavbar() {
  const pathname = usePathname();
  const isLibrary = pathname?.startsWith("/library");

  return (
    <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b border-neutral-100">
      <div className="max-w-6xl mx-auto px-5 sm:px-8 h-20 flex items-center justify-between gap-4">
        {/* AnaBook Brand Logo */}
        <Link href="/" className="flex items-center gap-2.5 group">
          <img
            src={`${BASE_PATH}/logo.png`}
            alt="AnaBook Logo"
            className="w-9 h-9 rounded-xl object-cover shadow-xs group-hover:scale-105 transition"
          />
          <span className="font-extrabold text-lg tracking-tight text-[#0F1115]">
            AnaBook
          </span>
        </Link>

        {/* Clean Centered Nav Links */}
        <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-[#5F6672]">
          <Link
            href="/"
            className={`transition hover:text-[#0F1115] ${!isLibrary ? "text-[#0F1115] font-semibold" : ""}`}
          >
            Home
          </Link>
          <Link
            href="/library"
            className={`transition hover:text-[#0F1115] ${isLibrary ? "text-[#0F1115] font-semibold" : ""}`}
          >
            Online Library
          </Link>
          <Link href="/#features" className="transition hover:text-[#0F1115]">
            Features
          </Link>
          <Link href="/#about" className="transition hover:text-[#0F1115]">
            About
          </Link>
        </nav>

        {/* Right Actions: Online Library (mobile) + Signature Black Pill with Lime Icon */}
        <div className="flex items-center gap-2.5">
          <Link
            href="/library"
            className="md:hidden inline-flex items-center px-3.5 py-2 rounded-full bg-[#F5F6F8] text-[#0F1115] text-xs font-bold"
          >
            Online Library
          </Link>

          <a
            href={APK_URL}
            className="inline-flex items-center gap-2.5 pl-4 pr-1.5 py-1.5 rounded-full bg-[#0F1115] hover:bg-neutral-800 text-white text-xs sm:text-sm font-semibold transition shadow-sm"
          >
            <span>Download Now</span>
            <span className="w-7 h-7 rounded-full bg-[#C6F353] text-[#0F1115] flex items-center justify-center">
              <Download className="w-3.5 h-3.5 stroke-[2.5]" />
            </span>
          </a>
        </div>
      </div>
    </header>
  );
}
