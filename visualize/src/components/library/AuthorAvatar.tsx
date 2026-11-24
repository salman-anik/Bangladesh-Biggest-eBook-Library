"use client";

import React, { useEffect, useMemo, useState } from "react";
import authorPhotosRaw from "../../../public/author_photos.json";
import type { ThemeTokens } from "@/lib/anabookTheme";

const AUTHOR_PHOTOS = authorPhotosRaw as Record<string, string>;

const ARCHIVAL_PALETTES = [
  { bg: "#3E2723", ring: "#C6927A", text: "#F7E7DC" },
  { bg: "#1F3A30", ring: "#86B8A3", text: "#E7F5EF" },
  { bg: "#1E2942", ring: "#88A9E6", text: "#EBF1FC" },
  { bg: "#4A1F2B", ring: "#D98A9C", text: "#FCEEF2" },
  { bg: "#5A2D21", ring: "#E59D85", text: "#FCEEE9" },
  { bg: "#19353C", ring: "#7BC4D4", text: "#E7F6F8" },
];

const HONORIFIC_PREFIXES = new Set([
  "ড.",
  "ড",
  "অধ্যাপক",
  "মাওলানা",
  "আল্লামা",
  "মুফতি",
  "dr.",
  "dr",
  "prof.",
  "prof",
  "md.",
  "md",
  "mr.",
  "mr",
  "mrs.",
  "mrs",
  "ms.",
  "ms",
]);

export function getAuthorPhotoId(name: string): string | null {
  const key = (name || "").trim().toLowerCase();
  if (!key) return null;
  if (AUTHOR_PHOTOS[key]) return AUTHOR_PHOTOS[key];
  const firstSegment = key.split(/[,&|/]/)[0].trim();
  if (firstSegment && AUTHOR_PHOTOS[firstSegment])
    return AUTHOR_PHOTOS[firstSegment];
  return null;
}

function getDriveAvatarUrl(id: string, fallback = false): string {
  if (id.startsWith("http://") || id.startsWith("https://")) {
    return id;
  }
  return fallback
    ? `https://lh3.googleusercontent.com/d/${encodeURIComponent(id)}=w240`
    : `https://drive.google.com/thumbnail?id=${encodeURIComponent(id)}&sz=w240`;
}

function pickPaletteIndex(name: string): number {
  const s = name || "author";
  let hash = 0;
  for (let i = 0; i < s.length; i++) {
    hash = (hash * 31 + s.charCodeAt(i)) >>> 0;
  }
  return hash % ARCHIVAL_PALETTES.length;
}

export function getAuthorInitials(name: string): string {
  const cleaned = (name || "").replace(/\(.*?\)/g, " ").trim();
  const rawWords = cleaned.split(/\s+/).filter(Boolean);
  const words = rawWords.filter(
    (w) => !HONORIFIC_PREFIXES.has(w.toLowerCase())
  );
  const target = words.length > 0 ? words : rawWords;
  if (target.length === 0) return "?";

  const chars = target
    .slice(0, 2)
    .map((w) => {
      const ch = Array.from(w)[0] || "";
      return /[a-z]/i.test(ch) ? ch.toUpperCase() : ch;
    })
    .filter(Boolean);

  return chars.join("") || "?";
}

interface AuthorAvatarProps {
  name: string;
  size?: number;
  theme: ThemeTokens;
}

/**
 * Circular portrait avatar matching AnaBook's AuthorAvatar with 131+ Drive author photos
 * and concentric SVG archival monogram fallback.
 */
export function AuthorAvatar({ name, size = 40, theme }: AuthorAvatarProps) {
  const photoId = getAuthorPhotoId(name);
  const [stage, setStage] = useState<"primary" | "fallback" | "avatar">(
    photoId ? "primary" : "avatar"
  );

  useEffect(() => {
    setStage(photoId ? "primary" : "avatar");
  }, [name, photoId]);

  const palette = useMemo(
    () => ARCHIVAL_PALETTES[pickPaletteIndex(name)],
    [name]
  );
  const initials = useMemo(() => getAuthorInitials(name), [name]);
  const fontSize = Math.max(
    11,
    Math.round(size * (initials.length > 1 ? 0.34 : 0.4))
  );

  const src =
    photoId && stage === "primary"
      ? getDriveAvatarUrl(photoId, false)
      : photoId && stage === "fallback"
        ? getDriveAvatarUrl(photoId, true)
        : "";

  return (
    <span
      className="relative inline-flex items-center justify-center rounded-full overflow-hidden border-[1.5px] shrink-0 select-none"
      style={{
        width: size,
        height: size,
        borderColor: theme.border,
        backgroundColor: palette.bg,
      }}
    >
      <svg
        width={size}
        height={size}
        viewBox="0 0 80 80"
        className="absolute inset-0"
        aria-hidden="true"
      >
        <circle
          cx="40"
          cy="40"
          r="35"
          fill="none"
          stroke={palette.ring}
          strokeWidth={1.6}
          opacity={0.55}
        />
        <circle cx="40" cy="40" r="29" fill={palette.ring} opacity={0.12} />
      </svg>

      <span
        className="relative font-extrabold tracking-wide"
        style={{ color: palette.text, fontSize }}
      >
        {initials}
      </span>

      {src ? (
        <img
          src={src}
          alt={name}
          loading="lazy"
          className="absolute inset-0 w-full h-full object-cover"
          onError={() => {
            if (stage === "primary" && !(photoId || "").startsWith("http")) {
              setStage("fallback");
            } else {
              setStage("avatar");
            }
          }}
        />
      ) : null}
    </span>
  );
}
