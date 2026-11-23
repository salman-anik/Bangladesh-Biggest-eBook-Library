import Link from "next/link";
import { ArrowLeft, Download, Smartphone } from "lucide-react";
import { LibraryExplorer } from "@/components/LibraryExplorer";

const APK_URL =
  "https://github.com/salman-anik/Bangladesh-Biggest-eBook-Library/raw/main/App/Bangladesh-eBook-Library.apk";

export default function OnlineLibraryPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <nav className="sticky top-0 z-40 border-b border-slate-800/80 bg-[#090d16]/95 backdrop-blur">
        <div className="max-w-[1480px] mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-200 text-xs font-semibold transition"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              App Home
            </Link>
            <span className="text-sm font-bold text-white hidden sm:inline">
              Online Library Archive
            </span>
          </div>

          <div className="flex items-center gap-2">
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-slate-300 hover:text-white text-xs font-semibold transition"
            >
              <Smartphone className="w-3.5 h-3.5" />
              Android App
            </Link>
            <a
              href={APK_URL}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition"
            >
              <Download className="w-3.5 h-3.5" />
              Download APK
            </a>
          </div>
        </div>
      </nav>
      <LibraryExplorer />
    </div>
  );
}
