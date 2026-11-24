#!/usr/bin/env python3
"""
Stage 3: Author Subfolder & Internet Series Organizer.

1) Fetches author bibliographies & book series lists from Bangla/English Wikipedia API
   plus curated series/genre taxonomies.
2) Populates existing empty subfolders under author folders (e.g. হুমায়ূন আহমেদ's
   existing subfolders) and creates clean series/genre subfolders for prolific authors
   (only creating new subfolders when >= 3 books match that subfolder, never creating duplicates).
3) Moves loose files strictly within their own author folder (never outside the author folder),
   logs every `create_folder` and `move` to Library Management/Reports/rename_changelog.{json,csv,md},
   and writes App/assets/series_catalog.json + visualize/public/series_catalog.json.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import drive_utils as du  # noqa: E402

BENGALI_RE = re.compile(r"[\u0980-\u09FF]")

# Curated + Internet-verified series & subgenre rules per author
AUTHOR_SERIES_RULES: dict[str, list[dict[str, Any]]] = {
    "হুমায়ূন আহমেদ": [
        {
            "bucket": "হিমু সিরিজ",
            "match_existing": ["হিমু", "himu"],
            "keywords": [
                "হিমু", "himu", "ময়ূরাক্ষী", "moyurakkhi", "দরজার ওপাশে", "dorjar opashe",
                "হলুদ হিমু", "পারাপার", "এবং হিমু", "এবংহিমু", "আজ হিমুর বিয়ে", "আঙুল কাটা জগলু",
                "angul kata", "মজার ভূত", "mojar bhoot", "হিমুর দ্বিতীয় প্রহর", "হিমুর রূপালী রাত্রি",
                "হিমুর হাতে কয়েকটি নীলপদ্ম", "সে আসে ধীরে", "হিমু মামা", "himu mama", "হিমুর নীল জোছনা",
                "হিমুর বাবার কথামালা", "হিমু রিমান্ডে", "হিমুর একান্ত সাক্ষাৎকার", "চলে যায় বসন্তের দিন",
                "তোমাদের এই নগরে", "একজন হিমু কয়েকটি ঝিঁঝিঁ পোকা", "হিমুর মধ্যদুপুর", "হিমুর আছে জল",
            ],
            "wiki_page": "হিমু (চরিত্র)",
        },
        {
            "bucket": "মিসির আলি সিরিজ",
            "match_existing": ["মিসির", "misir"],
            "keywords": [
                "মিসির আলি", "মিসিরআলি", "misir ali", "দেবী", "debi", "devi", "নিশীথিনী", "nishithini",
                "নিষাদ", "অন্যভুবন", "বৃহন্নলা", "brihonnola", "ভয়", "bhoy", "বিপদ", "অনীশ", "অনুভূতি",
                "তন্দ্রাবিলাস", "tondrabilash", "আমি এবং আমরা", "ami ebong amra", "আমিই মিসির আলি",
                "বাঘবন্দী মিসির আলি", "কহেন কবি কালিদাস", "kohen kobi kalidas", "হিমু এবং মিসির আলি",
                "যখন নামিবে আঁধার", "jokhon namibe", "পুফি", "হরতন ইশকাপন", "hartan", "মিসির আলির চশমা",
            ],
            "wiki_page": "মিসির আলি",
        },
        {
            "bucket": "শুভ্র সিরিজ",
            "match_existing": ["শুভ্র", "shuvro"],
            "keywords": [
                "শুভ্র", "shuvro", "দারুচিনি দ্বীপ", "daruchini", "রূপালী দ্বীপ", "মেঘের ছায়া",
                "এই শুভ্র", "শুভ্র গেছে বনে",
            ],
            "wiki_page": "শুভ্র",
        },
        {
            "bucket": "সায়েন্স ফিকশন ও রহস্য",
            "match_existing": ["সায়েন্স", "কল্প", "বৈজ্ঞানিক", "রহস্য", "ভৌতিক", "sci", "horror"],
            "keywords": [
                "সায়েন্স ফিকশন", "কল্পকাহিনী", "বৈজ্ঞানিক", "অমেঘ", "ইরিনা", "কুহক", "ফিহা সমীকরণ",
                "শূন্য", "নি", "ওমেগা পয়েন্ট", "অনন্ত নক্ষত্র বীথি", "দ্বিতীয় মানব", "নক্ষত্রের রাত",
                "তোমাদের জন্য ভালোবাসা", "অমানুষ", "পিশাচ", "ম্যাজিক মুন্সী", "কানী ডাইনি",
            ],
        },
        {
            "bucket": "মুক্তিযুদ্ধ",
            "match_existing": ["মুক্তিযুদ্ধ", "liberation", "১৯৭১", "1971"],
            "keywords": [
                "মুক্তিযুদ্ধ", "জোছনা ও জননীর গল্প", "শ্যামল ছায়া", "আগুনের পরশমণি", "নির্বাসন",
                "১৯৭১", "1971", "অনিল বাগচীর একদিন", "সৌরভ", "সূর্যের দিন",
            ],
        },
        {
            "bucket": "ভ্রমণ, প্রবন্ধ ও আত্মজীবনী",
            "match_existing": ["ভ্রমণ", "আত্মজীবনী", "স্মৃতি", "প্রবন্ধ", "ব্যক্তিগত"],
            "keywords": [
                "বলপয়েন্ট", "কাঠপেন্সিল", "ফাউন্টেনপেন", "রংপেন্সিল", "হিজিবিজি", "হোটেল গ্রেভার ইন",
                "নিউইয়র্কের", "ময়ূরপঙ্খী", "আমার ছেলেবেলা", "হুমায়ূন আহমেদের হাতে", "ছবি বানানোর গল্প",
                "আপনারে আমি খুঁজিয়া বেড়াই", "ফেরা", "সমুদ্র বিলাস", "মেঘ বলেছে",
            ],
        },
        {
            "bucket": "গল্প",
            "match_existing": ["গল্প", "story", "stories"],
            "keywords": ["গল্প", "golpo", "galpo", "গল্পসমগ্র", "শ্রেষ্ঠ গল্প", "বোতল ভূত", "ভূতসমগ্র", "অদ্ভুত সব গল্প"],
        },
        {
            "bucket": "উপন্যাস",
            "match_existing": ["উপন্যাস", "novel"],
            "keywords": [
                "উপন্যাস", "নন্দিত নরকে", "শঙ্খনীল কারাগার", "বাদশাহ নামদার", "মধ্যাহ্ন", "গৌরীপুর জংশন",
                "কোথাও কেউ নেই", "অচিনপুর", "বৃষ্টি বিলাস", "বাদল দিনের", "বহুব্রীহি", "লীলাবতী",
                "শ্রাবণ মেঘের দিন", "মাতাল হাওয়া", "দেয়াল", "অপেক্ষা", "নৃপতি", "ফেরা", "কবি",
                "তেঁতুল বনে জোছনা", "কে কথা কয়", "সবাই গেছে বনে", "পেন্সিলে আঁকা পরী", "তিথির নীল তোয়ালে",
                "এইসব দিনরাত্রি", "একটি সাইকেল এবং কয়েকটি ডাহুক পাখি", "আমার আছে জল", "সাজঘর", "ইস্টিশন",
                "রূপা", "বাসর", "আয়নাঘর", "পাখি আমার একলা পাখি", "লিলুয়া বাতাস", "মেঘের উপর বাড়ি",
                "দূরে কোথাও", "সেদিন চৈত্রমাস", "দিনগুলি মোর", "অন্যদিন", "চাঁদের আলোয় কয়েকজন যুবক",
            ],
            "wiki_page": "হুমায়ূন আহমেদের গ্রন্থপঞ্জি",
        },
    ],
    "মুহম্মদ জাফর ইকবাল": [
        {
            "bucket": "সায়েন্স ফিকশন",
            "match_existing": ["সায়েন্স", "কল্প", "বৈজ্ঞানিক"],
            "keywords": [
                "সায়েন্স ফিকশন", "কল্পকাহিনী", "কপোট্রনিক", "মহাকাশে মহাত্রাস", "ক্রুগো", "ত্রাতিনা",
                "টুকুনজিল", "নিঃসঙ্গ গ্রহচারী", "অক্টোপাসের চোখ", "ইকারাস", "প্রজেক্ট নেবুলা",
                "সেরিনা", "সুহানের স্বপ্ন", "রবো নগরী", "অবনীল", "ব্ল্যাকহোলের বাচ্চা", "ক্রেনিয়াল",
                "রিটিন", "জলজ", "সায়রা সায়েন্টিস্ট", "ত্রিনিত্রি রাশিমালা", "অন্ধকারের গ্রহ",
                "মেতসিস", "অমানুষ", "ফোবিয়ানের যাত্রী", "নিঃসঙ্গ", "কেপলার", "নয় নয় শূন্য তিন",
                "টুকি ও ঝায়ের", "বিজ্ঞানী অনিক লুম্বা", "অন্য জীবন", "একজন অতিমানবী",
            ],
            "wiki_page": "মুহম্মদ জাফর ইকবালের গ্রন্থপঞ্জি",
        },
        {
            "bucket": "কিশোর উপন্যাস ও গল্প",
            "match_existing": ["কিশোর", "শিশু"],
            "keywords": [
                "দীপু নাম্বার", "আমার বন্ধু রাশেদ", "আমি তপু", "হাত কাটা রবিন", "দুষ্টু ছেলের দল",
                "টি-রেক্স", "বিজ্ঞানী সফদর আলী", "বুবুনের বাবা", "আমড়া ও ক্র্যাব নেবুলা", "দস্যি কজন",
                "মেকু কাহিনী", "লাবু এল শহরে", "কাজলের দিনরাত্রি", "রাতুলের রাত", "নিতু ও তার বন্ধুরা",
                "শান্তা পরিবার", "গাব্বু", "ইস্টিশন", "কিশোর", "কাঁকন", "বাচ্চা ভয়ংকর",
            ],
        },
        {
            "bucket": "বিজ্ঞান, গণিত ও প্রবন্ধ",
            "match_existing": ["বিজ্ঞান", "গণিত", "প্রবন্ধ"],
            "keywords": ["বিজ্ঞান", "গণিত", "কোয়ান্টাম", "কম্পিউটার", "মুক্তিযুদ্ধ", "সাদাসিধে কথা", "কলাম", "প্রবন্ধ"],
        },
    ],
    "সত্যজিৎ রায়": [
        {
            "bucket": "ফেলুদা সিরিজ",
            "match_existing": ["ফেলুদা"],
            "keywords": ["ফেলুদা", "feluda", "সোনার কেল্লা", "জয় বাবা ফেলুনাথ", "বাদশাহী আংটি", "গোরস্থানে সাবধান", "কৈলাসে কেলেঙ্কারি", "বাক্স রহস্য", "হত্যাকাণ্ড"],
            "wiki_page": "ফেলুদা",
        },
        {
            "bucket": "প্রফেসর শঙ্কু সিরিজ",
            "match_existing": ["শঙ্কু"],
            "keywords": ["শঙ্কু", "shonku", "shanku"],
            "wiki_page": "প্রফেসর শঙ্কু",
        },
        {
            "bucket": "তারিণীখুড়ো ও অন্যান্য গল্প",
            "match_existing": ["গল্প", "তারিণী", "সত্যজিৎ"],
            "keywords": ["তারিণী", "গল্প", "সমগ্র", "এক ডজন", "যখন ছোট ছিলাম", "একেই বলে শুটিং", "চিলম", "পিকুর ডায়েরী"],
        },
    ],
    "রকিব হাসান": [
        {
            "bucket": "তিন গোয়েন্দা সিরিজ",
            "match_existing": ["তিন গোয়েন্দা"],
            "keywords": ["তিন গোয়েন্দা", "tin goyenda", "কিশোর পাশা", "মুসা", "রবিন"],
            "wiki_page": "তিন গোয়েন্দা",
        },
        {
            "bucket": "কিশোর হরর ও রহস্য",
            "match_existing": ["হরর", "ভৌতিক", "রহস্য"],
            "keywords": ["হরর", "ভৌতিক", "ভূত", "ভূতের", "রহস্য", "অশরীরী", "পিশাচ", "ড্রাকুলা"],
        },
        {
            "bucket": "অ্যাডভেঞ্চার ও অনুবাদ",
            "match_existing": ["অ্যাডভেঞ্চার", "অনুবাদ"],
            "keywords": ["অ্যাডভেঞ্চার", "টারজান", "জুল ভার্ন", "অনুবাদ", "রবিনসন"],
        },
    ],
    "সুনীল গঙ্গোপাধ্যায়": [
        {
            "bucket": "কাকাবাবু সিরিজ",
            "match_existing": ["কাকাবাবু"],
            "keywords": ["কাকাবাবু", "kakababu", "সন্তু", "সবুজ দ্বীপের রাজা", "মিশর রহস্য", "পাহাড়চূড়ায় আতঙ্ক"],
            "wiki_page": "কাকাবাবু",
        },
        {
            "bucket": "কবিতা ও নীরা",
            "match_existing": ["কবিতা"],
            "keywords": ["কবিতা", "নীরা", "কাব্য", "হঠাৎ নীরার জন্য", "আমি কী রকম ভাবে বেঁচে আছি"],
        },
        {
            "bucket": "ঐতিহাসিক ও প্রধান উপন্যাস",
            "match_existing": ["উপন্যাস"],
            "keywords": ["প্রথম আলো", "সেই সময়", "পূর্ব-পশ্চিম", "পূর্ব পশ্চিম", "অরণ্যের দিনরাত্রি", "অর্জুন", "রাণু ও ভানু", "মনের মানুষ", "উপন্যাস"],
        },
    ],
    "সমরেশ মজুমদার": [
        {
            "bucket": "অনিমেষ সিরিজ",
            "match_existing": ["অনিমেষ"],
            "keywords": ["উত্তরাধিকার", "uttoradhikar", "কালবেলা", "kalbela", "কালপুরুষ", "kalpurush", "মৌষলকাল", "অনিমেষ"],
            "wiki_page": "সমরেশ মজুমদার",
        },
        {
            "bucket": "অর্জুন সিরিজ",
            "match_existing": ["অর্জুন"],
            "keywords": ["অর্জুন", "arjun"],
        },
        {
            "bucket": "উপন্যাস ও সমগ্র",
            "match_existing": ["উপন্যাস", "সমগ্র"],
            "keywords": ["সাতকাহন", "satkahon", "গর্ভধারিণী", "garbhodharini", "উপন্যাস", "সমগ্র", "আট কুঠুরি"],
        },
    ],
    "শীর্ষেন্দু মুখোপাধ্যায়": [
        {
            "bucket": "শবর দাশগুপ্ত সিরিজ",
            "match_existing": ["শবর"],
            "keywords": ["শবর", "ঋণ", "আলোর গল্প", "ঈগলের চোখ", "আশ্চর্য প্রদীপ"],
            "wiki_page": "শবর দাশগুপ্ত",
        },
        {
            "bucket": "অদ্ভুতুড়ে ও কিশোর উপন্যাস",
            "match_existing": ["কিশোর", "অদ্ভুতুড়ে"],
            "keywords": ["অদ্ভুতুড়ে", "গোসাঁই বাগানের ভূত", "মনোজদের অদ্ভুত বাড়ি", "পাগলা সাহেবের কবর", "পাতালঘর", "বক্সার রতন", "গৌরের কবচ", "হিরের আংটি", "কিশোর"],
            "wiki_page": "শীর্ষেন্দু মুখোপাধ্যায়",
        },
        {
            "bucket": "উপন্যাস ও গল্প",
            "match_existing": ["উপন্যাস", "গল্প"],
            "keywords": ["মানবজমিন", "দূরবীন", "পারাপার", "ঘুণপোকা", "উপন্যাস", "গল্প"],
        },
    ],
    "রবীন্দ্রনাথ ঠাকুর": [
        {
            "bucket": "কবিতা ও গীতবিতান",
            "match_existing": ["কবিতা", "গীতবিতান", "কাব্য"],
            "keywords": ["গীতাঞ্জলি", "gitanjali", "গীতবিতান", "সঞ্চয়িতা", "সোনার তরী", "বলাকা", "কবিতা", "গীতা", "পুরবী", "কথা ও কাহিনী", "নৈবেদ্য", "ক্ষণিকা"],
            "wiki_page": "রবীন্দ্রনাথ ঠাকুরের গ্রন্থপঞ্জি",
        },
        {
            "bucket": "উপন্যাস",
            "match_existing": ["উপন্যাস"],
            "keywords": ["গোরা", "চোখের বালি", "শেষের কবিতা", "ঘরে-বাইরে", "ঘরে বাইরে", "নৌকাডুবি", "চতুরঙ্গ", "যোগাযোগ", "রাজর্ষি", "বৌ-ঠাকুরাণীর হাট", "চার অধ্যায়", "মালঞ্চ", "দুই বোন"],
        },
        {
            "bucket": "গল্পগুচ্ছ ও ছোটগল্প",
            "match_existing": ["গল্প", "গল্পগুচ্ছ"],
            "keywords": ["গল্পগুচ্ছ", "গল্প", "সে", "গল্পসল্প", "লিপিকা", "কাবুলিওয়ালা", "পোস্টমাস্টার", "হৈমন্তী"],
        },
        {
            "bucket": "নাটক ও প্রহসন",
            "match_existing": ["নাটক"],
            "keywords": ["রক্তকরবী", "ডাকঘর", "অচলায়তন", "তাসের দেশ", "বিসর্জন", "মুক্তধারা", "চণ্ডালিকা", "শ্যামা", "চিত্রাঙ্গদা", "নাটক"],
        },
        {
            "bucket": "রচনাবলী ও প্রবন্ধ",
            "match_existing": ["রচনাবলী", "প্রবন্ধ"],
            "keywords": ["রচনাবলী", "রচনা", "প্রবন্ধ", "ছিন্নপত্র", "সভ্যতার সংকট", "জীবনস্মৃতি", "বিশ্বপরিচয়", "সহজ পাঠ", "শান্তিনিকেতন"],
        },
    ],
    "শরৎচন্দ্র চট্টোপাধ্যায়": [
        {
            "bucket": "উপন্যাস",
            "match_existing": ["উপন্যাস"],
            "keywords": ["শ্রীকান্ত", "দেবদাস", "দেবদাস", "পথের দাবী", "গৃহদাহ", "পল্লীসমাজ", "চরিত্রহীন", "পরিণীতা", "দত্তা", "বড়দিদি", "বিরাজবৌ", "বৈকুণ্ঠের উইল", "দেনা-পাওনা", "দেনাপাওনা", "শেষ প্রশ্ন", "চন্দ্রনাথ", "অরক্ষণীয়া"],
            "wiki_page": "শরৎচন্দ্র চট্টোপাধ্যায়",
        },
        {
            "bucket": "গল্প ও রচনাবলী",
            "match_existing": ["গল্প", "রচনাবলী", "সমগ্র"],
            "keywords": ["রচনাবলী", "সমগ্র", "গল্প", "মহেশ", "অভাগীর স্বর্গ", "বিন্দুর ছেলে", "মেজদিদি", "রামের সুমতি", "মামলার ফল"],
        },
    ],
    "বঙ্কিমচন্দ্র চট্টোপাধ্যায়": [
        {
            "bucket": "উপন্যাস",
            "match_existing": ["উপন্যাস"],
            "keywords": ["দুর্গেশনন্দিনী", "কপালকুণ্ডলা", "kopalkundola", "মৃণালিনী", "বিষবৃক্ষ", "চন্দ্রশেখর", "কৃষ্ণকান্তের উইল", "রাজসিংহ", "আনন্দমঠ", "দেবী চৌধুরানী", "সীতারাম", "রজনী", "ইন্দিরা"],
            "wiki_page": "বঙ্কিমচন্দ্র চট্টোপাধ্যায়",
        },
        {
            "bucket": "প্রবন্ধ ও রচনাবলী",
            "match_existing": ["প্রবন্ধ", "রচনাবলী"],
            "keywords": ["কমলাকান্ত", "কৃষ্ণচরিত্র", "বিবিধ প্রবন্ধ", "রচনাবলী", "সমগ্র", "বঙ্গদর্শন", "প্রবন্ধ"],
        },
    ],
    "কাজী নজরুল ইসলাম": [
        {
            "bucket": "কবিতা ও সঙ্গীত",
            "match_existing": ["কবিতা", "গীতি", "কাব্য"],
            "keywords": ["অগ্নিবীণা", "বিষের বাঁশী", "ভাঙার গান", "সাম্যবাদী", "সর্বহারা", "সিন্ধু-হিন্দোল", "দোলনচাঁপা", "ছায়ানট", "চক্রবাক", "সঞ্চিতা", "বুলবুল", "কবিতা", "নজরুল গীতি"],
            "wiki_page": "কাজী নজরুল ইসলামের গ্রন্থপঞ্জি",
        },
        {
            "bucket": "উপন্যাস, গল্প ও রচনাবলী",
            "match_existing": ["উপন্যাস", "গল্প", "রচনাবলী"],
            "keywords": ["বাঁধনহারা", "মৃত্যুক্ষুধা", "কুহেলিকা", "ব্যথার দান", "রিক্তের বেদন", "শিউলিমালা", "যুগবাণী", "রাজবন্দীর জবানবন্দী", "রচনাবলী", "সমগ্র"],
        },
    ],
    "হেমেন্দ্রকুমার রায়": [
        {
            "bucket": "জয়ন্ত-মানিক ও বিমল-কুমার সিরিজ",
            "match_existing": ["জয়ন্ত", "বিমল", "সিরিজ"],
            "keywords": ["জয়ন্ত", "মানিক", "বিমল", "কুমার", "যকের ধন", "আবার যকের ধন", "ময়নামতীর মায়াকানন", "মানুষ পিশাচ"],
        },
        {
            "bucket": "কিশোর রোমাঞ্চ ও রচনাবলী",
            "match_existing": ["কিশোর", "রচনাবলী", "সমগ্র"],
            "keywords": ["কিশোর", "সমগ্র", "রচনাবলী", "রহস্য", "ভৌতিক", "অ্যাডভেঞ্চার"],
        },
    ],
    "সৈয়দ মুস্তাফা সিরাজ": [
        {
            "bucket": "কর্নেল সিরিজ",
            "match_existing": ["কর্নেল"],
            "keywords": ["কর্নেল", "colonel"],
        },
        {
            "bucket": "উপন্যাস ও গল্প",
            "match_existing": ["উপন্যাস", "গল্প"],
            "keywords": ["অলীক মানুষ", "উপন্যাস", "গল্প", "সমগ্র"],
        },
    ],
    "নীহাররঞ্জন গুপ্ত": [
        {
            "bucket": "কিরীটী রায় সিরিজ",
            "match_existing": ["কিরীটী"],
            "keywords": ["কিরীটী", "kiriti", "কালো ভ্রমর", "উল্কা"],
        },
    ],
    "আরিফ আজাদ": [
        {
            "bucket": "প্যারাডক্সিক্যাল সাজিদ সিরিজ",
            "match_existing": ["সাজিদ"],
            "keywords": ["প্যারাডক্সিক্যাল সাজিদ", "paradoxical", "সাজিদ"],
        },
        {
            "bucket": "ইসলামিক প্রবন্ধ ও জীবনদর্শন",
            "match_existing": ["প্রবন্ধ", "বেলা"],
            "keywords": ["বেলা ফুরাবার আগে", "আরজ আলি সমীপে", "প্রত্যাবর্তন", "মা, মা, মা এবং বাবা", "জবাব", "নবী জীবনের গল্প"],
        },
    ],
}

GENERIC_AUTHOR_BUCKETS = [
    ("রচনাবলী ও সমগ্র", ["রচনাবলী", "রচনাসমগ্র", "সমগ্র", "রচনা সংকলন", "rachanabali", "samagra", "somogro", "omnibus"]),
    ("কবিতা", ["কবিতা", "কাব্য", "সনেট", "গীতবিতান", "kobita", "kabita", "poem"]),
    ("নাটক", ["নাটক", "প্রহসন", "নাট্যসমগ্র", "natok", "drama"]),
    ("গল্প ও ছোটগল্প", ["গল্প", "ছোটগল্প", "গল্পগুচ্ছ", "গল্পসমগ্র", "golpo", "galpo", "stories"]),
    ("ভ্রমণ ও আত্মজীবনী", ["ভ্রমণ", "আত্মজীবনী", "স্মৃতিকথা", "জীবনী", "bhromon", "jiboni"]),
    ("প্রবন্ধ ও গবেষণা", ["প্রবন্ধ", "অভিধান", "আলোচনা", "ইতিহাস", "probondho", "essay"]),
    ("উপন্যাস", ["উপন্যাস", "uponyas", "novel"]),
]


WIKI_BIBLIOGRAPHY_PAGES: dict[str, str] = {
    "হুমায়ূন আহমেদ": "হুমায়ূন আহমেদের গ্রন্থপঞ্জি",
    "মুহম্মদ জাফর ইকবাল": "মুহম্মদ জাফর ইকবালের গ্রন্থপঞ্জি",
    "রবীন্দ্রনাথ ঠাকুর": "রবীন্দ্রনাথ ঠাকুরের গ্রন্থপঞ্জি",
    "কাজী নজরুল ইসলাম": "কাজী নজরুল ইসলামের গ্রন্থপঞ্জি",
    "শরৎচন্দ্র চট্টোপাধ্যায়": "শরৎচন্দ্র চট্টোপাধ্যায়",
    "বঙ্কিমচন্দ্র চট্টোপাধ্যায়": "বঙ্কিমচন্দ্র চট্টোপাধ্যায়",
    "সুনীল গঙ্গোপাধ্যায়": "সুনীল গঙ্গোপাধ্যায়",
    "সমরেশ মজুমদার": "সমরেশ মজুমদার",
    "শীর্ষেন্দু মুখোপাধ্যায়": "শীর্ষেন্দু মুখোপাধ্যায়",
    "বিভূতিভূষণ বন্দ্যোপাধ্যায়": "বিভূতিভূষণ বন্দ্যোপাধ্যায়",
    "মানিক বন্দ্যোপাধ্যায়": "মানিক বন্দ্যোপাধ্যায়",
    "তারাশঙ্কর বন্দ্যোপাধ্যায়": "তারাশঙ্কর বন্দ্যোপাধ্যায়",
    "সত্যজিৎ রায়": "সত্যজিৎ রায়",
    "রকিব হাসান": "তিন গোয়েন্দা",
    "কাজী আনোয়ার হোসেন": "মাসুদ রানা",
}

WIKI_SECTION_TO_BUCKET = [
    ("হিমু", "হিমু সিরিজ"),
    ("মিসির", "মিসির আলি সিরিজ"),
    ("শুভ্র", "শুভ্র সিরিজ"),
    ("মুক্তিযুদ্ধ", "মুক্তিযুদ্ধ"),
    ("বৈজ্ঞানিক কল্প", "সায়েন্স ফিকশন ও রহস্য"),
    ("কল্পবিজ্ঞান", "সায়েন্স ফিকশন ও রহস্য"),
    ("সাইন্স ফিকশন", "সায়েন্স ফিকশন"),
    ("কিশোর", "কিশোর উপন্যাস ও গল্প"),
    ("ফেলুদা", "ফেলুদা সিরিজ"),
    ("শঙ্কু", "প্রফেসর শঙ্কু সিরিজ"),
    ("কাকাবাবু", "কাকাবাবু সিরিজ"),
    ("অনিমেষ", "অনিমেষ সিরিজ"),
    ("শবর", "শবর দাশগুপ্ত সিরিজ"),
    ("আত্মজীবনী", "ভ্রমণ, প্রবন্ধ ও আত্মজীবনী"),
    ("স্মৃতি", "ভ্রমণ, প্রবন্ধ ও আত্মজীবনী"),
    ("ভ্রমণ", "ভ্রমণ ও আত্মজীবনী"),
    ("নাটক", "নাটক"),
    ("কাব্য", "কবিতা"),
    ("কবিতা", "কবিতা"),
    ("গল্প", "গল্প ও ছোটগল্প"),
    ("প্রবন্ধ", "প্রবন্ধ ও গবেষণা"),
    ("উপন্যাস", "উপন্যাস"),
    ("রচনাবলী", "রচনাবলী ও সমগ্র"),
]


def fetch_wiki_section_titles(page: str, lang: str = "bn", timeout: int = 12) -> dict[str, list[str]]:
    """Parse Wikipedia wikitext sections to extract book titles grouped by genre/series section."""
    by_sec: dict[str, list[str]] = collections.defaultdict(list)
    try:
        url = f"https://{lang}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
            {"action": "parse", "page": page, "prop": "wikitext", "format": "json", "redirects": 1}
        )
        req = urllib.request.Request(url, headers={"User-Agent": "AnaBookSeriesOrganizer/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
        wikitext = data.get("parse", {}).get("wikitext", {}).get("*", "")
        cur_sec = "সাধারণ"
        for line in wikitext.splitlines():
            m_h = re.match(r"^\s*={2,4}\s*(.+?)\s*={2,4}\s*$", line)
            if m_h:
                cur_sec = re.sub(r"\[\[|\]\]|'+", "", m_h.group(1)).strip()
                continue
            # Extract [[Title|Alias]] or * Title / * ''Title''
            for link in re.findall(r"\[\[([^\]|#]+?)(?:\|([^\]]+?))?\]\]", line):
                cand = (link[1] or link[0]).strip()
                if BENGALI_RE.search(cand) and 2 <= len(cand) <= 55 and not re.search(r"চিত্র:|বিভাগ:|গ্রন্থপঞ্জি|সাহিত্য|তালিকা|পুরস্কার", cand):
                    by_sec[cur_sec].append(cand)
            m_li = re.match(r"^\s*[\*#]\s*(?:'''|'')?([^(\n\[]+)", line)
            if m_li:
                raw_t = re.sub(r"'+|<[^>]+>", "", m_li.group(1)).split("–")[0].split("-")[0].strip(" ,।:")
                if BENGALI_RE.search(raw_t) and 2 <= len(raw_t) <= 50 and not re.search(r"গ্রন্থপঞ্জি|সাহিত্য|তালিকা", raw_t):
                    by_sec[cur_sec].append(raw_t)
    except Exception:
        pass
    # Deduplicate preserving order
    return {sec: list(dict.fromkeys(vals)) for sec, vals in by_sec.items() if vals}


def fetch_wiki_page_titles(page: str, lang: str = "bn", timeout: int = 12) -> list[str]:
    secs = fetch_wiki_section_titles(page, lang=lang, timeout=timeout)
    out: list[str] = []
    for vals in secs.values():
        out.extend(vals)
    return list(dict.fromkeys(out))


def build_internet_series_catalog() -> dict[str, Any]:
    """Collect live Wikipedia section-grouped work lists for authors to strengthen classification & app metadata."""
    catalog: dict[str, Any] = {}
    wiki_dynamic_kws: dict[str, dict[str, list[str]]] = collections.defaultdict(lambda: collections.defaultdict(list))

    for author, page in WIKI_BIBLIOGRAPHY_PAGES.items():
        secs = fetch_wiki_section_titles(page, lang="bn")
        for sec_name, titles in secs.items():
            matched_bucket = None
            for sec_key, bucket_name in WIKI_SECTION_TO_BUCKET:
                if sec_key in sec_name:
                    matched_bucket = bucket_name
                    break
            if matched_bucket:
                wiki_dynamic_kws[author][matched_bucket].extend(titles)

    for author, buckets in AUTHOR_SERIES_RULES.items():
        author_entry: dict[str, Any] = {}
        for b in buckets:
            bname = b["bucket"]
            collected: list[str] = list(wiki_dynamic_kws.get(author, {}).get(bname, []))
            wiki_page = b.get("wiki_page") or WIKI_BIBLIOGRAPHY_PAGES.get(author, "")
            if wiki_page and not collected and b.get("wiki_page"):
                collected = fetch_wiki_page_titles(wiki_page, lang="bn")
            # Merge curated strong keywords + Wikipedia section titles into the rule in-memory
            if collected:
                existing_kw_set = {k.lower() for k in b["keywords"]}
                for t in collected:
                    if len(t) >= 3 and t.lower() not in existing_kw_set:
                        b["keywords"].append(t)
                        existing_kw_set.add(t.lower())
            author_entry[bname] = {
                "wiki_page": wiki_page,
                "wiki_links_collected": len(collected),
                "sample_titles": collected[:60],
            }
        catalog[author] = author_entry
    return catalog


def has_keyword(text: str, kw: str) -> bool:
    k = kw.lower().strip()
    t = text.lower()
    if not k or k not in t:
        return False
    if len(k) <= 6 and " " not in k:
        return bool(re.search(rf"(?:^|[\s\-—–_.,()\[\]/|]){re.escape(k)}(?:$|[\s\-—–_.,()\[\]/|]|ের|ে|র)", t))
    return True


def classify_book_for_author(
    author_name: str,
    title: str,
    existing_subfolders: list[dict[str, Any]],
) -> str | None:
    """Return exact target subfolder name inside the author's folder, or None."""
    if author_name in AUTHOR_SERIES_RULES:
        for rule in AUTHOR_SERIES_RULES[author_name]:
            if any(has_keyword(title, kw) for kw in rule["keywords"]):
                # Reuse existing subfolder if an equivalent name already exists
                for ex in existing_subfolders:
                    ex_low = ex["name"].lower()
                    if ex_low == rule["bucket"].lower() or any(m.lower() in ex_low for m in rule.get("match_existing", [])):
                        return ex["name"]
                return rule["bucket"]

    # Generic fallback ONLY if author folder is prolific (checked by caller)
    for bucket, kws in GENERIC_AUTHOR_BUCKETS:
        if any(has_keyword(title, kw) for kw in kws):
            for ex in existing_subfolders:
                if bucket.split()[0].lower() in ex["name"].lower():
                    return ex["name"]
            return bucket

    # If author already has an 'উপন্যাস' or 'অন্যান্য' subfolder and book doesn't match specific tags, leave unmoved unless clear
    return None


