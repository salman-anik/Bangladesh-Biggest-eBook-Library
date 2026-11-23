import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from reorg_step4 import classify_author

SRC_XLSX = r'C:\Users\USER\.gemini\antigravity\scratch\Bangladesh-Biggest-eBook-Library\data\live_Library_Master_Navigator.xlsx'
OUT_XLSX = r'C:\Users\USER\.gemini\antigravity\scratch\Bangladesh-Biggest-eBook-Library\data\updated_Library_Master_Navigator.xlsx'

ROOT_CAT_MAP = {
    '00_Library_Management': 'Library Management',
    '01_Bangla_Books': 'Bangla Books',
    '02_English_Books': 'English Books',
    '03_Education_and_Textbooks': 'Education & Textbooks',
    '04_Religion_Books': 'Religion Books',
    '05_Authors_and_Scholars': 'Authors & Scholars',
    '06_Series_and_Collections': 'Series & Collections',
    '07_Reference_and_Research': 'Reference & Research',
    '08_Review_and_Unclassified': 'Review & Unclassified',
}

BANGLA_SUB_MAP = {
    'অনুবাদ ও বিদেশী সাহিত্য': 'Translated & Foreign Literature (অনুবাদ সাহিত্য)',
    'অন্যান্য': 'Other Books (অন্যান্য)',
    'ইতিহাস': 'History & Culture (ইতিহাস)',
    'উপন্যাস': 'Literature & Novels (উপন্যাস)',
    'কবিতা': 'Poetry (কবিতা)',
    'গল্প ও ছোটগল্প': 'Stories & Short Stories (গল্প ও ছোটগল্প)',
    'জীবনী ও আত্মজীবনী': 'Biography & Autobiography (জীবনী ও আত্মজীবনী)',
    'থ্রিলার, রহস্য ও গোয়েন্দা': 'Thriller, Mystery & Detective (থ্রিলার ও গোয়েন্দা)',
    'ধর্ম ও দর্শন': 'Philosophy & Thought (দর্শন ও চিন্তাধারা)',
    'নাটক': 'Drama & Plays (নাটক)',
    'প্রবন্ধ': 'Essays & Articles (প্রবন্ধ)',
    'বিজ্ঞান ও প্রযুক্তি': 'Science & Technology (বিজ্ঞান ও প্রযুক্তি)',
    'ভাষা ও ব্যাকরণ': 'Language & Grammar (ভাষা ও ব্যাকরণ)',
    'ভ্রমণ': 'Travel & Geography (ভ্রমণ)',
    'শিশু-কিশোর সাহিত্য': 'Children & Teen Literature (শিশু-কিশোর সাহিত্য)',
}

ENGLISH_SUB_MAP = {
    'Fiction': 'Fiction & Literature',
    'Science': 'Science & Technology',
    'Technology': 'Computer Science',
    'Non_Fiction': 'Self Development & Non-Fiction',
    'Biography': 'Biography & Memoirs',
    'History': 'History',
    'Philosophy': 'Philosophy',
    'Others': 'Other Subjects',
}

RELIGION_SUB_MAP = {
    'Buddhism_Books': 'Other Religions/Buddhism',
    'Christianity_Books': 'Other Religions/Christianity',
    'Comparative_and_Other_Religions': 'Other Religions/Comparative Religion',
    'Hinduism_Books': 'Other Religions/Hinduism',
    'Islamic_Books': 'Islam',
    'Islamic_Books/কুরআন ও তাফসির': 'Islam/Quran & Tafsir (কুরআন ও তাফসির)',
    'Islamic_Books/হাদিস': 'Islam/Hadith & Hadith Sciences (হাদিস)',
    'Islamic_Books/ফিকহ': 'Islam/Fiqh & Islamic Jurisprudence (ফিকহ)',
    'Islamic_Books/আকিদা': 'Islam/Aqidah & Theology (আকিদা)',
    'Islamic_Books/ইসলামিক ইতিহাস': 'Islam/Islamic History (ইসলামিক ইতিহাস)',
    'Islamic_Books/সীরাত': 'Islam/Seerah & Biography (সীরাত)',
    'Islamic_Books/ইসলামিক সাহিত্য': 'Islam/Islamic Literature & Spirituality (ইসলামিক সাহিত্য)',
    'Islamic_Books/অন্যান্য': 'Islam/Dawah, Tabligh & Other Islamic Books (অন্যান্য)',
}

SERIES_SPECIAL = {'আল-বিদায়া ওয়ান নিহায়া', 'তাফসীর ইবনে কাসীর', 'তাফহীমুল কুরআন', 'ফী যিলালিল কুরআন', 'মাসিক আত-তাহরীক'}
SERIES_COMPLETE = {'রচনাবলী ও রচনাসমগ্র'}

