"use client";

import type { AuthorDetailRecord } from "@/lib/anabookTheme";
import {
  BookItem,
  CompactCatalog,
  inflateCatalog,
  LibrarySummary,
} from "@/types/library";

export interface LoadedCatalog {
  books: BookItem[];
  summary: LibrarySummary;
}

let catalogPromise: Promise<LoadedCatalog> | null = null;
let cachedCatalog: LoadedCatalog | null = null;

let authorDetailsPromise: Promise<Record<string, AuthorDetailRecord>> | null =
  null;
let cachedAuthorDetails: Record<string, AuthorDetailRecord> | null = null;

/**
 * Loads and inflates books.json once per browser session so navigating between
 * Home, CommandPalette, and Online Library reuses the in-memory 29,178+ catalog.
 */
export function loadCatalogOnce(): Promise<LoadedCatalog> {
  if (cachedCatalog) {
    return Promise.resolve(cachedCatalog);
  }
  if (!catalogPromise) {
    const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";
    catalogPromise = fetch(`${basePath}/books.json`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<CompactCatalog>;
      })
      .then((raw) => {
        const inflated = inflateCatalog(raw);
        cachedCatalog = inflated;
        return inflated;
      })
      .catch((err) => {
        catalogPromise = null;
        throw err;
      });
  }
  return catalogPromise;
}

/**
 * Loads author_details.json once per browser session (non-fatal if unavailable).
 */
export function loadAuthorDetailsOnce(): Promise<
  Record<string, AuthorDetailRecord>
> {
  if (cachedAuthorDetails) {
    return Promise.resolve(cachedAuthorDetails);
  }
  if (!authorDetailsPromise) {
    const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";
    authorDetailsPromise = fetch(`${basePath}/author_details.json`)
      .then((res) => (res.ok ? res.json() : {}))
      .then((data) => {
        const parsed =
          data && typeof data === "object"
            ? (data as Record<string, AuthorDetailRecord>)
            : {};
        cachedAuthorDetails = parsed;
        return parsed;
      })
      .catch(() => ({}));
  }
  return authorDetailsPromise;
}
