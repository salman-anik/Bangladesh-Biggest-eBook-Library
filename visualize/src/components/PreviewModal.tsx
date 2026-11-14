"use client";

import React, { useEffect } from "react";
import { Download, ExternalLink, FolderOpen, X } from "lucide-react";
import {
  BookRecord,
  cleanCategoryLabel,
  formatBytes,
  getDriveDownloadUrl,
  getDriveFolderUrl,
  getDrivePreviewUrl,
  getDriveViewUrl,
} from "@/types/library";

interface PreviewModalProps {
  book: BookRecord | null;
  onClose: () => void;
}

export function PreviewModal({ book, onClose }: PreviewModalProps) {
  useEffect(() => {
    if (!book) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [book, onClose]);

  if (!book) return null;

  const primaryId = book.pdf_file_id || book.epub_file_id || book.text_file_id || book.file_id;

  return (
    <div
      className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-3 sm:p-6"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={`Preview ${book.name}`}
    >
      <div
        className="bg-slate-900 border border-slate-700 rounded-2xl w-full max-w-5xl h-[88vh] flex flex-col overflow-hidden shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-4 py-3 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3">
          <div className="min-w-0 flex-1">
            <h2 className="text-sm sm:text-base font-bold text-white truncate" title={book.name}>
              {book.name}
            </h2>
            <p className="text-xs text-slate-400 truncate mt-0.5">
              {book.author} • {cleanCategoryLabel(book.leaf_path)} • {formatBytes(book.size)}
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2 shrink-0">
            {book.folder_id && (
              <a
                href={getDriveFolderUrl(book.folder_id)}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-amber-300 text-xs font-medium border border-slate-700"
              >
                <FolderOpen className="w-3.5 h-3.5" />
                Book Folder
              </a>
            )}
            {book.text_file_id && (
              <a
                href={getDriveDownloadUrl(book.text_file_id)}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-sky-300 text-xs font-medium border border-slate-700"
              >
                <Download className="w-3.5 h-3.5" />
                Text JSON
              </a>
            )}
            <a
              href={book.link || getDriveViewUrl(primaryId)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700"
            >
              <ExternalLink className="w-3.5 h-3.5 text-emerald-400" />
              Open in Drive
            </a>
            <a
              href={getDriveDownloadUrl(primaryId)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold"
            >
              <Download className="w-3.5 h-3.5" />
              Download
            </a>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700 cursor-pointer"
              aria-label="Close preview"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="flex-1 bg-slate-950 relative">
          <iframe
            src={getDrivePreviewUrl(primaryId)}
            title={book.name}
            className="w-full h-full border-0"
            allow="autoplay"
          />
        </div>
      </div>
    </div>
  );
}
