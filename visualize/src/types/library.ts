export interface BookRecord {
  source_id?: string;
  file_id: string;
  name: string;
  size: number;
  mimeType?: string;
  top_category: string;
  leaf_path: string;
  leaf_category: string;
  subfolder: string | null;
  author: string;
  publication: string;
  link: string;
}

export type TaxonomyTree = Record<string, string[] | Record<string, string[]>>;

export interface TaxonomyData {
  root_drive_id: string;
  root_drive_name: string;
  folders: Record<string, string>;
  tree: TaxonomyTree;
}

export function formatBytes(bytes: number): string {
  if (!bytes || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  let value = bytes;
  let idx = 0;
  while (value >= 1024 && idx < units.length - 1) {
    value /= 1024;
    idx += 1;
  }
  return idx === 0 ? `${Math.round(value)} B` : `${value.toFixed(1)} ${units[idx]}`;
}

export function cleanCategoryLabel(raw: string): string {
  return raw.replace(/_/g, " ");
}

export function getDriveFolderUrl(folderId?: string): string {
  return `https://drive.google.com/drive/folders/${folderId || "1fMsplDtUnpUhnNBJGKvYQ1sdZx0QVJWq"}`;
}

export function getDriveViewUrl(fileId: string): string {
  return `https://drive.google.com/file/d/${fileId}/view`;
}

export function getDrivePreviewUrl(fileId: string): string {
  return `https://drive.google.com/file/d/${fileId}/preview`;
}

export function getDriveDownloadUrl(fileId: string): string {
  return `https://drive.google.com/uc?export=download&id=${fileId}`;
}
