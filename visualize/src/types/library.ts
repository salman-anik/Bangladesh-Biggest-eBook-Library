export interface CompactCatalog {
  v: number;
  generated_at: string;
  total: number;
  total_bytes: number;
  covers_count: number;
  authors_count: number;
  drive_roots: Record<string, string>;
  cats: string[];
  subs: string[];
  langs: string[];
  fmts: string[];
  books: [
    string, // 0: drive_file_id
    string, // 1: title
    string, // 2: author
    number, // 3: catIdx
    number, // 4: subIdx
    number, // 5: langIdx
    number, // 6: fmtIdx
    number, // 7: sizeBytes
    string, // 8: coverDriveId
    string, // 9: series
  ][];
}

export interface BookItem {
  id: string;
  title: string;
  author: string;
  cat: string;
  sub: string;
  lang: string;
  fmt: string;
  size: number;
  coverId: string;
  series: string;
  searchBlob: string;
}

export interface LibrarySummary {
  total: number;
  totalBytes: number;
  coversCount: number;
  authorsCount: number;
  cats: string[];
  driveRoots: Record<string, string>;
  generatedAt: string;
}

export function inflateCatalog(data: CompactCatalog): {
  books: BookItem[];
  summary: LibrarySummary;
} {
  const { cats = [], subs = [], langs = [], fmts = [], books = [] } = data;
  const inflated: BookItem[] = books.map((r) => {
    const id = r[0] || "";
    const title = r[1] || "Untitled";
    const author = r[2] || "Unknown";
    const cat = cats[r[3]] || "Other";
    const sub = subs[r[4]] || "";
    const lang = langs[r[5]] || "Unknown";
    const fmt = (fmts[r[6]] || "PDF").toUpperCase();
    const size = Number(r[7]) || 0;
    const coverId = r[8] || "";
    const series = r[9] || "";
    return {
      id,
      title,
      author,
      cat,
      sub,
      lang,
      fmt,
      size,
      coverId,
      series,
      searchBlob: `${title} ${author} ${cat} ${sub} ${series} ${fmt}`.toLowerCase(),
    };
  });

  return {
    books: inflated,
    summary: {
      total: data.total || inflated.length,
      totalBytes: data.total_bytes || 0,
      coversCount: data.covers_count || 0,
      authorsCount: data.authors_count || 0,
      cats: cats.filter((c) => c && c !== "Library Management"),
      driveRoots: data.drive_roots || {},
      generatedAt: data.generated_at || "",
    },
  };
}

export function formatBytes(bytes: number): string {
  const n = Number(bytes) || 0;
  if (n <= 0) return "—";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let v = n;
  for (let i = 0; i < units.length; i++) {
    if (v < 1000 || i === units.length - 1) {
      return `${i <= 1 ? Math.round(v) : v.toFixed(1)} ${units[i]}`;
    }
    v /= 1000;
  }
  return `${n} B`;
}

export function getCoverUrl(book: BookItem, fallback = false): string {
  const isImage = ["JPG", "JPEG", "PNG"].includes(book.fmt.toUpperCase());
  const thumbId = book.coverId || (isImage ? book.id : "");
  if (!thumbId) return "";
  return fallback
    ? `https://lh3.googleusercontent.com/d/${encodeURIComponent(thumbId)}=w400`
    : `https://drive.google.com/thumbnail?id=${encodeURIComponent(thumbId)}&sz=w400`;
}

export function getPreviewUrl(fileId: string): string {
  return `https://drive.google.com/file/d/${encodeURIComponent(fileId)}/preview`;
}

export function getDownloadUrl(fileId: string): string {
  return `https://drive.google.com/uc?export=download&id=${encodeURIComponent(fileId)}`;
}

export function getDriveFolderUrl(folderId: string): string {
  return `https://drive.google.com/drive/folders/${encodeURIComponent(folderId)}`;
}