REF_SUB_MAP = {
    'Dictionaries': 'Dictionaries & Encyclopedias/Dictionaries',
    'Encyclopedias': 'Dictionaries & Encyclopedias/Encyclopedias',
    'Journals': 'Reference Materials & Periodicals/Journals',
    'Magazines': 'Reference Materials & Periodicals/Magazines',
    'Research_Papers': 'Research Papers',
}

REVIEW_SUB_MAP = {
    'Needs_Manual_Review': 'Pending Review',
    'Exact_Duplicates_Quarantine': 'Duplicate Review',
    'Uncertain_Authors': 'Uncategorized Books/Uncertain_Authors',
    'upcoming book': 'Uncategorized Books/Upcoming Books',
    'Archives_ZIP': 'Uncategorized Books/Archives_ZIP',
    'Broken_HTML_Redirects': 'Uncategorized Books/Broken_HTML_Redirects',
    'Corrupted_or_Empty': 'Uncategorized Books/Corrupted_or_Empty',
}

def map_category_and_sub(old_cat, old_sub):
    new_cat = ROOT_CAT_MAP.get(old_cat, old_cat or '')
    sub = old_sub or ''
    edu_sys, acad_lvl, class_yr, semester = 'N/A', 'N/A', 'N/A', 'N/A'
    subject = sub

    if new_cat == 'Bangla Books':
        new_sub = BANGLA_SUB_MAP.get(sub, sub)
        subject = new_sub
    elif new_cat == 'English Books':
        new_sub = ENGLISH_SUB_MAP.get(sub, sub)
        subject = new_sub
    elif new_cat == 'Religion Books':
        new_sub = RELIGION_SUB_MAP.get(sub, sub)
        if 'Islamic_Books/' in sub and new_sub == sub:
            part = sub.split('/', 1)[1]
            new_sub = RELIGION_SUB_MAP.get(f'Islamic_Books/{part}', f'Islam/{part}')
        subject = new_sub.split('/')[-1] if '/' in new_sub else new_sub
    elif new_cat == 'Education & Textbooks':
        if sub == 'Admission':
            new_sub = 'General Education/Admission & Entrance Preparation'
            edu_sys, acad_lvl = 'General Education', 'Admission & Entrance'
        elif sub in ('Udvash Academic & Admission Care', 'Vitamin Admission Series'):
            new_sub = f'General Education/Admission & Entrance Preparation/{sub}'
            edu_sys, acad_lvl = 'General Education', 'Admission & Entrance'
        elif sub == 'Professional_Exams':
            new_sub = 'General Education/Professional & Job Exams (BCS)'
            edu_sys, acad_lvl = 'General Education', 'Professional & Job Exams'
        elif sub == 'HSC_Class_11-12':
            new_sub = 'General Education/Higher Secondary (Class 11-12)'
            edu_sys, acad_lvl, class_yr = 'General Education', 'Higher Secondary', 'Class 11-12'
        elif sub == 'School' or sub.startswith('School/'):
            edu_sys = 'General Education'
            if sub == 'School':
                new_sub = 'General Education/Secondary Education'
                acad_lvl = 'Secondary Education'
            elif sub == 'School/Pre_Primary':
                new_sub = 'General Education/Primary Education/Pre-Primary'
                acad_lvl, class_yr = 'Primary Education', 'Pre-Primary'
            elif sub == 'School/Other_School':
                new_sub = 'General Education/Other School Resources'
                acad_lvl = 'Primary & Secondary'
            elif sub.startswith('School/Class_'):
                cnum = int(sub.split('_')[-1])
                cls_label = f'Class {cnum}'
                class_yr = cls_label
                if cnum <= 5:
                    acad_lvl = 'Primary Education'
                    new_sub = f'General Education/Primary Education/{cls_label}'
                else:
                    acad_lvl = 'Secondary Education'
                    new_sub = f'General Education/Secondary Education/{cls_label}'
            else:
                new_sub = sub
        elif sub.startswith('Madrasa'):
            edu_sys = 'Alia Madrasa'
            parts = sub.split('/')
            if len(parts) == 1:
                new_sub = 'Alia Madrasa'
            elif parts[1] == 'Ibtedayi':
                new_sub = 'Alia Madrasa/Ebtedayee'
                acad_lvl = 'Ebtedayee'
            elif parts[1].startswith('Class_'):
                cnum = int(parts[1].split('_')[-1])
                new_sub = f'Alia Madrasa/Ebtedayee/Class {cnum}'
                acad_lvl, class_yr = 'Ebtedayee', f'Class {cnum}'
            elif parts[1] == 'Dakhil':
                new_sub = 'Alia Madrasa/Dakhil'
                acad_lvl = 'Dakhil'
            elif parts[1] == 'General':
                new_sub = 'Alia Madrasa/General'
                acad_lvl = 'General Madrasa Studies'
            else:
                new_sub = 'Alia Madrasa/' + '/'.join(parts[1:])
        elif sub.startswith('Qawmi_Madrasa'):
            edu_sys = 'Qawmi Madrasa'
            new_sub = sub.replace('Qawmi_Madrasa', 'Qawmi Madrasa', 1)
        elif sub.startswith('University'):
            edu_sys = 'University Education'
            new_sub = sub.replace('University', 'University Education', 1)
        else:
            new_sub = sub
        subject = new_sub.split('/')[-1]
    elif new_cat == 'Authors & Scholars':
        # Flatten A-Z/<Letter>/<Author> or বাংলা বর্ণমালা/<Author> -> Bangladeshi Authors/<Author>, International Authors/<Author>, Islamic Scholars/<Sub>/<Author>
        if sub.startswith('A-Z/'):
            parts = sub.split('/')
            author_name = parts[2] if len(parts) >= 3 else parts[-1]
            rest = '/'.join(parts[3:]) if len(parts) > 3 else ''
        elif sub.startswith('বাংলা বর্ণমালা/'):
            parts = sub.split('/')
            author_name = parts[1] if len(parts) >= 2 else parts[-1]
            rest = '/'.join(parts[2:]) if len(parts) > 2 else ''
        else:
            author_name = sub
            rest = ''
        cat_a, sub_a = classify_author(author_name)
        if cat_a == 'intl':
            base = f'International Authors/{author_name}'
        elif cat_a == 'scholar':
            base = f'Islamic Scholars/{sub_a}/{author_name}'
        else:
            base = f'Bangladeshi Authors/{author_name}'
        new_sub = f'{base}/{rest}' if rest else base
        subject = author_name
    elif new_cat == 'Series & Collections':
        if sub in SERIES_COMPLETE:
            new_sub = f'Complete Collections/{sub}'
        elif sub in SERIES_SPECIAL:
            new_sub = f'Special Collections/{sub}'
        else:
            new_sub = f'Book Series/{sub}'
        subject = sub
    elif new_cat == 'Reference & Research':
        new_sub = REF_SUB_MAP.get(sub, sub)
        subject = new_sub.split('/')[-1]
    elif new_cat == 'Review & Unclassified':
        new_sub = REVIEW_SUB_MAP.get(sub, sub)
        subject = new_sub.split('/')[-1]
    else:
        new_sub = sub

    return new_cat, new_sub, subject, edu_sys, acad_lvl, class_yr, semester

