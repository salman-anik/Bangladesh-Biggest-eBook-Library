import sys
import os
import json
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
from reorg_lib import rename_item, move_item, mkdir_item, gdrive_ls

AUTHORS_ROOT_ID = '1HG9mZ-FGPOydiFc8h32iIDsKYGY-j9DB'
AUTHORS_AZ_ID = '1t4sbTJRytV1btgWIJrqosHuXstIaEAtx'
AUTHORS_BANGLA_ID = '12hrCkJA6ABOYu5LlETm8cuOxu7ZkktGM'
REVIEW_ROOT_ID = '17xG7eM-GtkED3hWMfT1riucin9fnlI2t'

INTERNATIONAL_AUTHORS = {
    'অ্যার্জে', 'অ্যালেক্স রাদারফোর্ড', 'আইজাক আসিমভ', 'আগাথা ক্রিস্টি', 'আলফ্রেড হিচকক',
    'আলেকজান্ডার দ্যুমা', 'উইলবার এডিসন স্মিথ', 'উইলবার স্মিথ', 'উইলিয়াম শেক্সপিয়ার',
    'এ. পি. জে. আবদুল কালাম', 'এরিক ফন দানিকেন', 'কারেন আর্মস্ট্রং', 'কৃষণ চন্দর',
    'কেইগো হিগাশিনো', 'গি দ্য মপাসাঁ', 'চার্লস ডিকেন্স', 'জিম করবেট', 'জুল ভার্ন',
    'জেমস হ্যাডলি চেজ', 'ডেল কার্ণেগী', 'ডেল কার্নেগী', 'ড্যান ব্রাউন',
    'ড্যান ব্রাউন, মোহাম্মদ নাজিম উদ্দিন', 'নিল গেইম্যান', 'পাওলো কোয়েলহো',
    'প্রাণ কুমার শর্মা', 'ব্রায়ান ট্রেসি', 'মাও সেতুং', 'মার্ক টোয়েন', 'মিশিও কাকু',
    'ম্যাক্সিম গোর্কী', 'সিডনি শেলডন', 'স্টিফেন কিং', 'স্টিফেন হকিং',
    'স্যার আর্থার কোনান ডয়েল', 'হেনরি রাইডার হ্যাগার্ড',
    'C. L. Wilson', 'Maxim Gorki', 'Nur Masalha', 'Shlomo Sand', 'William B. Brown'
}

ARAB_SCHOLARS = {
    'Muhammad Bin Saleh Al Usaimin', 'ইবনু উসাইমীন', 'ইবনে উসাইমীন', 'ইবনে খালদুন',
    'আলবানী', 'ইমাম আহমাদ বিন হাম্বল', 'ইমাম ইবনে তাইমিয়া (রহ.)',
    'ইমাম মুহাম্মাদ আল-বুখারী (রহ.)',
    'ইমাম আল হুজ্জাতুল ইসলাম, আবূ বকর আহমাদ বিন আলী যাসসাস (র)',
    'শাইখ আলী তানতাবী', 'শায়খ মুহাম্মদ ইব্রাহীম আত-তুয়াইজিরী',
    'আহমাদ আবদুল আলী তাহতাভী', 'تنزيل من رب العالمين', 'دارالمؤلفین'
}

SOUTH_ASIAN_SCHOLARS = {
    'তারিক জামীল', 'ড. জাকির নায়েক', 'মুহাম্মদ ইকবাল কিলানী',
    'সাইয়েদ আবুল আলা মওদুদী', 'Zubair Ali Zai', 'নসীম হিজাযী', 'নাসিম হেযাজী',
    'এনায়তুল্লাহ আলতামাস', 'এনায়েতুল্লাহ আলতামাশ'
}

BANGLADESHI_SCHOLARS = {
    'আবদুল মান্নান তালিব', 'আবদুস শহীদ নাসিম', 'আব্দুস শহীদ নাসিম',
    'আবু আহমাদ সাইফুদ্দিন বেলাল', 'আবু তাহের মিসবাহ', 'আবু বকর জাকারিয়া',
    'ড. আবু বকর মুহাম্মাদ যাকারিয়া', 'আব্দুল হামীদ ফাইযী', 'আব্দুল্লাহ শহীদ আব্দুর রহমান',
    'আব্বাস আলী খান', 'আলী হাসান তৈয়ব', 'আল্লামা দেলাওয়ার হোসাইন সাঈদী',
    'আসাদুল্লাহ গালিব', 'মুহাম্মদ আসাদুল্লাহ আল গালিব', 'আরিফ আজাদ', 'কতিপয় উলামা',
    'ড. কাবীরুল ইসলাম', 'ড.কাবীরুল ইসলাম', 'ড. খোন্দকার আব্দুল্লাহ জাহাঙ্গীর',
    'ড. মুহাম্মদ মুযাম্মিল আলি', 'ড. মোহাম্মদ মানজুরে ইলাহী', 'মওলানা মুহাম্মাদ আবদুর রহীম',
    'মুফতীয়ে আযম বাঙ্গাল শায়েখ গোলাম সামদানী রেজভী', 'মুহাম্মদ আব্দুল মা‘বুদ',
    'মুহাম্মদ নুরুল ইসলাম', 'মোস্তাফিজুর রহমান ইবন আব্দুল আযীয আল-মাদানী',
    'শাইখ আতিক উল্লাহ', 'শায়খ আহমাদুল্লাহ', 'সানাউল্লাহ নজির আহমদ',
    'অধ্যাপক গোলাম আযম', 'অধ্যাপক আবদুল মতিন', 'অধ্যাপক মুজিবুর রহমান',
    'এ এন এম সিরাজুল ইসলাম', 'এ. কে. এম. নাজির আহমদ',
    'Abdullah Al-Amin', 'SHAIKH NOOR-E-ALAM', 'mijan bin motahar', 'Shahid Zubair'
}

