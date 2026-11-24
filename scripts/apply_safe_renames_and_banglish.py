#!/usr/bin/env python3
"""
Stage 2:
1) safe_renames    — Applies ONLY the 262 verified safe renames in
                     reports/renamer/safe_stage_d_plan.json.
2) banglish_renames — Finds romanized Bengali (Banglish) book filenames
                     (e.g., 'Aj Ami Kothao Jabo Na.pdf' -> 'আজ আমি কোথাও যাব না.pdf')
                     while leaving genuine English/Arabic/uncertain titles untouched.

Never deletes files, never moves files, never touches English Books / Qawmi Madrasa / shortcuts,
preserves extensions, avoids same-folder collisions, verifies every Drive PATCH, and logs
all renames to Library Management/Reports/rename_changelog.{json,csv,md}.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import drive_utils as du  # noqa: E402

SKIP_BANGLISH_TOP = {"Library Management", "English Books", "Review & Unclassified"}
SKIP_BANGLISH_SUB = {"Qawmi Madrasa", "Other Religions"}
BENGALI_RE = re.compile(r"[\u0980-\u09FF]")
ARABIC_RE = re.compile(r"[\u0600-\u06FF]")

ENGLISH_STOP_WORDS = {
    "the", "and", "of", "for", "with", "from", "into", "about", "in", "on", "to", "by", "at", "an",
    "introduction", "guide", "manual", "handbook", "theory", "science", "sciences", "computer",
    "programming", "python", "java", "javascript", "typescript", "html", "css", "sql", "linux",
    "database", "network", "networking", "algorithm", "algorithms", "architecture", "system",
    "systems", "analysis", "design", "principles", "fundamentals", "engineering", "mechanical",
    "electrical", "civil", "medical", "clinical", "medicine", "surgery", "anatomy", "pathology",
    "pharmacology", "biology", "chemistry", "physics", "mathematics", "math", "algebra", "calculus",
    "statistics", "geometry", "economics", "accounting", "finance", "banking", "management",
    "marketing", "business", "history", "philosophy", "psychology", "sociology", "politics",
    "international", "law", "legal", "grammar", "vocabulary", "dictionary", "encyclopedia",
    "translation", "english", "oxford", "cambridge", "macmillan", "pearson", "springer",
    "mcgraw", "wiley", "penguin", "edition", "vol", "volume", "volumes", "part", "series",
    "complete", "collected", "works", "stories", "story", "novel", "novels", "poems", "poetry",
    "essays", "selected", "short", "modern", "basic", "advanced", "practical", "essential",
    "textbook", "question", "questions", "answer", "answers", "solution", "solutions", "suggestion",
    "model", "test", "exam", "admission", "university", "college", "school", "class", "chapter",
    "quran", "hadith", "islam", "islamic", "muslim", "muslims", "prophet", "muhammad", "biography",
    "tafsir", "tafseer", "fiqh", "seerah", "sirah", "aqidah", "aqeedah", "sunnah", "arabic",
    "urdu", "hindi", "persian", "sanskrit", "bible", "christian", "hindu", "hinduism", "buddhism",
    "gita", "vedas", "upanishad", "tripitaka", "bible", "testament", "gospel", "journal",
    "research", "thesis", "report", "paper", "lecture", "notes", "bcs", "hsc", "ssc", "jsc",
    "ielts", "toefl", "gre", "gmat", "sat", "pdf", "epub", "book", "books", "library",
    "blue", "lagoon", "godfather", "atlantis", "mafia", "big", "bang", "life", "paracetamol",
    "how", "can", "reduce", "surface", "tension", "water", "so", "says", "poet", "harry", "potter",
    "sherlock", "holmes", "tintin", "world", "war", "king", "queen", "secret", "mystery", "golden",
    "shadow", "operation", "target", "mission", "death", "black", "white", "red", "dark", "night",
    "never", "stop", "learning", "learn", "make", "become", "everything", "nothing", "something",
    "always", "before", "after", "between", "great", "best", "better", "good", "human", "power",
    "mind", "thinking", "habit", "habits", "rich", "poor", "money", "success", "smart", "simple",
    "art", "magic", "journey", "future", "beyond", "within", "without", "through", "people",
    "light", "sound", "land", "earth", "life", "love", "time", "days", "years", "road",
    "free", "open", "code", "data", "deep", "machine", "social", "media", "digital", "global",
    "public", "health", "kids", "child", "children", "parents", "family", "home", "work", "job",
}

# Unambiguous single or common Bengali romanizations (lowercase -> Bangla Unicode)
# Never add ambiguous English words like "man", "bar", "tin", "ami" (no, "ami" is safe in Bangla folders),
# "tar", "bat", "rat", "din" without context, unless strictly unambiguous in Bangla titles!
AMBIGUOUS_IF_ALONE = {
    "na", "e", "o", "ba", "ma", "ke", "ki", "se", "je", "ta", "ar", "ei", "oi", "ek", "du",
    "din", "rat", "raat", "ali", "ran", "pal", "das", "ray", "roy", "sen", "kar", "de",
    "mama", "nana", "dadu", "baba", "chacha", "kaka", "bala", "bali", "mala", "kala",
    "era", "are", "is", "no", "in", "on", "to", "a", "i", "go", "so", "do", "me", "my", "he",
    "she", "we", "us", "am", "an", "as", "at", "by", "of", "or", "up", "it",
}

BANGLISH_LEXICON: dict[str, str] = {
    # Pronouns & function words
    "ami": "আমি", "tumi": "তুমি", "amra": "আমরা", "amar": "আমার", "amader": "আমাদের",
    "tomar": "তোমার", "tomader": "তোমাদের", "tader": "তাদের", "apni": "আপনি", "apnar": "আপনার",
    "kothao": "কোথাও", "kothai": "কোথায়", "keu": "কেউ", "kew": "কেউ", "kichu": "কিছু",
    "kichui": "কিছুই", "shob": "সব", "sob": "সব", "sobuj": "সবুজ", "shobai": "সবাই",
    "sobai": "সবাই", "ekjon": "একজন", "ekti": "একটি", "ekta": "একটা", "ekhon": "এখন",
    "jokhon": "যখন", "tokhon": "তখন", "kakhono": "কখনো", "kokhono": "কখনো", "jabo": "যাব",
    "jabe": "যাবে", "jacchi": "যাচ্ছি", "jachi": "যাচ্ছি", "eshe": "এসে", "ese": "এসে",
    "asche": "আসছে", "ashche": "আসছে", "ache": "আছে", "ase": "আছে", "achhe": "আছে",
    "chilo": "ছিল", "chhilo": "ছিল", "thakbe": "থাকবে", "hobe": "হবে", "hoye": "হয়ে",
    "hoyeche": "হয়েছে", "hoyechhe": "হয়েছে", "kore": "করে", "koro": "করো", "kori": "করি",
    "bollo": "বলল", "bole": "বলে", "kohen": "কহেন", "kono": "কোনো", "kon": "কোন",
    "nei": "নেই", "nai": "নাই", "ebong": "এবং", "abong": "এবং", "othoba": "অথবা",
    "kintu": "কিন্তু", "tobe": "তবে", "jodi": "যদি", "jeno": "যেন", "jemon": "যেমন",
    "ebhabe": "এভাবে", "shei": "সেই", "sei": "সেই", "ei": "এই", "oi": "ওই", "na": "না",
    "shudhu": "শুধু", "sudhu": "শুধু", "matro": "মাত্র", "aro": "আরো", "aar": "আর",
    "arek": "আরেক", "arekjon": "আরেকজন", "prothom": "প্রথম", "dwitiyo": "দ্বিতীয়",
    "ditiyo": "দ্বিতীয়", "tritiyo": "তৃতীয়", "sesh": "শেষ", "shesh": "শেষ", "shesher": "শেষের",
    "sesher": "শেষের", "aj": "আজ", "aaj": "আজ", "ajker": "আজকের", "kal": "কাল",
    "kalke": "কালকে", "goto": "গত", "gotokal": "গতকাল", "porer": "পরের", "ager": "আগের",

    # Literary genres, series & common Bangla book terms
    "uponyas": "উপন্যাস", "uponnyas": "উপন্যাস", "uponash": "উপন্যাস",
    "golpo": "গল্প", "galpo": "গল্প", "chotogolpo": "ছোটগল্প", "chhotogolpo": "ছোটগল্প",
    "golpoguccho": "গল্পগুচ্ছ", "golpoguchchho": "গল্পগুচ্ছ",
    "kobita": "কবিতা", "kabita": "কবিতা", "kabyo": "কাব্য", "kabyogrontho": "কাব্যগ্রন্থ",
    "probondho": "প্রবন্ধ", "prabandha": "প্রবন্ধ", "natok": "নাটক", "natak": "নাটক",
    "rochona": "রচনা", "rachana": "রচনা", "rochonaboli": "রচনাবলী", "rachanabali": "রচনাবলী",
    "somogro": "সমগ্র", "samagra": "সমগ্র", "shomogro": "সমগ্র", "shomogroho": "সংগ্রহ",
    "songroho": "সংগ্রহ", "sonkolon": "সংকলন", "sankalan": "সংকলন",
    "onubad": "অনুবাদ", "anubad": "অনুবাদ", "onudito": "অনূদিত",
    "jiboni": "জীবনী", "jibani": "জীবনী", "atmojiboni": "আত্মজীবনী", "smritikotha": "স্মৃতিকথা",
    "bhromon": "ভ্রমণ", "bhromonkahini": "ভ্রমণকাহিনী", "itihas": "ইতিহাস", "itihash": "ইতিহাস",
    "bishoyok": "বিষয়ক", "shompadito": "সম্পাদিত", "sompadito": "সম্পাদিত",
    "kishore": "কিশোর", "kishor": "কিশোর", "shishu": "শিশু", "rupkotha": "রূপকথা",
    "bhooter": "ভূতের", "bhoot": "ভূত", "bhut": "ভূত", "premer": "প্রেমের", "prem": "প্রেম",
    "bhalobasha": "ভালোবাসা", "valobasha": "ভালোবাসা", "bhalobashar": "ভালোবাসার",
    "goyenda": "গোয়েন্দা", "rohosso": "রহস্য", "rohosyo": "রহস্য", "rahasya": "রহস্য",
    "ovijan": "অভিযান", "obhijan": "অভিযান", "avijan": "অভিযান", "kahini": "কাহিনী",

    # Famous characters & author names in Banglish
    "humayun": "হুমায়ূন", "ahmed": "আহমেদ", "humayunahmed": "হুমায়ূন আহমেদ",
    "himu": "হিমু", "himur": "হিমুর", "misir": "মিসির", "ali": "আলি", "shuvro": "শুভ্র",
    "masud": "মাসুদ", "rana": "রানা", "feluda": "ফেলুদা", "feludar": "ফেলুদার",
    "shonku": "শঙ্কু", "kakababu": "কাকাবাবু", "kakababur": "কাকাবাবুর",
    "byomkesh": "ব্যোমকেশ", "bakshi": "বক্সী", "kiriti": "কিরীটী", "ghanada": "ঘনাদা",
    "tenida": "টেনিদা", "pagla": "পাগলা", "dashu": "দাশু", "gopal": "গোপাল", "bhar": "ভাঁড়",
    "rabindranath": "রবীন্দ্রনাথ", "robindronath": "রবীন্দ্রনাথ", "tagore": "ঠাকুর",
    "thakur": "ঠাকুর", "nazrul": "নজরুল", "nojrol": "নজরুল", "nojrul": "নজরুল",
    "sharat": "শরৎ", "sarat": "শরৎ", "chandra": "চন্দ্র", "chattopadhyay": "চট্টোপাধ্যায়",
    "zafar": "জাফর", "iqbal": "ইকবাল", "jafor": "জাফর", "ekbal": "ইকবাল",
    "satyajit": "সত্যজিৎ", "sotyojit": "সত্যজিৎ", "rakib": "রকিব", "hasan": "হাসান",
    "qazi": "কাজী", "anowar": "আনোয়ার", "anwar": "আনোয়ার", "hossain": "হোসেন", "hussain": "হোসেন",
    "sunil": "সুনীল", "gangopadhyay": "গঙ্গোপাধ্যায়", "samaresh": "সমরেশ", "majumdar": "মজুমদার",
    "shirshendu": "শীর্ষেন্দু", "sukumar": "সুকুমার", "kalidash": "কালিদাস", "kalidas": "কালিদাস",

    # Nouns, adjectives & verbs very frequent in Bangla book titles
    "akash": "আকাশ", "akashe": "আকাশে", "akasher": "আকাশের", "alo": "আলো", "alor": "আলোর",
    "andhar": "আঁধার", "adhar": "আঁধার", "ondhokar": "অন্ধকার", "ondhokarer": "অন্ধকারের",
    "angul": "আঙুল", "kata": "কাটা", "jaglu": "জগলু", "badol": "বাদল", "badol": "বাদল",
    "diner": "দিনের", "din": "দিন", "kodom": "কদম", "phul": "ফুল", "ful": "ফুল",
    "brishti": "বৃষ্টি", "bristi": "বৃষ্টি", "bilash": "বিলাস", "bilas": "বিলাস",
    "moyurakkhi": "ময়ূরাক্ষী", "mayurakshi": "ময়ূরাক্ষী", "ochinpur": "অচিনপুর", "achinpur": "অচিনপুর",
    "kuhurani": "কুহুরানী", "mojar": "মজার", "jol": "জল", "joler": "জলের",
    "pahar": "পাহাড়", "paharer": "পাহাড়ের", "nodi": "নদী", "nodir": "নদীর", "nodimotrika": "নদীমাতৃকা",
    "desh": "দেশ", "desher": "দেশের", "bangla": "বাংলা", "banglar": "বাংলার",
    "bangladesh": "বাংলাদেশ", "bangladesher": "বাংলাদেশের", "bangali": "বাঙালি",
    "gram": "গ্রাম", "gramer": "গ্রামের", "shohor": "শহর", "sohor": "শহর", "shohorer": "শহরের",
    "manush": "মানুষ", "manusher": "মানুষের", "manob": "মানব", "shomaj": "সমাজ", "somaj": "সমাজ",
    "shomoy": "সময়", "somoy": "সময়", "somoysima": "সময়সীমা", "modhya": "মধ্য", "modhyo": "মধ্য",
    "rat": "রাত", "raat": "রাত", "rater": "রাতের", "raater": "রাতের", "shokal": "সকাল", "sokal": "সকাল",
    "bikel": "বিকাল", "bikal": "বিকাল", "shondhya": "সন্ধ্যা", "sondhya": "সন্ধ্যা",
    "dupur": "দুপুর", "dupurer": "দুপুরের", "boshonto": "বসন্ত", "bosonto": "বসন্ত",
    "shorot": "শরৎ", "hemonto": "হেমন্ত", "sheet": "শীত", "grishmo": "গ্রীষ্ম",
    "meghe": "মেঘে", "megh": "মেঘ", "megher": "মেঘের", "chand": "চাঁদ", "chander": "চাঁদের",
    "josna": "জোছনা", "jochona": "জোছনা", "jyotsna": "জ্যোৎস্না", "tara": "তারা", "tarar": "তারার",
    "surjo": "সূর্য", "shurjo": "সূর্য", "shurjer": "সূর্যের", "prithibi": "পৃথিবী", "prithibir": "পৃথিবীর",
    "shona": "সোনা", "shonar": "সোনার", "sonar": "সোনার", "rupa": "রূপা", "rupor": "রূপোর",
    "kotha": "কথা", "kothar": "কথার", "gaan": "গান", "gan": "গান", "ganer": "গানের",
    "chokh": "চোখ", "chokher": "চোখের", "bali": "বালি", "mon": "মন", "moner": "মনের",
    "hridoy": "হৃদয়", "hridoyer": "হৃদয়ের", "jibon": "জীবন", "jiboner": "জীবনের",
    "mrityu": "মৃত্যু", "mrityur": "মৃত্যুর", "mrityubeez": "মৃত্যুবীজ", "ghanta": "ঘণ্টা",
    "moron": "মরণ", "moroner": "মরণের", "shukh": "সুখ", "sukher": "সুখের", "dukkho": "দুঃখ",
    "dukho": "দুঃখ", "hasi": "হাসি", "kanna": "কান্না", "shopno": "স্বপ্ন", "swopno": "স্বপ্ন",
    "ashar": "আশার", "asha": "আশা", "nirasha": "নিরাশা", "bismoy": "বিস্ময়",
    "bondhu": "বন্ধু", "bondhur": "বন্ধুর", "bondhutto": "বন্ধুত্ব", "shotru": "শত্রু",
    "bhoy": "ভয়", "voy": "ভয়", "bhoyonkor": "ভয়ংকর", "atonko": "আতঙ্ক", "atanko": "আতঙ্ক",
    "bibhishika": "বিভীষিকা", "chaya": "ছায়া", "chhaya": "ছায়া", "maya": "মায়া",
    "rakto": "রক্ত", "rokto": "রক্ত", "rokter": "রক্তের", "raktolalosha": "রক্তলালসা",
    "roktochosha": "রক্তচোষা", "harano": "হারানো", "khuje": "খুঁজে", "paowa": "পাওয়া",
    "shwarnotori": "স্বর্ণতরী", "swarnotori": "স্বর্ণতরী", "shokuner": "শকুনের",
    "arokkhito": "অরক্ষিত", "joloshima": "জলসীমা", "jonmovumi": "জন্মভূমি", "jonmobhumi": "জন্মভূমি",
    "proloy": "প্রলয়", "songket": "সংকেত", "sanket": "সংকেত", "palao": "পালাও",
    "boro": "বড়", "choto": "ছোট", "chhoto": "ছোট", "notun": "নতুন", "purono": "পুরনো",
    "khudha": "ক্ষুধা", "trishna": "তৃষ্ণা", "nirapod": "নিরাপদ", "karagar": "কারাগার",
    "shonkhonil": "শঙ্খনীল", "nondito": "নন্দিত", "noroke": "নরকে", "daruchini": "দারুচিনি",
    "dwip": "দ্বীপ", "rupali": "রূপালী", "gouripur": "গৌরীপুর", "junction": "জংশন",
    "debi": "দেবী", "devi": "দেবী", "nishithini": "নিশীথিনী", "nishad": "নিষাদ",
    "onnyobhubon": "অন্যভুবন", "brihonnola": "বৃহন্নলা", "pichash": "পিচাশ", "pishach": "পিশাচ",
    "matal": "মাতাল", "haoa": "হাওয়া", "hawa": "হাওয়া", "shrabon": "শ্রাবণ", "srabon": "শ্রাবণ",
    "ekattor": "একাত্তর", "ekattorer": "একাত্তরের", "muktijuddho": "মুক্তিযুদ্ধ",
    "birjoddha": "বীরযোদ্ধা", "shohid": "শহীদ", "shahid": "শহীদ", "swadhinota": "স্বাধীনতা",
    "gonohotta": "গণহত্যা", "shoshrosto": "সশস্ত্র", "soshrosto": "সশস্ত্র", "bahinite": "বাহিনীতে",
    "bahini": "বাহিনী", "jati": "জাতি", "jatir": "জাতির", "dunia": "দুনিয়া", "duniar": "দুনিয়ার",
    "kapano": "কাঁপানো", "dosh": "দশ", "sahasra": "সহস্র", "shohosro": "সহস্র", "ek": "এক",
    "arabya": "আরব্য", "arobyo": "আরব্য", "rajani": "রজনী", "rojoni": "রজনী",
    "pother": "পথের", "pather": "পথের", "panchali": "পাঁচালী", "dabi": "দাবী",
    "apomoy": "অপময়", "paracetamol": "প্যারাসিটামল", "peramoy": "প্যারাময়", "paracetamol": "প্যারাসিটামল",
    "abzab": "আবজাব", "namibe": "নামিবে", "nambe": "নামবে", "bhabna": "ভাবনা",
    "chinta": "চিন্তা", "kothokota": "কথকতা", "shatkahon": "সাতকাহন", "satkahon": "সাতকাহন",
    "uttara": "উত্তরা", "uttoradhikar": "উত্তরাধিকার", "kalbela": "কালবেলা", "kalpurush": "কালপুরুষ",
    "garbhodharini": "গর্ভধারিণী", "ardhek": "অর্ধেক", "manobi": "মানবী", "arjun": "অর্জুন",
    "tithir": "তিথির", "neel": "নীল", "nil": "নীল", "lal": "লাল", "kalo": "কালো", "shada": "সাদা",
    "sada": "সাদা", "holud": "হলুদ", "shobuj": "সবুজ", "shobuj": "সবুজ", "ronge": "রঙে", "rongin": "রঙিন",
    "rong": "রং", "paath": "পাঠ", "shiksha": "শিক্ষা", "shikkha": "শিক্ষা", "biggan": "বিজ্ঞান",
    "bigyan": "বিজ্ঞান", "gonit": "গণিত", "byakoron": "ব্যাকরণ", "bekoron": "ব্যাকরণ",
    "kothon": "কথন", "kothok": "কথক", "golpokar": "গল্পকার", "lekhok": "লেখক",
    "pathok": "পাঠক", "chithi": "চিঠি", "chithipotro": "চিঠিপত্র", "dayari": "ডায়েরি",
    "tithir": "তিথির", "toyale": "তোয়ালে", "chilam": "ছিলাম", "chhilam": "ছিলাম",
    "shagorer": "সাগরের", "sagorer": "সাগরের", "dhew": "ঢেউ", "dheu": "ঢেউ",
    "sahitto": "সাহিত্য", "shahitto": "সাহিত্য", "andhoprem": "অন্ধপ্রেম", "nokol": "নকল",
    "nakal": "নকল", "mig": "মিগ", "silet": "সিলেট", "sylhet": "সিলেট",
    "sattyajit": "সত্যজিৎ", "sattyajitray": "সত্যজিৎ রায়", "satyajitray": "সত্যজিৎ রায়",
    "kagoj": "কাগজ", "kolom": "কলম", "boi": "বই", "boimela": "বইমেলা",
    "paribarik": "পারিবারিক", "poribar": "পরিবার", "shongshar": "সংসার", "songsari": "সংসারী",
    "ghar": "ঘর", "ghor": "ঘর", "baire": "বাইরে", "ghore": "ঘরে", "bhitore": "ভিতরে",
    "pakhi": "পাখি", "pakhir": "পাখির", "gach": "গাছ", "fuler": "ফুলের", "bagan": "বাগান",
    "pukur": "পুকুর", "samudro": "সমুদ্র", "shomudro": "সমুদ্র", "sagor": "সাগর", "shagor": "সাগর",
    "jhor": "ঝড়", "batash": "বাতাস", "pani": "পানি", "agun": "আগুন", "mati": "মাটি",
    "akash": "আকাশ", "meghla": "মেঘলা", "borsha": "বর্ষা", "barsha": "বর্ষা",
    "ekush": "একুশ", "ekushe": "একুশে", "ekushey": "একুশে", "bijoy": "বিজয়",
    "swopner": "স্বপ্নের", "shopner": "স্বপ্নের", "raja": "রাজা", "rani": "রানী", "rajpurohit": "রাজপুরোহিত",
    "rakhosh": "রাক্ষস", "rakkhash": "রাক্ষস", "pari": "পরী", "pori": "পরী", "jadu": "জাদু",
    "jadukor": "জাদুকর", "bhoyonkor": "ভয়ঙ্কর", "adbhut": "অদ্ভুত", "odbhut": "অদ্ভুত",
    "ashchorjo": "আশ্চর্য", "ascharya": "আশ্চর্য", "chomotkar": "চমৎকার", "shundor": "সুন্দর",
    "sundor": "সুন্দর", "valo": "ভালো", "bhalo": "ভালো", "kharap": "খারাপ", "mora": "মরা",
    "bancha": "বাঁচা", "bacha": "বাঁচা", "hashi": "হাসি", "kothin": "কঠিন", "shohoj": "সহজ",
    "sohoj": "সহজ", "durgom": "দুর্গম", "duronto": "দুরন্ত", "pagol": "পাগল", "madhuri": "মাধুরী",
    "anondo": "আনন্দ", "ananda": "আনন্দ", "bedona": "বেদনা", "biroho": "বিরহ",
    "milon": "মিলন", "onuvuti": "অনুভূতি", "anubhuti": "অনুভূতি", "bichar": "বিচার",
    "bishoy": "বিষয়", "proshno": "প্রশ্ন", "uttor": "উত্তর", "shomadhan": "সমাধান",
}

# Exact famous lowercase Banglish phrase overrides (stem/core -> canonical Bangla)
CURATED_PHRASE_MAP: dict[str, str] = {
    "aj ami kothao jabo na": "আজ আমি কোথাও যাব না",
    "aaj ami kothao jabo na": "আজ আমি কোথাও যাব না",
    "kothao keu nei": "কোথাও কেউ নেই",
    "moyurakkhi": "ময়ূরাক্ষী",
    "ochinpur": "অচিনপুর",
    "achinpur": "অচিনপুর",
    "debi": "দেবী",
    "nishithini": "নিশীথিনী",
    "himu mama": "হিমু মামা",
    "himur ache jol": "হিমুর আছে জল",
    "brishti bilash": "বৃষ্টি বিলাস",
    "badol diner dwitiyo kodom phul": "বাদল দিনের দ্বিতীয় কদম ফুল",
    "kohen kobi kalidash": "কহেন কবি কালিদাস",
    "kohen kobi kalidas": "কহেন কবি কালিদাস",
    "misir ali bishoyok rochona jokhon namibe adhar": "যখন নামিবে আঁধার (মিসির আলি)",
    "jokhon namibe adhar": "যখন নামিবে আঁধার",
    "angul kata jaglu": "আঙুল কাটা জগলু",
    "mojar bhoot": "মজার ভূত",
    "kuhurani": "কুহুরানী",
    "shesher kobita": "শেষের কবিতা",
    "sesher kobita": "শেষের কবিতা",
    "gitanjali": "গীতাঞ্জলি",
    "chokher bali": "চোখের বালি",
    "ghore baire": "ঘরে-বাইরে",
    "gora": "গোরা",
    "noukadubi": "নৌকাডুবি",
    "pother panchali": "পথের পাঁচালী",
    "pather panchali": "পথের পাঁচালী",
    "chander pahar": "চাঁদের পাহাড়",
    "devdas": "দেবদাস",
    "srikanta": "শ্রীকান্ত",
    "pather dabi": "পথের দাবী",
    "padma nodir majhi": "পদ্মা নদীর মাঝি",
    "lalsalu": "লালসালু",
    "bishad shindhu": "বিষাদ সিন্ধু",
    "hajar bochor dhore": "হাজার বছর ধরে",
    "ekattorer dinguli": "একাত্তরের দিনগুলি",
    "ekattorer birjoddha": "একাত্তরের বীরযোদ্ধা",
    "deshe bideshe": "দেশে বিদেশে",
    "panchatantra": "পঞ্চতন্ত্র",
    "chacha kahini": "চাচা কাহিনী",
    "shonkhonil karagar": "শঙ্খনীল কারাগার",
    "nondito noroke": "নন্দিত নরকে",
    "daruchini dwip": "দারুচিনি দ্বীপ",
    "amar ache jol": "আমার আছে জল",
    "amra sei se jati": "আমরা সেই সে জাতি",
    "shoshrosto bahinite gonohotta": "সশস্ত্র বাহিনীতে গণহত্যা",
    "sahasra ak arabya rajani": "সহস্র এক আরব্য রজনী",
    "dunia kapano dosh din": "দুনিয়া কাঁপানো দশ দিন",
    "satkahon": "সাতকাহন",
    "garbhodharini": "গর্ভধারিণী",
    "kalbela": "কালবেলা",
    "kalpurush": "কালপুরুষ",
    "uttoradhikar": "উত্তরাধিকার",
    "golpoguccho": "গল্পগুচ্ছ",
    "paracetamol": "প্যারাময় লাইফের প্যারাসিটামল",
}

AUTHOR_WIKI_PAGES = [
    "হুমায়ূন আহমেদ",
    "হুমায়ূন আহমেদের গ্রন্থপঞ্জি",
    "মুহম্মদ জাফর ইকবাল",
    "মুহম্মদ জাফর ইকবালের গ্রন্থপঞ্জি",
    "রবীন্দ্রনাথ ঠাকুরের গ্রন্থপঞ্জি",
    "শরৎচন্দ্র চট্টোপাধ্যায়",
    "কাজী নজরুল ইসলামের গ্রন্থপঞ্জি",
    "সত্যজিৎ রায়",
    "সুনীল গঙ্গোপাধ্যায়",
    "সমরেশ মজুমদার",
    "শীর্ষেন্দু মুখোপাধ্যায়",
    "বিভূতিভূষণ বন্দ্যোপাধ্যায়",
    "বঙ্কিমচন্দ্র চট্টোপাধ্যায়",
    "মানিক বন্দ্যোপাধ্যায়",
    "তারাশঙ্কর বন্দ্যোপাধ্যায়",
    "জহির রায়হান",
    "আহমদ ছফা",
    "হুমায়ুন আজাদ",
    "সৈয়দ মুজতবা আলী",
    "কাজী আনোয়ার হোসেন",
    "রকিব হাসান",
    "আনিসুল হক",
    "মাসুদ রানা",
    "মিসির আলি",
    "হিমু (চরিত্র)",
    "তিন গোয়েন্দা",
    "ফেলুদা",
    "কাকাবাবু",
]

# Simple Bengali script -> normalized consonant-vowel Latin skeleton for cross-script dictionary matching
_BN_MAP = {
    "অ": "o", "আ": "a", "ই": "i", "ঈ": "i", "উ": "u", "ঊ": "u", "ঋ": "ri", "এ": "e", "ঐ": "oi",
    "ও": "o", "ঔ": "ou",
    "া": "a", "ি": "i", "ী": "i", "ু": "u", "ূ": "u", "ৃ": "ri", "ে": "e", "ৈ": "oi", "ো": "o", "ৌ": "ou",
    "ক": "k", "খ": "kh", "গ": "g", "ঘ": "gh", "ঙ": "ng",
    "চ": "ch", "ছ": "ch", "জ": "j", "ঝ": "jh", "ঞ": "n",
    "ট": "t", "ঠ": "th", "ড": "d", "ঢ": "dh", "ণ": "n",
    "ত": "t", "থ": "th", "দ": "d", "ধ": "dh", "ন": "n",
    "প": "p", "ফ": "f", "ব": "b", "ভ": "bh", "ম": "m",
    "য": "j", "র": "r", "ল": "l", "শ": "sh", "ষ": "sh", "স": "s", "হ": "h",
    "ড়": "r", "ঢ়": "rh", "য়": "y", "ৎ": "t", "ং": "ng", "ঃ": "h", "ঁ": "n",
}


def phonetic_skeleton(text: str) -> str:
    """Reduce both Bangla Unicode text and Latin Banglish text to comparable phonetic skeletons."""
    s = unicodedata.normalize("NFC", text or "").strip()
    if BENGALI_RE.search(s):
        out = []
        for ch in s:
            if ch in _BN_MAP:
                out.append(_BN_MAP[ch])
            elif ch == "্":
                continue
            elif ch.isalnum() or ch.isspace():
                out.append(ch.lower())
            else:
                out.append(" ")
        raw = "".join(out)
    else:
        raw = s.lower()
    raw = re.sub(r"ph", "f", raw)
    raw = re.sub(r"v", "bh", raw)
    raw = re.sub(r"oo", "u", raw)
    raw = re.sub(r"ee", "i", raw)
    raw = re.sub(r"au|ou", "o", raw)
    raw = re.sub(r"sh", "s", raw)
    raw = re.sub(r"chh?", "ch", raw)
    raw = re.sub(r"([a-z])\1+", r"\1", raw)
    # Retain initial digraphs and distinct non-schwa vowels (i, u, e) so Kamal != Komol / Hossain != Hasan
    words = []
    for w in re.findall(r"[a-z0-9]+", raw):
        if len(w) >= 4:
            words.append(w[:2] + re.sub(r"[ao]", "", w[2:]))
        else:
            words.append(w)
    return " ".join(words)


def _clean_bn_canonical(title: str) -> str:
    t = re.sub(r"\s*\([^)]*\)$", "", title).strip()
    # Strip catalog list numbering like '০৮। ', '১০২। ', '5. '
    t = re.sub(r"^[০-৯0-9]{1,3}\s*[।.\-:)]\s*", "", t).strip()
    # Strip catalog trailing volume tag like ' - ১', ' - ০১', ' - ৫'
    t = re.sub(r"[\s\-—–]+(?:[০-৯]{1,2}|[0-9]{1,2})$", "", t).strip()
    return t


def fetch_bn_wikipedia_titles(timeout: int = 12) -> list[str]:
    """Fetch quoted/italicized/linked book titles from key Bangla Wikipedia pages."""
    titles: set[str] = set()
    for page in AUTHOR_WIKI_PAGES:
        try:
            url = (
                "https://bn.wikipedia.org/w/api.php?"
                + urllib.parse.urlencode(
                    {
                        "action": "parse",
                        "page": page,
                        "prop": "links",
                        "format": "json",
                        "redirects": 1,
                    }
                )
            )
            req = urllib.request.Request(url, headers={"User-Agent": "AnaBookLibraryOrganizer/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read())
            for lk in data.get("parse", {}).get("links", []):
                if lk.get("ns") == 0:
                    t = lk.get("*", "").strip()
                    if BENGALI_RE.search(t) and 2 <= len(t) <= 65 and not re.search(r"গ্রন্থপঞ্জি|সাহিত্য|চলচ্চিত্র|পুরস্কার|তালিকা", t):
                        titles.add(t)
        except Exception:
            continue
    return sorted(titles)


def build_canonical_bn_index(repo_dir: Path, extra_bn_titles: list[str] | None = None) -> dict[str, str]:
    """
    Build skeleton -> canonical Bangla title lookup from:
    1) Curated famous titles
    2) Existing Bangla titles already in repo books.json
    3) Bangla Wikipedia bibliography links
    """
    index: dict[str, str] = {}
    counts: collections.Counter[tuple[str, str]] = collections.Counter()

    # Load from local books.json first
    cat_path = repo_dir / "books.json"
    if cat_path.exists():
        cat = json.loads(cat_path.read_text(encoding="utf-8"))
        for b in cat.get("books", []):
            title = (b[1] or "").strip()
            if BENGALI_RE.search(title) and not re.search(r"[A-Za-z]{4,}", title):
                clean = _clean_bn_canonical(re.split(r"\s+[-—]\s+", title)[0].strip())
                if 3 <= len(clean) <= 65:
                    sk = phonetic_skeleton(clean)
                    if len(sk.split()) >= 1 and len(sk.replace(" ", "")) >= 5:
                        counts[(sk, clean)] += 1

    # Most common Bangla spelling wins per phonetic skeleton
    for (sk, clean), _cnt in counts.most_common():
        index.setdefault(sk, clean)

    for t in (extra_bn_titles or []):
        clean = _clean_bn_canonical(t)
        if 3 <= len(clean) <= 65:
            sk = phonetic_skeleton(clean)
            if len(sk.split()) >= 2 or len(sk.replace(" ", "")) >= 6:
                index.setdefault(sk, clean)

    return index


def split_banglish_filename(filename: str) -> tuple[str, str, str, str]:
    """
    Separate (prefix_tags, title_core, suffix_tags, ext).
    Example: 'HumayunAhmed Himu Mama [2004].pdf' -> ('', 'Himu Mama', '[2004] - হুমায়ূন আহমেদ', '.pdf')
    """
    stem, ext = os.path.splitext(filename)
    work = stem.strip()
    prefix_parts: list[str] = []
    suffix_parts: list[str] = []

    # Strip known website noise tags cleanly
    work = re.sub(r"\[?\s*(?:www\.)?[a-z0-9-]+\.(?:com|org|net|blogspot\.com|wordpress\.com|info|bd)\s*\]?", "", work, flags=re.I)
    work = re.sub(r"\(\s*Unknown Author\s*\)", "", work, flags=re.I).strip()

    # Preserve leading series brackets like [065-066] or [320]
    m_pre = re.match(r"^(\[[0-9,\s-]+\])\s*(.+)$", work)
    if m_pre:
        prefix_parts.append(m_pre.group(1))
        work = m_pre.group(2).strip()

    # Extract trailing [YYYY] or (YYYY) year badge
    m_yr = re.search(r"\s*([\[(](?:19|20)\d{2}[\])])\s*$", work)
    if m_yr:
        suffix_parts.insert(0, m_yr.group(1))
        work = work[: m_yr.start()].strip()

    # Handle inline glued author prefixes like 'HumayunAhmed <Title>' or 'SattyajitRay <Title>'
    m_ha = re.match(r"^(?:Humayun\s*Ahmed|HumayunAhmed)\s+(.+)$", work, flags=re.I)
    if m_ha:
        work = m_ha.group(1).strip()
        if "হুমায়ূন আহমেদ" not in " ".join(suffix_parts):
            suffix_parts.append("- হুমায়ূন আহমেদ")
    m_sr = re.match(r"^(?:Sattyajit\s*Ray|Satyajit\s*Ray|SattyajitRay|SatyajitRay)\s+(.+)$", work, flags=re.I)
    if m_sr:
        work = m_sr.group(1).strip()
        if "সত্যজিৎ রায়" not in " ".join(suffix_parts):
            suffix_parts.append("- সত্যজিৎ রায়")

    # Strip trailing parenthetical English explanation or gloss e.g. '(So Says ...)' or '(Tondra = Slumber; ...)'
    work = re.sub(r"\s*\((?:So Says|Bangla Onubad|Bangla Translation|[^)]*=)[^)]*\)\s*$", "", work, flags=re.I).strip()

    return " ".join(prefix_parts), work, " ".join(suffix_parts), ext


def convert_banglish_title(
    filename: str,
    folder_path: str,
    bn_index: dict[str, str],
) -> tuple[str | None, str]:
    """
    Attempt strict, high-confidence Banglish -> Bangla conversion.
    Returns (new_filename_or_None, reason_or_status).
    """
    if BENGALI_RE.search(filename) or ARABIC_RE.search(filename):
        return None, "already_non_latin"

    top = folder_path.split("/")[0] if folder_path else ""
    if top in SKIP_BANGLISH_TOP or any(sub in folder_path for sub in SKIP_BANGLISH_SUB):
        return None, "protected_folder"

    prefix, core, suffix, ext = split_banglish_filename(filename)
    if not core or not re.search(r"[A-Za-z]{2,}", core):
        return None, "no_latin_core"

    # Extract trailing numeric volume/part (e.g. '1', '2', '1,2')
    trailing_num = ""
    m_num = re.match(r"^(.*?)\s+(\d+(?:\s*,\s*\d+)*)$", core)
    if m_num and re.search(r"[A-Za-z]", m_num.group(1)):
        core_main = m_num.group(1).strip()
        trailing_num = m_num.group(2).strip()
    else:
        core_main = core

    # Strip trailing ' - Bangla Onubad' / ' Bangla Onubad' if present
    core_norm = re.sub(r"[-—]+", " ", core_main).strip()
    low_norm = re.sub(r"\s+", " ", core_norm.lower()).strip()

    # Handle 'Masud Rana - <Subtitle>' pattern cleanly
    masud_sub = None
    m_mr = re.match(r"^masud\s*rana(?:\s*-\s*|\s+)(.+)$", core_main, flags=re.I)
    if m_mr:
        masud_sub = m_mr.group(1).strip()

    # Split core into words and check English prose exclusion
    tokens = re.findall(r"[A-Za-z]+|\d+", core_norm)
    alpha_tokens = [t.lower() for t in tokens if t.isalpha()]
    if not alpha_tokens:
        return None, "no_alpha_tokens"

    english_hits = [t for t in alpha_tokens if t in ENGLISH_STOP_WORDS and t not in ("ali", "tagore")]
    if english_hits and low_norm not in CURATED_PHRASE_MAP:
        return None, f"english_guard:{','.join(english_hits[:3])}"

    # 1) Curated famous phrase lookup
    if low_norm in CURATED_PHRASE_MAP:
        bn_core = CURATED_PHRASE_MAP[low_norm]
        return _assemble_bn_name(prefix, bn_core, trailing_num, suffix, ext), "curated_phrase_match"

    # 2) Canonical Wikipedia / existing Bangla catalog lookup
    sk = phonetic_skeleton(core_norm)
    # Only allow 1-word canonical lookup if clearly in a Bengali author/series/bangla folder
    in_bn_context = top in ("Bangla Books", "Authors & Scholars", "Series & Collections")
    if sk in bn_index and (len(alpha_tokens) >= 2 or (in_bn_context and len(alpha_tokens[0]) >= 6 and alpha_tokens[0] not in AMBIGUOUS_IF_ALONE)):
        bn_core = bn_index[sk]
        return _assemble_bn_name(prefix, bn_core, trailing_num, suffix, ext), "canonical_bn_bibliography_match"

    # 3) Word-by-word strict Banglish lexicon conversion (requires 100% alpha coverage & >= 2 strong tokens)
    if masud_sub:
        sub_tokens = re.findall(r"[A-Za-z]+", masud_sub)
        if sub_tokens and all(t.lower() in BANGLISH_LEXICON for t in sub_tokens) and not any(t.lower() in ENGLISH_STOP_WORDS for t in sub_tokens):
            bn_sub = " ".join(BANGLISH_LEXICON[t.lower()] for t in sub_tokens)
            return _assemble_bn_name(prefix, f"মাসুদ রানা - {bn_sub}", trailing_num, suffix, ext), "masud_rana_lexicon_match"

    strong_hits = [t for t in alpha_tokens if t in BANGLISH_LEXICON and t not in AMBIGUOUS_IF_ALONE]
    if len(strong_hits) >= 2 and all(t in BANGLISH_LEXICON for t in alpha_tokens):
        bn_words = [BANGLISH_LEXICON[t.lower()] if t.isalpha() else t for t in tokens]
        bn_core = " ".join(bn_words)
        return _assemble_bn_name(prefix, bn_core, trailing_num, suffix, ext), "strict_banglish_lexicon_match"

    # Identify items that have at least 1 strong Banglish signal for manual review report
    if strong_hits:
        return None, f"requires_manual_review:partial_banglish({','.join(strong_hits[:3])})"
    return None, "english_or_other"


def _assemble_bn_name(prefix: str, bn_core: str, trailing_num: str, suffix: str, ext: str) -> str:
    if trailing_num and re.search(rf"(?:^|\s){re.escape(trailing_num)}$", bn_core):
        trailing_num = ""
    parts = [p for p in (prefix, bn_core, trailing_num, suffix) if p]
    return du.sanitize_filename(" ".join(parts), ext)


def run_safe_renames(repo_dir: Path, dry_run: bool = False) -> dict[str, Any]:
    plan_path = repo_dir / "reports" / "renamer" / "safe_stage_d_plan.json"
    if not plan_path.exists():
        raise FileNotFoundError(f"Safe Stage D plan not found: {plan_path}")
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    candidates = plan.get("renames", [])
    print(f"[SafeRenames] Loaded {len(candidates)} verified safe candidates (dry_run={dry_run}).", flush=True)

    # Cache live children per parent folder so we check exact live collisions accurately
    parent_siblings: dict[str, dict[str, dict[str, Any]]] = {}
    rename_log: list[dict[str, Any]] = []
    already_done = 0
    missing_or_trashed = 0
    collisions = 0
    errors: list[dict[str, Any]] = []
    verified = 0

    for item in candidates:
        fid = item["id"]
        pid = item["parentId"]
        old_name = item["old_name"]
        new_name = item["new_name"]

        if os.path.splitext(old_name)[1].lower() != os.path.splitext(new_name)[1].lower():
            errors.append({"id": fid, "error": "extension_mismatch"})
            continue

        if pid not in parent_siblings:
            kids = du.list_children(pid)
            parent_siblings[pid] = {k["id"]: k for k in kids}

        live = parent_siblings[pid].get(fid)
        if not live:
            try:
                meta = du.drive_request(
                    "GET",
                    f"/files/{fid}",
                    params={"supportsAllDrives": "true", "fields": "id,name,parents,trashed,mimeType"},
                )
                if meta.get("trashed"):
                    missing_or_trashed += 1
                    continue
                live = meta
            except Exception as e:
                missing_or_trashed += 1
                errors.append({"id": fid, "error": str(e)[:180]})
                continue

        live_name = live.get("name", "")
        if live_name == new_name:
            already_done += 1
            continue

        sibling_names = {k.get("name", "").lower() for kid_id, k in parent_siblings[pid].items() if kid_id != fid}
        if new_name.lower() in sibling_names:
            collisions += 1
            continue

        if dry_run:
            rename_log.append(
                {
                    "id": fid,
                    "action": "rename",
                    "folder": item["folder"],
                    "old_parent_id": pid,
                    "new_parent_id": pid,
                    "old_name": live_name,
                    "new_name": new_name,
                    "category": item.get("category", item.get("top_folder", "")),
                }
            )
            continue

        try:
            du.drive_request(
                "PATCH",
                f"/files/{fid}",
                params={"supportsAllDrives": "true", "fields": "id,name,parents"},
                body={"name": new_name},
            )
            check = du.drive_request(
                "GET",
                f"/files/{fid}",
                params={"supportsAllDrives": "true", "fields": "id,name,parents,trashed"},
            )
            if check.get("name") == new_name and not check.get("trashed", False):
                verified += 1
            live["name"] = new_name
            rename_log.append(
                {
                    "id": fid,
                    "action": "rename",
                    "folder": item["folder"],
                    "old_parent_id": pid,
                    "new_parent_id": pid,
                    "old_name": live_name,
                    "new_name": new_name,
                    "category": item.get("category", item.get("top_folder", "")),
                }
            )
        except Exception as e:
            errors.append({"id": fid, "old": live_name, "new": new_name, "error": str(e)[:200]})

    applied_at = dt.datetime.now(dt.timezone.utc).isoformat()
    cl_res = {"batch_id": "", "total_entries": 0}
    if not dry_run and rename_log:
        cl_res = du.update_rename_changelog(
            repo_dir, rename_log, applied_at, sync_drive=True, batch_id=du.make_batch_id(applied_at, "safe")
        )

    out = {
        "applied_at": applied_at,
        "dry_run": dry_run,
        "planned_count": len(candidates),
        "renamed_count": len(rename_log),
        "verified_count": verified,
        "already_done": already_done,
        "missing_or_trashed": missing_or_trashed,
        "collisions_skipped": collisions,
        "errors_count": len(errors),
        "batch_id": cl_res["batch_id"],
        "renames": rename_log,
        "errors": errors,
    }
    (repo_dir / "reports" / "safe_stage_d_execution.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps({k: v for k, v in out.items() if k not in ("renames", "errors")}, indent=2), flush=True)
    return out


def run_banglish_renames(repo_dir: Path, dry_run: bool = False, local_catalog_only: bool = False) -> dict[str, Any]:
    print("[Banglish] Fetching Bangla Wikipedia bibliography index...", flush=True)
    wiki_titles = fetch_bn_wikipedia_titles()
    bn_index = build_canonical_bn_index(repo_dir, extra_bn_titles=wiki_titles)
    print(f"[Banglish] Canonical Bengali skeleton index size: {len(bn_index)} ({len(wiki_titles)} Wiki titles).", flush=True)

    candidates: list[dict[str, Any]] = []
    manual_review: list[dict[str, Any]] = []
    siblings_by_parent: dict[str, set[str]] = collections.defaultdict(set)
    inspected = 0

    if local_catalog_only:
        cat = json.loads((repo_dir / "books.json").read_text(encoding="utf-8"))
        cats, subs, fmts = cat["cats"], cat["subs"], cat["fmts"]
        for b in cat["books"]:
            fid, title, author, ci, si, li, fi, sz, cov, ser = b
            c_name = cats[ci] if 0 <= ci < len(cats) else ""
            s_name = subs[si] if 0 <= si < len(subs) else ""
            ext = "." + (fmts[fi].lower() if 0 <= fi < len(fmts) else "pdf")
            fname = f"{title}{ext}"
            fpath = f"{c_name}/{s_name}".strip("/")
            siblings_by_parent[fpath].add(fname.lower())
            inspected += 1
            proposed, reason = convert_banglish_title(fname, fpath, bn_index)
            if proposed and proposed != fname:
                candidates.append(
                    {
                        "id": fid,
                        "parent_id": fpath,
                        "folder": fpath,
                        "old_name": fname,
                        "new_name": proposed,
                        "reason": reason,
                        "category": c_name,
                    }
                )
            elif reason.startswith("requires_manual_review:"):
                manual_review.append({"id": fid, "folder": fpath, "name": fname, "reason": reason})
    else:
        tree = du.walk_drive_tree(du.ROOT_ID)
        for f in tree["files"]:
            siblings_by_parent[f["parent_id"]].add(f["name"].lower())
        for sc in tree["shortcuts"]:
            siblings_by_parent[sc["parent_id"]].add(sc["name"].lower())

        for f in tree["files"]:
            if f["ext"] not in du.BOOK_EXTS:
                continue
            inspected += 1
            proposed, reason = convert_banglish_title(f["name"], f["folder"], bn_index)
            if proposed and proposed != f["name"]:
                candidates.append(
                    {
                        "id": f["id"],
                        "parent_id": f["parent_id"],
                        "folder": f["folder"],
                        "old_name": f["name"],
                        "new_name": proposed,
                        "reason": reason,
                        "category": f["folder"].split("/")[0] if f["folder"] else "",
                    }
                )
            elif reason.startswith("requires_manual_review:"):
                manual_review.append({"id": f["id"], "folder": f["folder"], "name": f["name"], "reason": reason})

    rename_log: list[dict[str, Any]] = []
    verified = 0
    collisions = 0
    errors: list[dict[str, Any]] = []

    for cand in candidates:
        pid = cand["parent_id"]
        if cand["new_name"].lower() in siblings_by_parent[pid]:
            collisions += 1
            continue
        if dry_run or local_catalog_only:
            rename_log.append(
                {
                    "id": cand["id"],
                    "action": "rename",
                    "folder": cand["folder"],
                    "old_parent_id": pid,
                    "new_parent_id": pid,
                    "old_name": cand["old_name"],
                    "new_name": cand["new_name"],
                    "reason": cand["reason"],
                    "category": cand["category"],
                }
            )
            siblings_by_parent[pid].discard(cand["old_name"].lower())
            siblings_by_parent[pid].add(cand["new_name"].lower())
            continue

        try:
            du.drive_request(
                "PATCH",
                f"/files/{cand['id']}",
                params={"supportsAllDrives": "true", "fields": "id,name,parents"},
                body={"name": cand["new_name"]},
            )
            chk = du.drive_request(
                "GET",
                f"/files/{cand['id']}",
                params={"supportsAllDrives": "true", "fields": "id,name,parents,trashed"},
            )
            if chk.get("name") == cand["new_name"] and not chk.get("trashed", False):
                verified += 1
            siblings_by_parent[pid].discard(cand["old_name"].lower())
            siblings_by_parent[pid].add(cand["new_name"].lower())
            rename_log.append(
                {
                    "id": cand["id"],
                    "action": "rename",
                    "folder": cand["folder"],
                    "old_parent_id": pid,
                    "new_parent_id": pid,
                    "old_name": cand["old_name"],
                    "new_name": cand["new_name"],
                    "reason": cand["reason"],
                    "category": cand["category"],
                }
            )
        except Exception as e:
            errors.append({"id": cand["id"], "old": cand["old_name"], "error": str(e)[:200]})

    applied_at = dt.datetime.now(dt.timezone.utc).isoformat()
    cl_res = {"batch_id": "", "total_entries": 0}
    if not dry_run and not local_catalog_only and rename_log:
        cl_res = du.update_rename_changelog(
            repo_dir, rename_log, applied_at, sync_drive=True, batch_id=du.make_batch_id(applied_at, "banglish")
        )

    out = {
        "applied_at": applied_at,
        "dry_run": dry_run or local_catalog_only,
        "inspected": inspected,
        "matched_candidates": len(candidates),
        "renamed_count": len(rename_log),
        "verified_count": verified,
        "collisions_skipped": collisions,
        "manual_review_count": len(manual_review),
        "errors_count": len(errors),
        "batch_id": cl_res["batch_id"],
        "renames": rename_log,
        "manual_review": manual_review[:300],
        "errors": errors,
    }
    reports_dir = repo_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "banglish_rename_report.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    md = [
        "# Banglish-to-Bengali Script Rename Report",
        "",
        f"- **Timestamp (UTC):** `{applied_at}`",
        f"- **Dry Run:** `{out['dry_run']}`",
        f"- **Books Inspected:** `{inspected}`",
        f"- **Verified Banglish -> Bengali Renames:** `{len(rename_log)}` (verified on Drive: `{verified}`)",
        f"- **Partial Banglish Held for Manual Review:** `{len(manual_review)}`",
        "",
        "## Converted Titles",
        "",
        "| Folder | Old Filename (Banglish) | New Filename (Bangla) | Method |",
        "|---|---|---|---|",
    ]
    for r in rename_log:
        md.append(f"| `{r['folder']}` | {r['old_name']} | {r['new_name']} | `{r['reason']}` |")
    if manual_review:
        md += ["", "## Partial Matches Left Untouched for Review (Sample)", ""]
        for mr in manual_review[:100]:
            md.append(f"- `{mr['folder']}` / `{mr['name']}` ({mr['reason']})")
    (reports_dir / "banglish_rename_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k not in ("renames", "manual_review", "errors")}, indent=2), flush=True)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["safe_renames", "banglish_renames", "all"], required=True)
    ap.add_argument("--repo-dir", default=".")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--local-catalog-only", action="store_true", help="Test banglish_renames locally using books.json")
    args = ap.parse_args()

    repo_dir = Path(args.repo_dir).resolve()
    if args.mode in ("safe_renames", "all"):
        run_safe_renames(repo_dir, dry_run=args.dry_run)
    if args.mode in ("banglish_renames", "all"):
        run_banglish_renames(repo_dir, dry_run=args.dry_run, local_catalog_only=args.local_catalog_only)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
