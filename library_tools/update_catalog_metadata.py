"""Update master catalog and indexes after author consolidation."""
import csv
import json
import re
from pathlib import Path
from collections import defaultdict

BN_DIGITS = {'০':'0', '১':'1', '২':'2', '৩':'3', '৪':'4', '৫':'5', '৬':'6', '৭':'7', '৮':'8', '৯':'9'}
def bn_to_en(s: str) -> str:
    for b, e in BN_DIGITS.items():
        s = s.replace(b, e)
    return s

def extract_year(s: str) -> str:
    s_en = bn_to_en(s)
    m = re.search(r'\[(1[89]\d{2}|20\d{2})\]|\((1[89]\d{2}|20\d{2})\)|\b(1[89]\d{2}|20\d{2})\b', s_en)
    if m:
        return m.group(1) or m.group(2) or m.group(3)
    return ""

def main():
    repo_dir = Path(r'C:\Users\USER\.gemini\antigravity\scratch\Bangladesh-Biggest-eBook-Library')
    cat_json_path = repo_dir / 'catalog' / 'master_catalog.json'
    cat_csv_path = repo_dir / 'catalog' / 'master_catalog.csv'
    author_index_path = repo_dir / 'catalog' / 'AUTHOR_INDEX.md'

    with open(cat_json_path, 'r', encoding='utf-8') as f:
        catalog = json.load(f)

    print(f"Updating metadata for {len(catalog)} books...")

    # Canonical author mapping
    author_map = {
        'Ariph Ajad': 'আরিফ আজাদ',
        'Arif Azad': 'আরিফ আজাদ',
        'Qazi Anowar Hussain': 'কাজী আনোয়ার হোসেন',
        'Ahmadullah': 'শায়খ আহমাদুল্লাহ',
        'সাইয়্যেদ আবুল আলা মওদুদী': 'সাইয়েদ আবুল আলা মওদুদী',
        'আব্দুল হামীদ ফাইযী মাদানী': 'আব্দুল হামীদ ফাইযী',
        'গোপাল হালদার সম্পাদিত': 'গোপাল হালদার',
        'Choturth Khondo': 'তারাশঙ্কর বন্দ্যোপাধ্যায়',
        'Dwitij Khondo': 'তারাশঙ্কর বন্দ্যোপাধ্যায়',
        'Prothom Khondo': 'তারাশঙ্কর বন্দ্যোপাধ্যায়',
        'Tritij Khondo': 'তারাশঙ্কর বন্দ্যোপাধ্যায়',
        '১ম খন্ড': 'আল্লামা দেলাওয়ার হোসাইন সাঈদী',
        '২য় খন্ড': 'আল্লামা দেলাওয়ার হোসাইন সাঈদী',
        '৩য় খন্ড': 'মুহাম্মদ আব্দুল মা‘বুদ',
        '৪র্থ খন্ড': 'মুহাম্মদ আব্দুল মা‘বুদ',
        '৫ম খন্ড': 'মুহাম্মদ আব্দুল মা‘বুদ',
        '৬ষ্ঠ খন্ড': 'মুহাম্মদ আব্দুল মা‘বুদ',
        'অষ্টম খণ্ড': 'গজেন্দ্রকুমার মিত্র',
        'একাদশ খণ্ড': 'গজেন্দ্রকুমার মিত্র',
        'দশম খণ্ড': 'গজেন্দ্রকুমার মিত্র',
        'নবম খণ্ড': 'গজেন্দ্রকুমার মিত্র',
        'পঞ্চম খণ্ড': 'গজেন্দ্রকুমার মিত্র',
        'ষষ্ঠ খণ্ড': 'গজেন্দ্রকুমার মিত্র',
        'সপ্তম খণ্ড': 'গজেন্দ্রকুমার মিত্র',
    }

    # Title specific author overrides for multipart books
    title_author_overrides = [
        (r'গজেন্দ্রকুমার মিত্র রচনাবলী', 'গজেন্দ্রকুমার মিত্র'),
        (r'তারাশঙ্কর-রচনাবলী', 'তারাশঙ্কর বন্দ্যোপাধ্যায়'),
        (r'বিভূতি-রচনাবলী', 'বিভূতিভূষণ বন্দ্যোপাধ্যায়'),
        (r'বিদ্যাসাগরের গ্রন্থাবলী', 'ঈশ্বরচন্দ্র বিদ্যাসাগর'),
        (r'মাও সে তুং', 'মাও সেতুং'),
        (r'মপাসাঁ রচনাবলী', 'গি দ্য মপাসাঁ'),
        (r'জীবনানন্দ দাশের কাব্যগ্রন্থ', 'জীবনানন্দ দাশ'),
        (r'আল্লামা সাঈদী রচনাবলী', 'আল্লামা দেলাওয়ার হোসাইন সাঈদী'),
        (r'আল-মুকাদ্দিমা', 'ইবনে খালদুন'),
        (r'মুসনাদে আহমাদ', 'ইমাম আহমাদ বিন হাম্বল'),
        (r'আসহাবে রাসূলের জীবনকথা|বিশ্ব নবীর সাহাবী', 'মুহাম্মদ আব্দুল মা‘বুদ'),
        (r'তাগুত|সীরাতে সরওয়ারে আলম|তাফহীমুল কুরআন', 'সাইয়েদ আবুল আলা মওদুদী'),
        (r'বাংলাদেশে ইসলামী আন্দোলনে অগ্রপথিক যারা', 'আবদুল মান্নান তালিব'),
    ]

    updated_years_count = 0
    updated_authors_count = 0

    for b in catalog:
        # 1. Clean author if it has year attached
        cur_auth = b.get('author', '').strip()
        yr_in_auth = extract_year(cur_auth)
        if yr_in_auth and (not b.get('publication_year') or b.get('publication_year') == 'Unknown'):
            b['publication_year'] = yr_in_auth
            updated_years_count += 1
            
        cur_auth_noyr = re.sub(r'\s*\[.*?\]|\s*\(.*?\)', '', cur_auth).strip()
        if cur_auth_noyr in ('হুমায়ূন আহমেদ', 'হুমায়ুন আজাদ'):
            if cur_auth != cur_auth_noyr:
                b['author'] = cur_auth_noyr
                updated_authors_count += 1
                
        # 2. Map canonical author
        if b.get('author') in author_map:
            b['author'] = author_map[b['author']]
            updated_authors_count += 1

        # Title overrides
        t = b.get('title', '')
        for pat, real_auth in title_author_overrides:
            if re.search(pat, t):
                if b.get('author') != real_auth:
                    b['author'] = real_auth
                    updated_authors_count += 1
                break

        # Extract publication year from title or original filename if not set
        if not b.get('publication_year') or b.get('publication_year') == 'Unknown':
            yr_t = extract_year(t) or extract_year(b.get('original_filename', ''))
            if yr_t:
                b['publication_year'] = yr_t
                updated_years_count += 1

    print(f"Preserved/Updated {updated_years_count} publication years.")
    print(f"Consolidated/Updated {updated_authors_count} author entries.")

    # Save updated JSON
    with open(cat_json_path, 'w', encoding='utf-8') as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)

    # Save updated CSV
    if catalog:
        fieldnames = list(catalog[0].keys())
        with open(cat_csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(catalog)

    print("Saved updated master_catalog.json and master_catalog.csv.")

    # Regenerate AUTHOR_INDEX.md
    author_counts = defaultdict(int)
    for b in catalog:
        a = b.get('author', '').strip()
        if a and a not in ("Unknown", "NCTB", "এনসিটিবি"):
            author_counts[a] += 1

    # Load live drive author folder links from drive_author_folders.json
    base_audit = Path(r'C:\Users\USER\.gemini\antigravity\brain\fc64da93-615a-4dd3-b630-983a9609f78a\scratch\authors_audit')
    with open(base_audit / 'drive_author_folders.json', 'r', encoding='utf-8') as f:
        df = json.load(f)

    drive_links = {}
    for it in df['bangla_items']:
        drive_links[it['name']] = f"https://drive.google.com/drive/folders/{it['id']}"
    for it in df['az_items']:
        drive_links[it['name']] = f"https://drive.google.com/drive/folders/{it['id']}"

    # Add newly created folders
    new_folders = {
        'শায়খ আহমাদুল্লাহ': 'https://drive.google.com/drive/folders/1py7169ObJwt_qzvc8_WmQwRHGshqmUWq',
        'আরিফ আজাদ': 'https://drive.google.com/drive/folders/16KEop05HHNuVIaVYoKMu1cmQch0TnWkd',
        'গজেন্দ্রকুমার মিত্র': 'https://drive.google.com/drive/folders/1lsUIu5S7VczLN6LDAgj-k8G1zqBqUYo9',
        'মুহাম্মদ আব্দুল মা‘বুদ': 'https://drive.google.com/drive/folders/1LlDba09e31Yy2PovlZn8Q8-jlZhZecYE',
        'মাও সেতুং': 'https://drive.google.com/drive/folders/194yvz8SURSnkGWlgaue7FZ77Q6WGMfwj',
        'গি দ্য মপাসাঁ': 'https://drive.google.com/drive/folders/1TGie0hrQ06Grl681nyTIzYZu6CajZ8Gr',
        'ইবনে খালদুন': 'https://drive.google.com/drive/folders/1wdfcgP3EadXsYcVDDb17whgfEDRvL7S0',
        'ইমাম আহমাদ বিন হাম্বল': 'https://drive.google.com/drive/folders/1it3Wrzq83_UFHXW-xBihrxZSYXCa9bNq',
    }
    drive_links.update(new_folders)

    # Sort authors by count descending
    sorted_authors = sorted(author_counts.items(), key=lambda kv: (-kv[1], kv[0]))

    lines = [
        "# Author Index — Bangladesh Biggest eBook Library",
        "",
        f"Total unique named authors: **{len(sorted_authors):,}** (plus NCTB / এনসিটিবি textbooks and Unknown-author items flagged for review).",
        "",
        "Browse in Google Drive: [05_Authors_and_Scholars](https://drive.google.com/drive/folders/1HG9mZ-FGPOydiFc8h32iIDsKYGY-j9DB) | [বাংলা বর্ণমালা](https://drive.google.com/drive/folders/12hrCkJA6ABOYu5LlETm8cuOxu7ZkktGM) | [A-Z](https://drive.google.com/drive/folders/1t4sbTJRytV1btgWIJrqosHuXstIaEAtx)",
        "",
        "| # | Author | Books | Drive Folder |",
        "|---:|---|---:|---|"
    ]

    for idx, (auth, count) in enumerate(sorted_authors[:500], start=1):
        link = f"[Open Folder]({drive_links[auth]})" if auth in drive_links else "—"
        lines.append(f"| {idx} | {auth} | {count} | {link} |")

    with open(author_index_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines) + "\n")

    print(f"Regenerated AUTHOR_INDEX.md with {len(sorted_authors)} authors.")

if __name__ == '__main__':
    main()
