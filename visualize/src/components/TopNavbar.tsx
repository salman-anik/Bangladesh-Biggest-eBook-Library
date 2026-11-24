"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Download, Menu, Moon, Search, Sun, X } from "lucide-react";
import { useWebTheme } from "@/context/WebThemeContext";

const APK_URL =
  "https://github.com/salman-anik/AnaBook/releases/latest/download/AnaBook.apk";
const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH || "";

export function TopNavbar() {
  const pathname = usePathname();
  const isLibrary = pathname?.startsWith("/library");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { theme, themeMode, toggleThemeMode, setCommandOpen, hydrated } =
    useWebTheme();

  const useThemedChrome = hydrated && (isLibrary || themeMode === "dark");

  return (
    <header
      className="sticky top-0 z-50 backdrop-blur-md border-b transition-colors duration-200"
      style={
        useThemedChrome
          ? {
              backgroundColor: `${theme.surface}F2`,
              borderColor: theme.border,
              color: theme.ink,
            }
          : {
              backgroundColor: "rgba(255, 255, 255, 0.95)",
              borderColor: "#F5F5F5",
              color: "#0F1115",
            }
      }
    >
      <div className="max-w-6xl mx-auto px-4 sm:px-8 h-16 sm:h-20 flex items-center justify-between gap-3">
        {/* AnaBook Brand Logo */}
        <Link href="/" className="flex items-center gap-2 group shrink-0">
          <img
            src={`${BASE_PATH}/logo.png`}
            alt="AnaBook Logo"
            className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl object-cover shadow-xs group-hover:scale-105 transition"
          />
          <span className="font-extrabold text-base sm:text-lg tracking-tight">
            AnaBook
          </span>
        </Link>

        {/* Clean Centered Nav Links (Desktop) */}
        <nav
          className="hidden md:flex items-center gap-7 text-sm font-medium"
          style={{ color: useThemedChrome ? theme.muted : "#5F6672" }}
        >
          <Link
            href="/"
            className="transition hover:opacity-100"
            style={
              !isLibrary
                ? {
                    color: useThemedChrome ? theme.ink : "#0F1115",
                    fontWeight: 700,
                  }
                : undefined
            }
          >
            Home
          </Link>
          <Link
            href="/library"
            className="transition hover:opacity-100"
            style={
              isLibrary
                ? {
                    color: useThemedChrome ? theme.ink : "#0F1115",
                    fontWeight: 700,
                  }
                : undefined
            }
          >
            Online Library
          </Link>
          <Link href="/#features" className="transition hover:opacity-80">
            Features
          </Link>
          <Link href="/#about" className="transition hover:opacity-80">
            About
          </Link>
        </nav>

        {/* Right Actions: Command Search + Theme Mode + Mobile Library + APK + Hamburger */}
        <div className="flex items-center gap-2 sm:gap-2.5">
          {/* Desktop Ctrl+K Search Trigger */}
          <button
            type="button"
            onClick={() => setCommandOpen(true)}
            aria-label="Open quick search (Ctrl+K)"
            className="hidden sm:inline-flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-semibold transition hover:opacity-85 cursor-pointer"
            style={
              useThemedChrome
                ? {
                    backgroundColor: theme.surfaceAlt,
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
            <Search className="w-3.5 h-3.5" />
            <span>Search…</span>
            <kbd
              className="px-1.5 py-0.5 rounded border text-[10px] font-bold"
              style={
                useThemedChrome
                  ? {
                      backgroundColor: theme.surface,
                      borderColor: theme.border,
                      color: theme.ink,
                    }
                  : {
                      backgroundColor: "#FFFFFF",
                      borderColor: "#E5E7EB",
                      color: "#0F1115",
                    }
              }
            >
              ⌘K
            </kbd>
          </button>

          {/* Mobile Search Icon Button */}
          <button
            type="button"
            onClick={() => setCommandOpen(true)}
            aria-label="Open quick search"
            className="sm:hidden w-8 h-8 rounded-full flex items-center justify-center border transition"
            style={
              useThemedChrome
                ? {
                    backgroundColor: theme.surfaceAlt,
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
            <Search className="w-3.5 h-3.5" />
          </button>

          {/* Quick Light/Dark Toggle */}
          <button
            type="button"
            onClick={toggleThemeMode}
            title={
              themeMode === "light"
                ? "Switch to Dark Mode"
                : "Switch to Light Mode"
            }
            aria-label={
              themeMode === "light"
                ? "Switch to Dark Mode"
                : "Switch to Light Mode"
            }
            className="hidden xs:inline-flex w-8 h-8 rounded-full border items-center justify-center transition hover:opacity-85 cursor-pointer"
            style={
              useThemedChrome
                ? {
                    backgroundColor: theme.surfaceAlt,
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
            {themeMode === "light" ? (
              <Moon className="w-3.5 h-3.5" />
            ) : (
              <Sun className="w-3.5 h-3.5" />
            )}
          </button>

          <Link
            href="/library"
            className="md:hidden inline-flex items-center px-3 py-1.5 rounded-full text-[11px] font-bold"
            style={
              useThemedChrome
                ? {
                    backgroundColor: theme.surfaceAlt,
                    color: theme.ink,
                  }
                : {
                    backgroundColor: "#F5F6F8",
                    color: "#0F1115",
                  }
            }
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
            className="md:hidden w-8 h-8 rounded-full flex items-center justify-center transition"
            style={
              useThemedChrome
                ? {
                    backgroundColor: theme.surfaceAlt,
                    color: theme.ink,
                  }
                : {
                    backgroundColor: "#F5F6F8",
                    color: "#0F1115",
                  }
            }
            aria-label="Toggle navigation menu"
          >
            {mobileMenuOpen ? (
              <X className="w-4 h-4" />
            ) : (
              <Menu className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>

      {/* Mobile Drawer Dropdown */}
      {mobileMenuOpen && (
        <div
          className="md:hidden border-t backdrop-blur-md px-5 py-4 space-y-3 shadow-lg"
          style={
            useThemedChrome
              ? {
                  backgroundColor: theme.surface,
                  borderColor: theme.border,
                  color: theme.ink,
                }
              : {
                  backgroundColor: "rgba(255,255,255,0.98)",
                  borderColor: "#F5F5F5",
                  color: "#0F1115",
                }
          }
        >
          <Link
            href="/"
            onClick={() => setMobileMenuOpen(false)}
            className="block py-2 text-sm font-semibold"
          >
            Home
          </Link>
          <Link
            href="/library"
            onClick={() => setMobileMenuOpen(false)}
            className="block py-2 text-sm font-semibold"
          >
            Online Library (29,178+ Books)
          </Link>
          <Link
            href="/#features"
            onClick={() => setMobileMenuOpen(false)}
            className="block py-2 text-sm font-semibold opacity-80"
          >
            Features &amp; Reader Themes
          </Link>
          <Link
            href="/#about"
            onClick={() => setMobileMenuOpen(false)}
            className="block py-2 text-sm font-semibold opacity-80"
          >
            About Developer
          </Link>
        </div>
      )}
    </header>
  );
}
