"use client";

import React, { useEffect, useMemo, useState } from "react";
import type { ThemeTokens } from "@/lib/anabookTheme";
import { BookItem, getCoverUrl } from "@/types/library";

const CLOTH_PALETTES = [
  "#2B1B17",
  "#172B24",
  "#182338",
  "#2E1A2C",
  "#2E2314",
  "#142A30",
  "#331922",
];

function pickClothBg(book: BookItem): string {
  const seed = `${book.title || ""}|${book.cat || ""}`;
  let hash = 0;
  for (let i = 0; i < seed.length; i++) {
    hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  }
  return CLOTH_PALETTES[hash % CLOTH_PALETTES.length];
}

interface BookCoverProps {
  book: BookItem;
  theme: ThemeTokens;
  isSaved?: boolean;
  showFormatBadge?: boolean;
  compact?: boolean;
  className?: string;
}

/**
 * Web port of AnaBook's cloth-bound hardcover BookCover with spine shading, crease highlight,
 * Drive cover fallback chain, and deterministic 7-palette gold-framed hardcover fallback.
 */
export function BookCover({
  book,
  theme,
  isSaved = false,
  showFormatBadge = false,
  compact = false,
  className = "",
}: BookCoverProps) {
  const [stage, setStage] = useState<"primary" | "fallback" | "none">(
    getCoverUrl(book, false) ? "primary" : "none"
  );

  useEffect(() => {
    setStage(getCoverUrl(book, false) ? "primary" : "none");
  }, [book.id, book.coverId, book.fmt]);

  const src =
    stage === "primary"
      ? getCoverUrl(book, false)
      : stage === "fallback"
        ? getCoverUrl(book, true)
        : "";

  const leafCat = (book.sub || book.cat).split("/").pop() || book.cat;
  const clothBg = useMemo(
    () => pickClothBg(book),
    [book.title, book.cat]
  );

  return (
    <div
      className={`relative overflow-hidden rounded-l-[4px] rounded-r-[10px] border shadow-[0_6px_16px_rgba(0,0,0,0.22)] ${className}`}
      style={{
        backgroundColor: src ? theme.surfaceAlt : clothBg,
        borderColor: src ? theme.border : "rgba(255, 255, 255, 0.16)",
      }}
    >
      {src ? (
        <img
          src={src}
          alt={book.title}
          loading="lazy"
          className="w-full h-full object-cover"
          onError={() =>
            setStage((s) => (s === "primary" ? "fallback" : "none"))
          }
        />
      ) : (
        <div
          className={`w-full h-full flex ${compact ? "p-[3px] pl-[7px]" : "p-1.5 pl-2.5"}`}
          style={{ backgroundColor: clothBg }}
        >
          <div
            className={`flex-1 border border-white/16 rounded-l-[2px] rounded-r-[7px] flex flex-col justify-between text-left ${
              compact ? "px-1.5 py-1.5" : "px-2 py-2.5"
            }`}
          >
            <span
              className={`font-extrabold uppercase tracking-wider line-clamp-1 ${
                compact ? "text-[6.5px]" : "text-[8.5px]"
              }`}
              style={{ color: "#E5C29F" }}
            >
              {leafCat}
            </span>
            <span
              className={`font-bold leading-snug ${
                compact ? "text-[8px] line-clamp-3" : "text-[11px] line-clamp-4"
              }`}
              style={{ color: "#F7F3EE" }}
            >
              {book.title}
            </span>
            <span
              className={`font-semibold line-clamp-1 border-t border-white/16 pt-1 ${
                compact ? "text-[6.5px]" : "text-[9px]"
              }`}
              style={{ color: "rgba(247, 243, 238, 0.75)" }}
            >
              {book.author}
            </span>
          </div>
        </div>
      )}

      {/* Left-edge spine shading & highlight crease */}
      <span
        className="absolute inset-y-0 left-0 w-[5px] bg-black/22 pointer-events-none"
        aria-hidden="true"
      />
      <span
        className="absolute inset-y-0 left-[5px] w-[1.5px] bg-white/22 pointer-events-none"
        aria-hidden="true"
      />

      {showFormatBadge && (
        <span
          className="absolute top-2 left-2.5 px-2 py-0.5 rounded-md text-[9px] font-extrabold tracking-wide uppercase"
          style={{
            backgroundColor: "rgba(17, 16, 15, 0.82)",
            color: "#F7F3EE",
          }}
        >
          {book.fmt}
        </span>
      )}

      {isSaved && (
        <span
          className="absolute top-2 right-2 px-1.5 py-0.5 rounded text-[8px] font-extrabold tracking-wider uppercase"
          style={{
            backgroundColor: theme.sage,
            color: "#F7F3EE",
          }}
        >
          SAVED
        </span>
      )}
    </div>
  );
}
