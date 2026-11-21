# Bangladesh's Biggest eBook Library (বাংলাদেশের বৃহত্তম ই-বুক লাইব্রেরি)

[Google Drive Library](https://drive.google.com/drive/folders/1fMsplDtUnpUhnNBJGKvYQ1sdZx0QVJWq) | [Master Catalog CSV](catalog/master_catalog.csv) | [Master Catalog JSON](catalog/master_catalog.json) | [Master Navigator Sheet](catalog/Bangladesh_eBook_Library_Master_Navigator.xlsx) | [Authors (3,816)](catalog/AUTHOR_INDEX.md) | [Categories (298)](catalog/CATEGORY_INDEX.md) | [Series (26)](catalog/SERIES_INDEX.md) | [Sources & Licenses](catalog/SOURCES_AND_LICENSES.md)

**18,647 verified unique eBooks** (**262.48 GB**) professionally organized in Bangla and English across **9 clean top-level Drive folders**, with **360 live Author folders** and **4,273 shortcuts** (zero duplicate physical copies).

## Library Architecture & Navigators

| Folder | Books | Size | GitHub Navigator | Google Drive |
|---|---:|---:|:---:|:---:|
| `00_Library_Management/` | Management & Catalogs | — | [Browse Section](00_Library_Management/README.md) | [Open in Drive](https://drive.google.com/drive/folders/1GkKPJ4-Xt8dx954uMhfVZkvYpivU7ukv) |
| `01_Bangla_Books/` | 5,906 | 74.72 GB | [Browse Section](01_Bangla_Books/README.md) | [Open in Drive](https://drive.google.com/drive/folders/12SSwDn9I1QPsFynHYuPVgIbStsL-S8gs) |
| `02_English_Books/` | 1,593 | 34.33 GB | [Browse Section](02_English_Books/README.md) | [Open in Drive](https://drive.google.com/drive/folders/1T250ptAUwZnv80QxH34qFApKhRZ_s4d9) |
| `03_Education_and_Textbooks/` | 1,622 | 65.46 GB | [Browse Section](03_Education_and_Textbooks/README.md) | [Open in Drive](https://drive.google.com/drive/folders/1Hoy8Zv0ObmQcGLrDUhmkGSYK_DDSK1BR) |
| `04_Religion_Books/` | 5,671 | 44.98 GB | [Browse Section](04_Religion_Books/README.md) | [Open in Drive](https://drive.google.com/drive/folders/1feCztJCCjKkLJJxJhkN7jyGhCMJiz2K8) |
| `05_Authors_and_Scholars/` | 2,773 (360 Authors) | 30.32 GB | [Browse Section](05_Authors_and_Scholars/README.md) | [Open in Drive](https://drive.google.com/drive/folders/1HG9mZ-FGPOydiFc8h32iIDsKYGY-j9DB) |
| `06_Series_and_Collections/` | 502 (18 Series) | 6.94 GB | [Browse Section](06_Series_and_Collections/README.md) | [Open in Drive](https://drive.google.com/drive/folders/1_dHgKueL1AS_EbaXUO-XWCtrgal1JZ8m) |
| `07_Reference_and_Research/` | 334 | 4.17 GB | [Browse Section](07_Reference_and_Research/README.md) | [Open in Drive](https://drive.google.com/drive/folders/1p2RgJYCjE1Z8uvIizVfMgKRYB3BFp57B) |
| `08_Review_and_Unclassified/` | 246 | 1.57 GB | [Browse Section](08_Review_and_Unclassified/README.md) | [Open in Drive](https://drive.google.com/drive/folders/17xG7eM-GtkED3hWMfT1riucin9fnlI2t) |

## Catalog, Naming & Automation

- **Master Catalog Sort Order:** `catalog/master_catalog.csv`, `catalog/master_catalog.json`, and the **All Books** sheet of `catalog/Bangladesh_eBook_Library_Master_Navigator.xlsx` are sorted ascending by book title.
- **Religion Books Organization:** `04_Religion_Books/` organizes `Islamic_Books`, `Hinduism_Books`, `Christianity_Books`, `Buddhism_Books`, and `Comparative_and_Other_Religions`.
- **Deduplication:** Byte-identical / normalized duplicate files are quarantined under `08_Review_and_Unclassified/Exact_Duplicates_Quarantine/` (never permanently deleted).
- **Storage Policy:** Large eBook binaries live exclusively on Google Drive; GitHub stores catalogs, markdown navigators, automation scripts, and reports.