def remap_path_string(p):
    if not p or not isinstance(p, str):
        return p
    parts = [x for x in p.split('/') if x]
    if not parts:
        return p
    old_root = parts[0]
    if old_root not in ROOT_CAT_MAP:
        return p
    # Check if filename is at the end (has extension)
    has_file = '.' in parts[-1] and len(parts) >= 2
    fname = parts[-1] if has_file else None
    sub_parts = parts[1:-1] if has_file else parts[1:]
    old_sub = '/'.join(sub_parts)
    new_cat, new_sub, *_ = map_category_and_sub(old_root, old_sub)
    if fname:
        return f"{new_cat}/{new_sub}/{fname}" if new_sub else f"{new_cat}/{fname}"
    return f"{new_cat}/{new_sub}/" if new_sub else f"{new_cat}/"

def update_books_sheet(ws):
    headers = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
    new_cols = ['Subject', 'Education System', 'Academic Level', 'Class / Year', 'Semester', 'Classification Status']
    existing_col_count = len(headers)
    add_start = existing_col_count + 1
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")

    col_indices = {}
    for idx, col_name in enumerate(new_cols):
        if col_name in headers:
            col_indices[col_name] = headers.index(col_name) + 1
        else:
            c_idx = add_start + len([x for x in new_cols[:idx] if x not in headers])
            cell = ws.cell(1, c_idx, col_name)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
            col_indices[col_name] = c_idx

    # Also locate existing columns: Target Category (5), Target Subfolder (6), Target Folder Path (11), Current Drive Path (12), Placement Status (13), Verification Status (20)
    for r in range(2, ws.max_row + 1):
        old_cat = ws.cell(r, 5).value
        old_sub = ws.cell(r, 6).value
        new_cat, new_sub, subject, edu_sys, acad_lvl, class_yr, semester = map_category_and_sub(old_cat, old_sub)

        ws.cell(r, 5).value = new_cat
        ws.cell(r, 6).value = new_sub
        ws.cell(r, 11).value = f"{new_cat}/{new_sub}/" if new_sub else f"{new_cat}/"

        cur_p = ws.cell(r, 12).value
        if cur_p:
            ws.cell(r, 12).value = remap_path_string(cur_p)

        ver_status = ws.cell(r, 20).value or ''
        place_status = ws.cell(r, 13).value or ''
        if new_cat == 'Review & Unclassified' or 'Needs Review' in str(ver_status):
            cls_status = str(ver_status) if ver_status else 'Pending Review'
        elif 'Correctly Placed' in str(place_status):
            cls_status = 'Classified & Verified'
        else:
            cls_status = str(place_status) or 'Classified'

        ws.cell(r, col_indices['Subject']).value = subject
        ws.cell(r, col_indices['Education System']).value = edu_sys
        ws.cell(r, col_indices['Academic Level']).value = acad_lvl
        ws.cell(r, col_indices['Class / Year']).value = class_yr
        ws.cell(r, col_indices['Semester']).value = semester
        ws.cell(r, col_indices['Classification Status']).value = cls_status