def classify_author(name):
    if name in ARAB_SCHOLARS:
        return ('scholar', 'Arab Scholars')
    if name in SOUTH_ASIAN_SCHOLARS:
        return ('scholar', 'South Asian Scholars')
    if name in BANGLADESHI_SCHOLARS:
        return ('scholar', 'Bangladeshi Scholars')
    if name in INTERNATIONAL_AUTHORS:
        return ('intl', None)
    return ('bd', None)

def run_step4():
    print("=== STEP 4: Authors & Scholars Restructuring (Flat, No A-Z Subfolders) ===")
    top_items = {it['id']: it['name'] for it in gdrive_ls(AUTHORS_ROOT_ID)}

    # 1. Rename বাংলা বর্ণমালা -> Bangladeshi Authors (keeps all BD authors in-place, zero unnecessary moves!)
    if AUTHORS_BANGLA_ID in top_items and top_items[AUTHORS_BANGLA_ID] != 'Bangladeshi Authors':
        rename_item(AUTHORS_BANGLA_ID, 'Bangladeshi Authors', old_name=top_items[AUTHORS_BANGLA_ID])
    bd_authors_id = AUTHORS_BANGLA_ID

    # 2. Create International Authors and Islamic Scholars (with regional scholar categories)
    intl_authors_id = mkdir_item('International Authors', AUTHORS_ROOT_ID)
    scholars_root_id = mkdir_item('Islamic Scholars', AUTHORS_ROOT_ID)
    bd_scholars_id = mkdir_item('Bangladeshi Scholars', scholars_root_id)
    sa_scholars_id = mkdir_item('South Asian Scholars', scholars_root_id)
    arab_scholars_id = mkdir_item('Arab Scholars', scholars_root_id)

    scholar_dest = {
        'Bangladeshi Scholars': bd_scholars_id,
        'South Asian Scholars': sa_scholars_id,
        'Arab Scholars': arab_scholars_id,
    }

    moves = []

    # Scan Bangladeshi Authors (formerly বাংলা বর্ণমালা) and move out International & Islamic Scholars
    bd_cur = gdrive_ls(bd_authors_id)
    for it in bd_cur:
        cat, sub = classify_author(it['name'])
        if cat == 'intl':
            moves.append((it['id'], intl_authors_id, bd_authors_id, it['name']))
        elif cat == 'scholar':
            moves.append((it['id'], scholar_dest[sub], bd_authors_id, it['name']))

    # Scan A-Z letter folders and move ALL authors out into flat folders!
    az_letters = gdrive_ls(AUTHORS_AZ_ID)
    with ThreadPoolExecutor(max_workers=6) as ex:
        letter_children = list(ex.map(lambda l: (l['id'], l['name'], gdrive_ls(l['id'])), [x for x in az_letters if x.get('mimeType') == 'application/vnd.google-apps.folder']))

    for lid, lname, items in letter_children:
        for it in items:
            cat, sub = classify_author(it['name'])
            if cat == 'intl':
                target = intl_authors_id
            elif cat == 'scholar':
                target = scholar_dest[sub]
            else:
                target = bd_authors_id
            moves.append((it['id'], target, lid, it['name']))

    print(f"Moving {len(moves)} author folders into flat Bangladeshi/International/Islamic Scholar folders...")
    with ThreadPoolExecutor(max_workers=5) as ex:
        list(ex.map(lambda args: move_item(*args), moves))

    # Archive empty A-Z container folder (never delete/trash)
    archive_empty_id = mkdir_item('Archived Empty Legacy Folders', REVIEW_ROOT_ID)
    top_cur_after = {it['id']: it['name'] for it in gdrive_ls(AUTHORS_ROOT_ID)}
    if AUTHORS_AZ_ID in top_cur_after:
        # Verify A-Z letters are empty
        remaining = 0
        for lid, lname, _ in letter_children:
            if len(gdrive_ls(lid)) > 0:
                remaining += 1
        if remaining == 0:
            move_item(AUTHORS_AZ_ID, archive_empty_id, old_parent_id=AUTHORS_ROOT_ID, name='A-Z (Empty Alphabet Folders)')
        else:
            print(f"[WARN] A-Z still has {remaining} non-empty letter folders; keeping for inspection.")

if __name__ == '__main__':
    run_step4()