def _run_local_preview(repo_dir: Path, series_catalog: dict[str, Any]) -> dict[str, Any]:
    cat = json.loads((repo_dir / "books.json").read_text(encoding="utf-8"))
    cats, subs = cat["cats"], cat["subs"]
    by_author: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    existing_author_subs: dict[str, set[str]] = collections.defaultdict(set)

    for b in cat["books"]:
        fid, title, _auth, ci, si, *_ = b
        c_name = cats[ci] if 0 <= ci < len(cats) else ""
        s_name = subs[si] if 0 <= si < len(subs) else ""
        if c_name != "Authors & Scholars" or not s_name:
            continue
        parts = s_name.split("/")
        if parts[0] in ("Bangladeshi Authors", "International Authors") and len(parts) >= 2:
            author = parts[1]
            if len(parts) == 2:
                by_author[author].append({"id": fid, "title": title})
            else:
                existing_author_subs[author].add(parts[2])
        elif parts[0] == "Islamic Scholars" and len(parts) >= 3:
            author = parts[2]
            if len(parts) == 3:
                by_author[author].append({"id": fid, "title": title})
            else:
                existing_author_subs[author].add(parts[3])

    planned_moves = 0
    authors_planned: list[dict[str, Any]] = []
    for author, loose in by_author.items():
        if len(loose) < 12 and author not in AUTHOR_SERIES_RULES:
            continue
        ex_list = [{"name": n} for n in sorted(existing_author_subs.get(author, set()))]
        by_bucket: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
        for bk in loose:
            tgt = classify_book_for_author(author, bk["title"], ex_list)
            if tgt:
                by_bucket[tgt].append(bk)
        valid = {k: len(v) for k, v in by_bucket.items() if k in existing_author_subs[author] or len(v) >= 3}
        if valid:
            cnt = sum(valid.values())
            planned_moves += cnt
            authors_planned.append({"author": author, "loose_total": len(loose), "moves": cnt, "buckets": valid})

    return {
        "dry_run": True,
        "local_catalog_only": True,
        "authors_organized": len(authors_planned),
        "planned_moves": planned_moves,
        "details": sorted(authors_planned, key=lambda x: -x["moves"]),
        "series_catalog": series_catalog,
    }


