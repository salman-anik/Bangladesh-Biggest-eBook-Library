"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Download, Menu, X } from "lucide-react";

const APK_URL =
  "https://github.com/salman-anik/AnaBook/releases/latest/download/AnaBook.apk";
const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || "";

export function TopNavbar() {
  const pathname = usePathname();
  const isLibrary = pathname?.startsWith("/library");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 bg-white/95 backdrop-blur-md border-b border-neutral-100">
      <div className="max-w-6xl mx-auto px-4 sm:px-8 h-16 sm:h-20 flex items-center justify-between gap-3">
        {/* AnaBook Brand Logo */}
        <Link href="/" className="flex items-center gap-2 group shrink-0">
          <img
            src={`${BASE_PATH}/logo.png`}
            alt="AnaBook Logo"
            className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl object-cover shadow-xs group-hover:scale-105 transition"
          />
          <span className="font-extrabold text-base sm:text-lg tracking-tight text-[#0F1115]">
            AnaBook
          </span>
        </Link>

        {/* Clean Centered Nav Links (Desktop) */}
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

        {/* Right Actions: Mobile Library Pill + Download Button + Hamburger Toggle */}
        <div className="flex items-center gap-2 sm:gap-2.5">
          <Link
            href="/library"
            className="md:hidden inline-flex items-center px-3 py-1.5 rounded-full bg-[#F5F6F8] text-[#0F1115] text-[11px] font-bold"
          >
            Library
          </Link>

          <a
            href={APK_URL}
            className="inline-flex items-center gap-2 pl-3 sm:pl-4 pr-1.5 py-1 sm:py-1.5 rounded-full bg-[#0F1115] hover:bg-neutral-800 text-white text-xs sm:text-sm font-semibold transition shadow-sm"
          >
            <span className="hidden xs:inline">Download</span>
            <span className="xs:hidden">APK</span>
            <span className="w-6 h-6 sm:w-7 sm:h-7 rounded-full bg-[#C6F353] text-[#0F1115] flex items-center justify-center shrink-0">
              <Download className="w-3 h-3 sm:w-3.5 sm:h-3.5 stroke-[2.5]" />
            </span>
          </a>

          {/* Mobile Menu Toggle Button */}
          <button
            type="button"
            onClick={() => setMobileMenuOpen((o) => !o)}
            className="md:hidden w-8 h-8 rounded-full bg-[#F5F6F8] text-[#0F1115] flex items-center justify-center transition hover:bg-neutral-200"
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Mobile Drawer Dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden border-t border-neutral-100 bg-white/98 backdrop-blur-md px-5 py-4 space-y-3 shadow-lg animate-in slide-in-from-top-2 duration-150">
          <Link
            href="/"
            onClick={() => setMobileMenuOpen(false)}
            className={`block py-2 text-sm font-semibold transition ${
              !isLibrary ? "text-[#0F1115]" : "text-[#5F6672]"
            }`}
          >
            Home
          </Link>
          <Link
            href="/library"
            onClick={() => setMobileMenuOpen(false)}
            className={`block py-2 text-sm font-semibold transition ${
              isLibrary ? "text-[#0F1115]" : "text-[#5F6672]"
            }`}
          >
            Online Library (29,178+ Books)
          </Link>
          <Link
            href="/#features"
            onClick={() => setMobileMenuOpen(false)}
            className="block py-2 text-sm font-semibold text-[#5F6672] hover:text-[#0F1115]"
          >
            Features &amp; Reader Themes
          </Link>
          <Link
            href="/#about"
            onClick={() => setMobileMenuOpen(false)}
            className="block py-2 text-sm font-semibold text-[#5F6672] hover:text-[#0F1115]"
          >
            About Developer
          </Link>
        </div>
      )}
    </header>
  );
}
