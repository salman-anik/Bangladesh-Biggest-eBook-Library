"use client";

import React from "react";
import { ChevronRight, ExternalLink, Folder, FolderOpen, Home } from "lucide-react";
import {
  cleanCategoryLabel,
  formatBytes,
  getDriveFolderUrl,
  TaxonomyData,
} from "@/types/library";

export interface FolderCardNode {
  path: string;
  label: string;
  count: number;
  size: number;
  driveId?: string;
}

interface FolderBrowserGridProps {
  taxonomy: TaxonomyData;
  activePath: string;
  onSelectPath: (path: string) => void;
  pathCounts: Record<string, number>;
  pathSizes: Record<string, number>;
  subfoldersByLeaf: Record<string, { name: string; count: number; size: number }[]>;
}

export function FolderBrowserGrid({
  taxonomy,
  activePath,
  onSelectPath,
  pathCounts,
  pathSizes,
  subfoldersByLeaf,
}: FolderBrowserGridProps) {
  const segments = activePath ? activePath.split("/") : [];

  const getChildNodes = (): FolderCardNode[] => {
    if (!activePath) {
      return Object.keys(taxonomy.tree).map((tc) => ({
        path: tc,
        label: tc,
        count: pathCounts[tc] || 0,
        size: pathSizes[tc] || 0,
        driveId: taxonomy.folders[tc],
      }));
    }

    const parts = activePath.split("/");
    const tc = parts[0];
    const tcEntry = taxonomy.tree[tc];
    if (!tcEntry) return [];

    if (parts.length === 1) {
      if (Array.isArray(tcEntry)) {
        return tcEntry.map((lf) => {
          const p = `${tc}/${lf}`;
          return {
            path: p,
            label: lf,
            count: pathCounts[p] || 0,
            size: pathSizes[p] || 0,
            driveId: taxonomy.folders[p],
          };
        });
      }
      return Object.keys(tcEntry).map((mid) => {
        const p = `${tc}/${mid}`;
        return {
          path: p,
          label: mid,
          count: pathCounts[p] || 0,
          size: pathSizes[p] || 0,
          driveId: taxonomy.folders[p],
        };
      });
    }

    if (parts.length === 2 && !Array.isArray(tcEntry)) {
      const mid = parts[1];
      const leaves = tcEntry[mid];
      if (leaves && leaves.length > 0) {
        return leaves.map((lf) => {
          const p = `${activePath}/${lf}`;
          return {
            path: p,
            label: lf,
            count: pathCounts[p] || 0,
            size: pathSizes[p] || 0,
            driveId: taxonomy.folders[p],
          };
        });
      }
    }

    // Check subfolders of leaf category
    const subs = subfoldersByLeaf[activePath] || [];
    return subs.map((s) => {
      const p = `${activePath}/${s.name}`;
      return {
        path: p,
        label: s.name,
        count: s.count,
        size: s.size,
        driveId: taxonomy.folders[p],
      };
    });
  };

  const childNodes = getChildNodes();
  const currentDriveId = activePath
    ? taxonomy.folders[activePath] || taxonomy.root_drive_id
    : taxonomy.root_drive_id;
  const activeCount = activePath
    ? pathCounts[activePath] || 0
    : Object.keys(taxonomy.tree).reduce((acc, tc) => acc + (pathCounts[tc] || 0), 0);

  return (
    <section className="space-y-3">
      {/* Breadcrumb + Open Current Folder in Drive */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-xl px-4 py-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-1.5 text-sm">
          <button
            type="button"
            onClick={() => onSelectPath("")}
            className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md font-semibold transition ${
              activePath === ""
                ? "text-emerald-300 bg-emerald-500/15"
                : "text-slate-300 hover:bg-slate-800 hover:text-white"
            }`}
          >
            <Home className="w-3.5 h-3.5 text-emerald-400" />
            Bangladesh-Biggest-eBook-Library
          </button>
          {segments.map((seg, idx) => {
            const segPath = segments.slice(0, idx + 1).join("/");
            const isLast = idx === segments.length - 1;
            return (
              <React.Fragment key={segPath}>
                <ChevronRight className="w-4 h-4 text-slate-600" />
                <button
                  type="button"
                  onClick={() => onSelectPath(segPath)}
                  className={`px-2 py-1 rounded-md font-medium transition ${
                    isLast
                      ? "text-emerald-300 bg-emerald-500/15 border border-emerald-500/30"
                      : "text-slate-300 hover:bg-slate-800 hover:text-white"
                  }`}
                >
                  {cleanCategoryLabel(seg)}
                </button>
              </React.Fragment>
            );
          })}
          <span className="ml-2 text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-medium">
            {activeCount.toLocaleString()} books
          </span>
        </div>

        <a
          href={getDriveFolderUrl(currentDriveId)}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-600/20 hover:bg-emerald-600/30 border border-emerald-500/40 text-emerald-300 text-xs font-semibold transition"
        >
          <FolderOpen className="w-3.5 h-3.5" />
          Open Current Folder in Drive
          <ExternalLink className="w-3 h-3" />
        </a>
      </div>

      {/* Child Folder Visualizer Cards */}
      {childNodes.length > 0 && (
        <div className="bg-slate-900/50 border border-slate-800/80 rounded-xl p-3">
          <div className="flex items-center justify-between mb-2.5 px-1">
            <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              {activePath ? "Subfolders inside this category" : "All 25 Library Categories"} ({childNodes.length})
            </h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-2.5 max-h-72 overflow-y-auto pr-1">
            {childNodes.map((node) => (
              <div
                key={node.path}
                onClick={() => onSelectPath(node.path)}
                className="group bg-slate-900/90 hover:bg-slate-800/90 border border-slate-800 hover:border-emerald-500/50 rounded-lg p-3 cursor-pointer transition flex flex-col justify-between gap-2"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <Folder className="w-4 h-4 text-amber-400 shrink-0" />
                    <span
                      className="text-xs font-semibold text-slate-100 group-hover:text-emerald-300 truncate"
                      title={cleanCategoryLabel(node.label)}
                    >
                      {cleanCategoryLabel(node.label)}
                    </span>
                  </div>
                  {node.driveId && (
                    <a
                      href={getDriveFolderUrl(node.driveId)}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      title="Open in Google Drive"
                      className="text-slate-500 hover:text-emerald-400 shrink-0"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  )}
                </div>
                <div className="flex items-center justify-between text-[11px] text-slate-400">
                  <span className="font-medium text-emerald-400/90">
                    {node.count.toLocaleString()} books
                  </span>
                  <span>{formatBytes(node.size)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
