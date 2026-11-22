# Bangladesh's Biggest eBook Library (বাংলাদেশের বৃহত্তম ই-বুক লাইব্রেরি)

[Google Drive Library](https://drive.google.com/drive/folders/1fMsplDtUnpUhnNBJGKvYQ1sdZx0QVJWq) | [Master Catalog CSV](catalog/master_catalog.csv) | [Master Catalog JSON](catalog/master_catalog.json) | [Authors (3,946)](catalog/AUTHOR_INDEX.md) | [Categories (298)](catalog/CATEGORY_INDEX.md) | [Series (28)](catalog/SERIES_INDEX.md) | [Sources & Licenses](catalog/SOURCES_AND_LICENSES.md)

**18,648 verified unique eBooks** (**262.49 GB**) professionally organized in Bangla and English across **9 clean top-level Drive folders**, with **4,273 Author & Series shortcuts** (zero duplicate physical copies).

## Google Drive Folder Architecture

| Folder | Books | Size | Google Drive |
|---|---:|---:|---|
| `00_Library_Management/` | Management/Quarantine | — | [Open Folder](https://drive.google.com/drive/folders/1GkKPJ4-Xt8dx954uMhfVZkvYpivU7ukv) |
| `01_Bangla_Books/` | 5,906 | 74.72 GB | [Open Folder](https://drive.google.com/drive/folders/12SSwDn9I1QPsFynHYuPVgIbStsL-S8gs) |
| `02_English_Books/` | 1,593 | 34.33 GB | [Open Folder](https://drive.google.com/drive/folders/1T250ptAUwZnv80QxH34qFApKhRZ_s4d9) |
| `03_Education_and_Textbooks/` | 1,622 | 65.46 GB | [Open Folder](https://drive.google.com/drive/folders/1Hoy8Zv0ObmQcGLrDUhmkGSYK_DDSK1BR) |
| `04_Religion_Books/` | 5,672 | 44.98 GB | [Open Folder](https://drive.google.com/drive/folders/1feCztJCCjKkLJJxJhkN7jyGhCMJiz2K8) |
| `05_Authors_and_Scholars/` | 2,773 | 30.32 GB | [Open Folder](https://drive.google.com/drive/folders/1HG9mZ-FGPOydiFc8h32iIDsKYGY-j9DB) |
| `06_Series_and_Collections/` | 502 | 6.94 GB | [Open Folder](https://drive.google.com/drive/folders/1_dHgKueL1AS_EbaXUO-XWCtrgal1JZ8m) |
| `07_Reference_and_Research/` | 334 | 4.17 GB | [Open Folder](https://drive.google.com/drive/folders/1p2RgJYCjE1Z8uvIizVfMgKRYB3BFp57B) |
| `08_Review_and_Unclassified/` | 246 | 1.57 GB | [Open Folder](https://drive.google.com/drive/folders/17xG7eM-GtkED3hWMfT1riucin9fnlI2t) |

## Catalog, Naming & Automation

- **Naming Convention:** `বইয়ের নাম — লেখকের নাম.ext` (Bangla) and `Book Title — Author Name.ext` (English), preserving original language titles and full metadata.
- **Deduplication:** Byte-identical files detected via `md5Checksum`; extras moved safely to `08_Review_and_Unclassified/Exact_Duplicates_Quarantine/` (never permanently deleted).
- **Storage Policy:** Large eBook binaries live exclusively on Google Drive; GitHub stores only catalogs, indexes, automation scripts, and verification reports.
- **Verification Report:** See [verification_report.md](reports/verification_report.md) and [verification_report.json](reports/verification_report.json).