"use client";

import React, { useState } from "react";
import { ChevronDown, ChevronRight, ExternalLink, Folder, FolderOpen, Home } from "lucide-react";
import {
  cleanCategoryLabel,
  getDriveFolderUrl,
  TaxonomyData,
} from "@/types/library";

interface FolderTreeSidebarProps {
  taxonomy: TaxonomyData;
  activePath: string;
  onSelectPath: (path: string) => void;
  pathCounts: Record<string, number>;
  subfoldersByLeaf: Record<string, { name: string; count: number }[]>;
}

export function FolderTreeSidebar({
  taxonomy,
  activePath,
  onSelectPath,
  pathCounts,
  subfoldersByLeaf,
}: FolderTreeSidebarProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({
    "01_Religion_ধর্ম": true,
    "01_Religion_ধর্ম/Islam_ইসলাম": true,
    "02_Literature_সাহিত্য": true,
  });

  const toggleExpand = (path: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setExpanded((prev) => ({ ...prev, [path]: !prev[path] }));
  };

  const renderLeafItem = (leafPath: string, label: string, depthClass: string) => {
    const subs = subfoldersByLeaf[leafPath] || [];
    const hasSubs = subs.length > 0;
    const isExpanded = !!expanded[leafPath];
    const isActive = activePath === leafPath;
    const count = pathCounts[leafPath] || 0;
    const driveId = taxonomy.folders[leafPath];

    return (
      <div key={leafPath}>
        <div
          className={`group flex items-center justify-between gap-1 rounded-lg px-2 py-1.5 text-xs transition cursor-pointer ${depthClass} ${
            isActive
              ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
              : "text-slate-300 hover:bg-slate-800/70"
          }`}
          onClick={() => {
            onSelectPath(leafPath);
            if (hasSubs) {
              setExpanded((prev) => ({ ...prev, [leafPath]: true }));
            }
          }}
        >
          <div className="flex items-center gap-1.5 min-w-0">
            {hasSubs ? (
              <button
                type="button"
                onClick={(e) => toggleExpand(leafPath, e)}
                className="p-0.5 text-slate-400 hover:text-slate-200 shrink-0"
                aria-label={`Toggle ${label}`}
              >
                {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
              </button>
            ) : (
              <span className="w-4 shrink-0" />
            )}
            {isActive ? (
              <FolderOpen className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            ) : (
              <Folder className="w-3.5 h-3.5 text-amber-400/80 shrink-0" />
            )}
            <span className="truncate" title={cleanCategoryLabel(label)}>
              {cleanCategoryLabel(label)}
            </span>
          </div>
          <div className="flex items-center gap-1 shrink-0">
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 font-medium">
              {count}
            </span>
            {driveId && (
              <a
                href={getDriveFolderUrl(driveId)}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                title="Open folder in Google Drive"
                className="opacity-0 group-hover:opacity-100 p-0.5 text-slate-400 hover:text-emerald-400 transition"
              >
                <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>
        </div>

        {hasSubs && isExpanded && (
          <div className="ml-5 pl-2 border-l border-slate-800 space-y-0.5 mt-0.5">
            {subs.slice(0, 80).map((sub) => {
              const subPath = `${leafPath}/${sub.name}`;
              const subActive = activePath === subPath;
              return (
                <div
                  key={subPath}
                  onClick={() => onSelectPath(subPath)}
                  className={`flex items-center justify-between gap-1.5 rounded-md px-2 py-1 text-[11px] cursor-pointer transition ${
                    subActive
                      ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                      : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
                  }`}
                >
                  <span className="truncate" title={sub.name}>
                    {sub.name}
                  </span>
                  <span className="text-[10px] text-slate-500 shrink-0">{sub.count}</span>
                </div>
              );
            })}
            {subs.length > 80 && (
              <div className="px-2 py-1 text-[10px] text-slate-500">
                +{subs.length - 80} more subfolders in grid view
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  const totalBooks = Object.entries(taxonomy.tree).reduce(
    (sum, [tc]) => sum + (pathCounts[tc] || 0),
    0
  );

  return (
    <aside className="bg-slate-900/80 border border-slate-800 rounded-xl p-3 flex flex-col max-h-[calc(100vh-11rem)] sticky top-4">
      <div className="flex items-center justify-between pb-2.5 mb-2 border-b border-slate-800">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Folder Hierarchy (25)
        </span>
        <a
          href={getDriveFolderUrl(taxonomy.root_drive_id)}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-[11px] text-emerald-400 hover:text-emerald-300"
        >
          Drive Root <ExternalLink className="w-3 h-3" />
        </a>
      </div>

      <button
        type="button"
        onClick={() => onSelectPath("")}
        className={`flex items-center justify-between w-full rounded-lg px-2.5 py-2 text-xs font-semibold mb-1.5 transition ${
          activePath === ""
            ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
            : "text-slate-200 hover:bg-slate-800/70"
        }`}
      >
        <span className="flex items-center gap-2 truncate">
          <Home className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
          <span className="truncate">BANGLA_LIBRARY</span>
        </span>
        <span className="text-[11px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
          {totalBooks.toLocaleString()}
        </span>
      </button>

      <div className="overflow-y-auto space-y-1 pr-1 flex-1">
        {Object.entries(taxonomy.tree).map(([tc, sub]) => {
          const isOpen = !!expanded[tc];
          const isActive = activePath === tc;
          const tcCount = pathCounts[tc] || 0;
          const tcDriveId = taxonomy.folders[tc];

          return (
            <div key={tc} className="space-y-0.5">
              <div
                onClick={() => {
                  onSelectPath(tc);
                  setExpanded((prev) => ({ ...prev, [tc]: !prev[tc] }));
                }}
                className={`group flex items-center justify-between gap-1 rounded-lg px-2 py-1.5 text-xs font-medium cursor-pointer transition ${
                  isActive
                    ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                    : "text-slate-200 hover:bg-slate-800/70"
                }`}
              >
                <div className="flex items-center gap-1.5 min-w-0">
                  <button
                    type="button"
                    onClick={(e) => toggleExpand(tc, e)}
                    className="p-0.5 text-slate-400 hover:text-slate-200 shrink-0"
                    aria-label={`Toggle ${tc}`}
                  >
                    {isOpen ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
                  </button>
                  {isActive ? (
                    <FolderOpen className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                  ) : (
                    <Folder className="w-3.5 h-3.5 text-emerald-400/80 shrink-0" />
                  )}
                  <span className="truncate" title={cleanCategoryLabel(tc)}>
                    {cleanCategoryLabel(tc)}
                  </span>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                    {tcCount.toLocaleString()}
                  </span>
                  {tcDriveId && (
                    <a
                      href={getDriveFolderUrl(tcDriveId)}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      title="Open in Google Drive"
                      className="opacity-0 group-hover:opacity-100 p-0.5 text-slate-400 hover:text-emerald-400"
                    >
                      <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
              </div>

              {isOpen && (
                <div className="ml-3 pl-1.5 border-l border-slate-800 space-y-0.5">
                  {Array.isArray(sub)
                    ? sub.map((lf) => renderLeafItem(`${tc}/${lf}`, lf, ""))
                    : Object.entries(sub).map(([mid, leaves]) => {
                        const midPath = `${tc}/${mid}`;
                        if (leaves.length === 0) {
                          return renderLeafItem(midPath, mid, "");
                        }
                        const midOpen = !!expanded[midPath];
                        const midActive = activePath === midPath;
                        const midCount = pathCounts[midPath] || 0;
                        return (
                          <div key={midPath} className="space-y-0.5">
                            <div
                              onClick={() => {
                                onSelectPath(midPath);
                                setExpanded((prev) => ({ ...prev, [midPath]: !prev[midPath] }));
                              }}
                              className={`group flex items-center justify-between gap-1 rounded-lg px-2 py-1.5 text-xs font-medium cursor-pointer transition ${
                                midActive
                                  ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                                  : "text-slate-200 hover:bg-slate-800/70"
                              }`}
                            >
                              <div className="flex items-center gap-1.5 min-w-0">
                                <button
                                  type="button"
                                  onClick={(e) => toggleExpand(midPath, e)}
                                  className="p-0.5 text-slate-400 hover:text-slate-200 shrink-0"
                                  aria-label={`Toggle ${mid}`}
                                >
                                  {midOpen ? (
                                    <ChevronDown className="w-3.5 h-3.5" />
                                  ) : (
                                    <ChevronRight className="w-3.5 h-3.5" />
                                  )}
                                </button>
                                <Folder className="w-3.5 h-3.5 text-sky-400 shrink-0" />
                                <span className="truncate">{cleanCategoryLabel(mid)}</span>
                              </div>
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                                {midCount.toLocaleString()}
                              </span>
                            </div>
                            {midOpen && (
                              <div className="ml-3 pl-1.5 border-l border-slate-800 space-y-0.5">
                                {leaves.map((lf) => renderLeafItem(`${midPath}/${lf}`, lf, ""))}
                              </div>
                            )}
                          </div>
                        );
                      })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </aside>
  );
}
