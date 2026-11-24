"use client";

import React, { useEffect } from "react";
import { Globe, X } from "lucide-react";
import type { ThemeTokens } from "@/lib/anabookTheme";
import { AuthorAvatar } from "./AuthorAvatar";

interface AuthorDetailModalProps {
  visible: boolean;
  authorName: string;
  group: string;
  bookCount: number;
  subfolderCount: number;
  shortDesc?: string;
  bio?: string;
  wikiUrl?: string;
  theme: ThemeTokens;
  onClose: () => void;
}

/**
 * Web port of AnaBook's AuthorDetailModal featuring archival portrait,
 * group/book/section badges, biography card, and Wikipedia link.
 */
export function AuthorDetailModal({
  visible,
  authorName,
  group,
  bookCount,
  subfolderCount,
  shortDesc,
  bio,
  wikiUrl,
  theme,
  onClose,
}: AuthorDetailModalProps) {
  useEffect(() => {
    if (!visible) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [visible, onClose]);

  if (!visible) return null;

  const displayBio =
    bio?.trim() ||
    `${authorName} is featured in Bangladesh's Biggest eBook Library under ${
      group || "Authors & Scholars"
    }, with ${bookCount.toLocaleString()} digitized ${
      bookCount === 1 ? "book" : "books"
    } preserved for online reading and offline download.`;

  return (
    <div
      className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={`Author biography: ${authorName}`}
    >
      <div
        className="w-full max-w-lg max-h-[88vh] rounded-3xl border p-5 sm:p-6 flex flex-col gap-4 shadow-2xl overflow-hidden"
        style={{
          backgroundColor: theme.surface,
          borderColor: theme.border,
          color: theme.ink,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between">
          <span
            className="text-[11px] font-extrabold uppercase tracking-[0.09em]"
            style={{ color: theme.accent }}
          >
            Author Biography
          </span>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close author details"
            className="w-8 h-8 rounded-full border flex items-center justify-center transition hover:opacity-80 cursor-pointer"
            style={{
              backgroundColor: theme.surfaceAlt,
              borderColor: theme.border,
              color: theme.ink,
            }}
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="overflow-y-auto space-y-4 pr-1">
          <div className="flex flex-col items-center text-center gap-2.5">
            <AuthorAvatar name={authorName} size={88} theme={theme} />
            <h3 className="text-lg sm:text-xl font-extrabold">{authorName}</h3>
            {shortDesc ? (
              <p
                className="text-xs sm:text-sm font-semibold"
                style={{ color: theme.cream }}
              >
                {shortDesc}
              </p>
            ) : null}

            <div className="flex flex-wrap items-center justify-center gap-2 pt-1">
              {group ? (
                <span
                  className="px-3 py-1 rounded-full border text-xs font-bold"
                  style={{
                    backgroundColor: theme.accentSoft,
                    borderColor: theme.accent,
                    color: theme.accent,
                  }}
                >
                  {group}
                </span>
              ) : null}
              <span
                className="px-3 py-1 rounded-full border text-xs font-bold"
                style={{
                  backgroundColor: theme.surfaceAlt,
                  borderColor: theme.border,
                  color: theme.ink,
                }}
              >
                {bookCount.toLocaleString()} {bookCount === 1 ? "Book" : "Books"}
              </span>
              {subfolderCount > 0 ? (
                <span
                  className="px-3 py-1 rounded-full border text-xs font-bold"
                  style={{
                    backgroundColor: theme.surfaceAlt,
                    borderColor: theme.border,
                    color: theme.ink,
                  }}
                >
                  {subfolderCount}{" "}
                  {subfolderCount === 1 ? "Section" : "Sections"}
                </span>
              ) : null}
            </div>
          </div>

          <div
            className="rounded-2xl border p-4 space-y-1.5"
            style={{
              backgroundColor: theme.surfaceAlt,
              borderColor: theme.borderSubtle,
            }}
          >
            <p
              className="text-[10px] font-extrabold uppercase tracking-[0.08em]"
              style={{ color: theme.muted }}
            >
              About the Author
            </p>
            <p
              className="text-xs sm:text-sm leading-relaxed"
              style={{ color: theme.ink }}
            >
              {displayBio}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5 pt-1">
          {wikiUrl ? (
            <a
              href={wikiUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-[1.4] inline-flex items-center justify-center gap-2 py-2.5 px-4 rounded-2xl text-xs sm:text-sm font-extrabold transition hover:opacity-90"
              style={{
                backgroundColor: theme.accent,
                color: theme.creamInk,
              }}
            >
              <Globe className="w-4 h-4" />
              <span>Read on Wikipedia</span>
            </a>
          ) : null}

          <button
            type="button"
            onClick={onClose}
            className={`py-2.5 px-4 rounded-2xl border text-xs sm:text-sm font-bold transition hover:opacity-85 cursor-pointer ${
              wikiUrl ? "flex-[0.7]" : "flex-1"
            }`}
            style={{
              backgroundColor: theme.surfaceAlt,
              borderColor: theme.border,
              color: theme.ink,
            }}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
