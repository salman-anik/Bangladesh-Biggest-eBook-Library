"use client";

import React from "react";
import { Building2, Download, ExternalLink, Eye, FileText, FolderOpen, FolderTree, User } from "lucide-react";
import {
  BookRecord,
  cleanCategoryLabel,
  formatBytes,
  getDriveDownloadUrl,
  getDriveFolderUrl,
  getDriveThumbnailUrl,
  getDriveViewUrl,
} from "@/types/library";

interface BookCardProps {
  book: BookRecord;
  onPreview: (book: BookRecord) => void;
  onFilterAuthor: (author: string) => void;
  onFilterPublication: (pub: string) => void;
  onNavigatePath: (path: string) => void;
}

function getFileBadge(name: string, mimeType?: string): string {
  const lower = name.toLowerCase();
  if (lower.endsWith(".pdf") || mimeType === "application/pdf") return "PDF";
  if (lower.endsWith(".epub")) return "EPUB";
  if (lower.endsWith(".json") || mimeType === "application/json") return "JSON";
  if (lower.endsWith(".txt")) return "TXT";
  if (lower.endsWith(".doc") || lower.endsWith(".docx")) return "DOC";
  return "FILE";
}

export function BookCard({
  book,
  onPreview,
  onFilterAuthor,
  onFilterPublication,
  onNavigatePath,
}: BookCardProps) {
  const badges = book.formats && book.formats.length > 0 ? book.formats : [getFileBadge(book.name, book.mimeType)];
  const primaryId = book.pdf_file_id || book.epub_file_id || book.text_file_id || book.file_id;
  const viewUrl = book.folder_id ? getDriveFolderUrl(book.folder_id) : (book.link || getDriveViewUrl(primaryId));
  const downloadUrl = getDriveDownloadUrl(primaryId);
  const coverSrc = book.cover_file_id ? getDriveThumbnailUrl(book.cover_file_id) : (book.cover_url || "");

  return (
    <article className="bg-slate-900/90 border border-slate-800 hover:border-slate-700 rounded-xl p-4 flex flex-col justify-between gap-3 transition">
      <div className="space-y-2.5">
        <div className="flex items-start justify-between gap-2.5">
          {coverSrc && (
            <img
              src={coverSrc}
              alt={book.name}
              loading="lazy"
              onError={(e) => { e.currentTarget.style.display = "none"; }}
              className="w-12 h-16 object-cover rounded-md border border-slate-700/80 bg-slate-950 shrink-0"
            />
          )}
          <div className="min-w-0 flex-1 space-y-1.5">
            <h3 className="text-sm font-semibold text-slate-100 leading-snug break-words">
              {book.name}
            </h3>
            <div className="flex flex-wrap items-center gap-1">
              {badges.map((badge) => (
                <span
                  key={badge}
                  className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide bg-slate-800 text-slate-300 border border-slate-700"
                >
                  <FileText className="w-2.5 h-2.5 text-emerald-400" />
                  {badge}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Category & Subfolder */}
        <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
          <button
            type="button"
            onClick={() => onNavigatePath(book.leaf_path)}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/25 transition max-w-full"
            title={cleanCategoryLabel(book.leaf_path)}
          >
            <FolderTree className="w-3 h-3 shrink-0" />
            <span className="truncate">{cleanCategoryLabel(book.leaf_category)}</span>
          </button>

          {book.subfolder && (
            <button
              type="button"
              onClick={() => onNavigatePath(`${book.leaf_path}/${book.subfolder}`)}
              className="inline-flex items-center px-2 py-0.5 rounded-full bg-sky-500/15 border border-sky-500/30 text-sky-300 hover:bg-sky-500/25 transition truncate max-w-[180px]"
              title={book.subfolder}
            >
              {book.subfolder}
            </button>
          )}
        </div>

        {/* Author & Publication clickable chips */}
        <div className="flex flex-wrap items-center gap-1.5 text-[11px]">
          <button
            type="button"
            onClick={() => onFilterAuthor(book.author)}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-800/90 hover:bg-slate-700 text-slate-300 border border-slate-700/80 transition max-w-full"
            title={`Filter by author: ${book.author}`}
          >
            <User className="w-3 h-3 text-amber-400 shrink-0" />
            <span className="truncate max-w-[170px]">{book.author}</span>
          </button>

          <button
            type="button"
            onClick={() => onFilterPublication(book.publication)}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-800/90 hover:bg-slate-700 text-slate-300 border border-slate-700/80 transition max-w-full"
            title={`Filter by publication: ${book.publication}`}
          >
            <Building2 className="w-3 h-3 text-purple-400 shrink-0" />
            <span className="truncate max-w-[170px]">{book.publication}</span>
          </button>
        </div>
      </div>

      {/* Size & Actions */}
      <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between gap-2 flex-wrap">
        <span className="text-xs font-medium text-slate-400">
          {formatBytes(book.size)}
        </span>

        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => onPreview(book)}
            className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition cursor-pointer"
          >
            <Eye className="w-3.5 h-3.5 text-sky-400" />
            Preview
          </button>

          <a
            href={viewUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition"
          >
            {book.folder_id ? (
              <FolderOpen className="w-3.5 h-3.5 text-amber-400" />
            ) : (
              <ExternalLink className="w-3.5 h-3.5 text-emerald-400" />
            )}
            {book.folder_id ? "Folder" : "Drive"}
          </a>

          <a
            href={downloadUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold transition"
          >
            <Download className="w-3.5 h-3.5" />
            Download
          </a>
        </div>
      </div>
    </article>
  );
}