def run_author_organizer(repo_dir: Path, dry_run: bool = False, local_catalog_only: bool = False) -> dict[str, Any]:
    print("[AuthorOrganizer] Collecting internet series & bibliography metadata from Wikipedia...", flush=True)
    series_catalog = build_internet_series_catalog()

    # Export enriched series catalog for App & Website
    for rel in ("App/assets/series_catalog.json", "visualize/public/series_catalog.json"):
        p = repo_dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(series_catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if local_catalog_only:
        res = _run_local_preview(repo_dir, series_catalog)
        reports_dir = repo_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        (reports_dir / "author_subfolders_report.json").write_text(
            json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps({"dry_run": True, "authors_organized": res["authors_organized"], "planned_moves": res["planned_moves"]}, indent=2), flush=True)
        return res

    # Live Google Drive mode: walk ONLY Authors & Scholars
    authors_root_id, authors_root_path = du.resolve_folder_path("Authors & Scholars")
    tree = du.walk_drive_tree(authors_root_id, base_prefix=authors_root_path, skip_top_folders=set())

    # Identify each author folder (level-2 under Bangladeshi/International Authors, or level-3 under Islamic Scholars)
    author_folders: list[dict[str, Any]] = []
    for fid, info in tree["folders_by_id"].items():
        parts = [p for p in info["path"].split("/") if p]
        if len(parts) == 3 and parts[1] in ("Bangladeshi Authors", "International Authors"):
            author_folders.append(info)
        elif len(parts) == 4 and parts[1] == "Islamic Scholars":
            author_folders.append(info)

    print(f"[AuthorOrganizer] Inspected {len(author_folders)} author folders on Drive.", flush=True)

    move_log: list[dict[str, Any]] = []
    folder_creations: list[dict[str, Any]] = []
    author_summaries: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    verified_moves = 0

    for ainfo in sorted(author_folders, key=lambda x: x["path"]):
        aid = ainfo["id"]
        aname = ainfo["name"]
        apath = ainfo["path"]
        kids = tree["children_by_folder"].get(aid, [])
        ex_subfolders = [k for k in kids if k.get("mimeType") == du.FOLDER_MIME]
        loose_books = [
            k for k in kids
            if k.get("mimeType") not in (du.FOLDER_MIME, du.SHORTCUT_MIME)
            and os.path.splitext(k.get("name", ""))[1].lower() in du.BOOK_EXTS
        ]

        if not loose_books:
            continue
        if len(loose_books) < 12 and aname not in AUTHOR_SERIES_RULES and not ex_subfolders:
            continue

        # Plan moves into buckets
        by_bucket: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
        for bk in loose_books:
            stem = os.path.splitext(bk["name"])[0]
            tgt = classify_book_for_author(aname, stem, ex_subfolders)
            if tgt:
                by_bucket[tgt].append(bk)

        existing_names = {sf["name"].lower(): sf for sf in ex_subfolders}
        active_buckets = {
            bname: blist for bname, blist in by_bucket.items()
            if bname.lower() in existing_names or len(blist) >= 3
        }
        if not active_buckets:
            continue

        author_moved = 0
        bucket_counts: dict[str, int] = {}
        for bname, blist in sorted(active_buckets.items()):
            if bname.lower() in existing_names:
                tgt_folder = existing_names[bname.lower()]
                created = False
            elif dry_run:
                tgt_folder = {"id": f"DRY_{bname}", "name": bname}
                created = True
            else:
                tgt_folder, created = du.find_or_create_folder(aid, bname, existing_children=kids, parent_path=apath)
                if created:
                    folder_creations.append(
                        {
                            "id": tgt_folder["id"],
                            "action": "create_folder",
                            "folder": apath,
                            "old_parent_id": aid,
                            "new_parent_id": aid,
                            "old_name": "",
                            "new_name": bname,
                            "category": "Authors & Scholars",
                        }
                    )
                    existing_names[bname.lower()] = tgt_folder

            # Cache destination sibling names to prevent name collision on move
            if dry_run or created:
                dest_names: set[str] = set()
            else:
                dest_children = tree["children_by_folder"].get(tgt_folder["id"], du.list_children(tgt_folder["id"]))
                dest_names = {c.get("name", "").lower() for c in dest_children}

            for bk in blist:
                if bk["name"].lower() in dest_names:
                    continue
                if dry_run:
                    move_log.append(
                        {
                            "id": bk["id"],
                            "action": "move",
                            "folder": f"{apath} -> {apath}/{bname}",
                            "old_parent_id": aid,
                            "new_parent_id": tgt_folder["id"],
                            "old_name": bk["name"],
                            "new_name": bk["name"],
                            "category": "Authors & Scholars",
                        }
                    )
                    dest_names.add(bk["name"].lower())
                    author_moved += 1
                    bucket_counts[bname] = bucket_counts.get(bname, 0) + 1
                    continue
                try:
                    du.drive_request(
                        "PATCH",
                        f"/files/{bk['id']}",
                        params={
                            "supportsAllDrives": "true",
                            "addParents": tgt_folder["id"],
                            "removeParents": aid,
                            "fields": "id,name,parents",
                        },
                    )
                    chk = du.drive_request(
                        "GET",
                        f"/files/{bk['id']}",
                        params={"supportsAllDrives": "true", "fields": "id,name,parents,trashed"},
                    )
                    if tgt_folder["id"] in (chk.get("parents") or []) and not chk.get("trashed", False):
                        verified_moves += 1
                    dest_names.add(bk["name"].lower())
                    author_moved += 1
                    bucket_counts[bname] = bucket_counts.get(bname, 0) + 1
                    move_log.append(
                        {
                            "id": bk["id"],
                            "action": "move",
                            "folder": f"{apath} -> {apath}/{bname}",
                            "old_parent_id": aid,
                            "new_parent_id": tgt_folder["id"],
                            "old_name": bk["name"],
                            "new_name": bk["name"],
                            "category": "Authors & Scholars",
                        }
                    )
                except Exception as exc:
                    errors.append({"id": bk["id"], "name": bk["name"], "error": str(exc)[:200]})

        if author_moved:
            author_summaries.append(
                {"author": aname, "path": apath, "loose_before": len(loose_books), "moved": author_moved, "subfolders": bucket_counts}
            )

    applied_at = dt.datetime.now(dt.timezone.utc).isoformat()
    all_entries = folder_creations + move_log
    cl_res = {"batch_id": "", "total_entries": 0}
    if not dry_run and all_entries:
        cl_res = du.update_rename_changelog(
            repo_dir, all_entries, applied_at, sync_drive=True, batch_id=du.make_batch_id(applied_at, "author_subs")
        )

    out = {
        "applied_at": applied_at,
        "dry_run": dry_run,
        "authors_organized": len(author_summaries),
        "folders_created": len(folder_creations),
        "books_moved": len(move_log),
        "verified_moves": verified_moves,
        "errors_count": len(errors),
        "batch_id": cl_res["batch_id"],
        "authors": author_summaries,
        "errors": errors,
    }
    reports_dir = repo_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "author_subfolders_report.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = [
        "# Author Subfolder & Series Organization Report",
        "",
        f"- **Timestamp (UTC):** `{applied_at}`",
        f"- **Dry Run:** `{dry_run}`",
        f"- **Authors Organized:** `{len(author_summaries)}`",
        f"- **Subfolders Created:** `{len(folder_creations)}`",
        f"- **Books Organized into Series/Genre Subfolders:** `{len(move_log)}` (verified: `{verified_moves}`)",
        "",
        "| Author | Loose Before | Moved | Subfolder Breakdown |",
        "|---|---:|---:|---|",
    ]
    for a in author_summaries:
        bd = ", ".join(f"{k}: {v}" for k, v in sorted(a["subfolders"].items()))
        md.append(f"| {a['author']} | {a['loose_before']} | {a['moved']} | {bd} |")
    (reports_dir / "author_subfolders_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k not in ("authors", "errors")}, indent=2), flush=True)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-dir", default=".")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--local-catalog-only", action="store_true")
    args = ap.parse_args()
    run_author_organizer(Path(args.repo_dir).resolve(), dry_run=args.dry_run, local_catalog_only=args.local_catalog_only)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