def main():
    print(f"Loading live workbook {SRC_XLSX}...")
    wb = openpyxl.load_workbook(SRC_XLSX)

    # 1. Update Dashboard
    ws_dash = wb['📊 Dashboard & Navigator']
    for r in range(1, ws_dash.max_row + 1):
        for c in range(1, ws_dash.max_column + 1):
            v = ws_dash.cell(r, c).value
            if isinstance(v, str):
                for old_k, new_k in ROOT_CAT_MAP.items():
                    v = v.replace(old_k, new_k)
                v = v.replace('(বাংলা বর্ণমালা ও A-Z Index) — 1 Author = 1 Folder', '(Bangladeshi Authors, International Authors & Islamic Scholars — Flat Author Folders)')
                ws_dash.cell(r, c).value = v

    # 2. Update All Books & Review & Placement Tasks
    print("Updating All Books sheet...")
    update_books_sheet(wb['📚 All Books (18,647)'])
    print("Updating Review & Placement Tasks sheet...")
    update_books_sheet(wb['⚠️ Review & Placement Tasks'])

    # 3. Update Folder Placement Guide
    print("Updating Folder Placement Guide sheet...")
    ws_guide = wb['📁 Folder Placement Guide']
    for r in range(2, ws_guide.max_row + 1):
        old_cat = ws_guide.cell(r, 1).value
        old_sub = ws_guide.cell(r, 2).value
        if old_sub and str(old_sub).startswith('—'):
            new_cat = ROOT_CAT_MAP.get(old_cat, old_cat)
            ws_guide.cell(r, 1).value = new_cat
            ws_guide.cell(r, 3).value = f"{new_cat}/"
            if isinstance(ws_guide.cell(r, 6).value, str):
                v6 = ws_guide.cell(r, 6).value
                for ok, nk in ROOT_CAT_MAP.items():
                    v6 = v6.replace(ok, nk)
                ws_guide.cell(r, 6).value = v6
        elif old_cat in ROOT_CAT_MAP:
            new_cat, new_sub, *_ = map_category_and_sub(old_cat, old_sub)
            ws_guide.cell(r, 1).value = new_cat
            ws_guide.cell(r, 2).value = new_sub
            ws_guide.cell(r, 3).value = f"{new_cat}/{new_sub}/" if new_sub else f"{new_cat}/"
            ws_guide.cell(r, 6).value = f"Books categorized under {new_cat} > {new_sub}."

    # 4. Update Author Folders Directory
    print("Updating Author Folders Directory sheet...")
    ws_auth = wb['✍️ Author Folders Directory']
    for r in range(2, ws_auth.max_row + 1):
        auth_name = ws_auth.cell(r, 2).value
        if auth_name:
            cat_a, sub_a = classify_author(str(auth_name))
            if cat_a == 'intl':
                ws_auth.cell(r, 3).value = 'Authors & Scholars / International Authors'
            elif cat_a == 'scholar':
                ws_auth.cell(r, 3).value = f'Authors & Scholars / Islamic Scholars / {sub_a}'
            else:
                ws_auth.cell(r, 3).value = 'Authors & Scholars / Bangladeshi Authors'

    print(f"Saving updated workbook to {OUT_XLSX}...")
    wb.save(OUT_XLSX)
    print("Saved successfully!")

if __name__ == '__main__':
    main()
