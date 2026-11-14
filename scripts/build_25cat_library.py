import argparse
import concurrent.futures
import json
import re
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote

GDRIVE = shutil.which("gdrive") or "gdrive"
REPO_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_DIR / "data"
ROOT_DRIVE_ID = "1fMsplDtUnpUhnNBJGKvYQ1sdZx0QVJWq"
ROOT_DRIVE_NAME = "bangladesh biggest e book library"

# Exact 25-category BANGLA_LIBRARY tree
# Each top category maps to either:
#   - a list of leaf category folder names, OR
#   - a dict for nested categories (used by 01_Religion_ধর্ম -> Islam_ইসলাম -> 16 subcategories)
TAXONOMY = {
    "01_Religion_ধর্ম": {
        "Islam_ইসলাম": [
            "Quran_কুরআন",
            "Tafsir_তাফসীর",
            "Hadith_হাদিস",
            "Fiqh_ফিকহ",
            "Aqeedah_আকীদাহ",
            "Seerah_সীরাত",
            "Prophets_নবী_রাসূল",
            "Sahaba_সাহাবী",
            "Islamic_History_ইসলামের_ইতিহাস",
            "Islamic_Lifestyle_ইসলামী_জীবনব্যবস্থা",
            "Dua_and_Prayer_দোয়া_ও_নামাজ",
            "Islamic_Economics_ইসলামী_অর্থনীতি",
            "Islamic_Politics_ইসলামী_রাজনীতি",
            "Islamic_Philosophy_ইসলামী_দর্শন",
            "Islamic_Literature_ইসলামী_সাহিত্য",
            "Islamic_Children_Books_শিশুদের_ইসলাম",
        ],
        "Hinduism_হিন্দুধর্ম": [],
        "Buddhism_বৌদ্ধধর্ম": [],
        "Christianity_খ্রিষ্টধর্ম": [],
        "Other_Religions_অন্যান্য_ধর্ম": [],
        "Comparative_Religion_তুলনামূলক_ধর্ম": [],
    },
    "02_Literature_সাহিত্য": [
        "Poetry_কবিতা",
        "Novels_উপন্যাস",
        "Short_Stories_ছোটগল্প",
        "Essays_প্রবন্ধ",
        "Drama_নাটক",
        "Plays_নাট্যসাহিত্য",
        "Humorous_Literature_রম্যসাহিত্য",
        "Travel_Writing_ভ্রমণকাহিনী",
        "Letters_পত্রসাহিত্য",
        "Literary_Criticism_সাহিত্য_সমালোচনা",
        "Autobiography_আত্মজীবনী",
        "Memoirs_স্মৃতিকথা",
        "Folk_Literature_লোকসাহিত্য",
        "Children's_Literature_শিশুসাহিত্য",
        "Prose_গদ্য",
        "Rhymes_ছড়া",
        "Collected_Works_রচনাবলী",
    ],
    "03_Fiction_কল্পকাহিনী": [
        "Romance_রোমান্স",
        "Mystery_রহস্য",
        "Detective_গোয়েন্দা",
        "Thriller_থ্রিলার",
        "Horror_ভৌতিক",
        "Ghost_Stories_ভূতের_গল্প",
        "Science_Fiction_সায়েন্স_ফিকশন",
        "Fantasy_ফ্যান্টাসি",
        "Historical_Fiction_ঐতিহাসিক_কল্পকাহিনী",
        "Adventure_অ্যাডভেঞ্চার",
        "Psychological_Fiction_মনস্তাত্ত্বিক",
        "Political_Fiction_রাজনৈতিক_কল্পকাহিনী",
        "War_Fiction_যুদ্ধভিত্তিক",
        "Social_Fiction_সামাজিক",
        "Dystopian_ডিস্টোপিয়ান",
    ],
    "04_Science_বিজ্ঞান": [
        "Mathematics_গণিত",
        "Physics_পদার্থবিজ্ঞান",
        "Chemistry_রসায়ন",
        "Biology_জীববিজ্ঞান",
        "Astronomy_জ্যোতির্বিজ্ঞান",
        "Geography_ভূগোল",
        "Geology_ভূতত্ত্ব",
        "Environmental_Science_পরিবেশবিজ্ঞান",
        "Genetics_জেনেটিক্স",
        "Neuroscience_স্নায়ুবিজ্ঞান",
        "General_Science_সাধারণ_বিজ্ঞান",
    ],
    "05_Computer_and_Technology_কম্পিউটার_ও_প্রযুক্তি": [
        "Computer_Science_কম্পিউটার_বিজ্ঞান",
        "Programming_প্রোগ্রামিং",
        "Artificial_Intelligence_AI_কৃত্রিম_বুদ্ধিমত্তা",
        "Machine_Learning_মেশিন_লার্নিং",
        "Data_Science_ডেটা_সায়েন্স",
        "Data_Analytics_ডেটা_অ্যানালিটিক্স",
        "Cybersecurity_সাইবার_নিরাপত্তা",
        "Networking_নেটওয়ার্কিং",
        "Web_Development_ওয়েব_ডেভেলপমেন্ট",
        "Software_Engineering_সফটওয়্যার_ইঞ্জিনিয়ারিং",
        "Database_ডেটাবেজ",
        "Robotics_রোবোটিক্স",
        "Emerging_Technology_নতুন_প্রযুক্তি",
    ],
    "06_History_ইতিহাস": [
        "Bangladesh_History_বাংলাদেশের_ইতিহাস",
        "World_History_বিশ্ব_ইতিহাস",
        "Ancient_History_প্রাচীন_ইতিহাস",
        "Medieval_History_মধ্যযুগীয়_ইতিহাস",
        "Modern_History_আধুনিক_ইতিহাস",
        "Liberation_War_মুক্তিযুদ্ধ",
        "Language_Movement_ভাষা_আন্দোলন",
        "British_Period_ব্রিটিশ_শাসন",
        "Mughal_Period_মুঘল_যুগ",
        "Archaeology_প্রত্নতত্ত্ব",
        "Historical_Documents_ঐতিহাসিক_দলিল",
    ],
    "07_Politics_and_Government_রাজনীতি_ও_সরকার": [
        "Political_Theory_রাজনৈতিক_তত্ত্ব",
        "Political_Parties_রাজনৈতিক_দল",
        "Democracy_গণতন্ত্র",
        "Constitution_সংবিধান",
        "Governance_শাসনব্যবস্থা",
        "International_Relations_আন্তর্জাতিক_সম্পর্ক",
        "Diplomacy_কূটনীতি",
        "Public_Administration_জনপ্রশাসন",
        "Human_Rights_মানবাধিকার",
    ],
    "08_Social_Science_সমাজবিজ্ঞান": [
        "Sociology_সমাজবিজ্ঞান",
        "Anthropology_নৃবিজ্ঞান",
        "Psychology_মনোবিজ্ঞান",
        "Economics_অর্থনীতি",
        "Education_শিক্ষা",
        "Social_Work_সমাজকর্ম",
        "Gender_Studies_জেন্ডার_স্টাডিজ",
        "Population_Studies_জনসংখ্যা",
        "Culture_সংস্কৃতি",
        "Development_Studies_উন্নয়ন_অধ্যয়ন",
    ],
    "09_Philosophy_দর্শন": [
        "Logic_যুক্তিবিদ্যা",
        "Ethics_নীতিশাস্ত্র",
        "Metaphysics_অধিবিদ্যা",
        "Eastern_Philosophy_প্রাচ্য_দর্শন",
        "Western_Philosophy_পাশ্চাত্য_দর্শন",
        "Islamic_Philosophy_ইসলামী_দর্শন",
        "Modern_Philosophy_আধুনিক_দর্শন",
    ],
    "10_Psychology_and_Mind_মনোবিজ্ঞান_ও_মানসিকতা": [
        "Cognitive_Psychology",
        "Behavioral_Psychology",
        "Social_Psychology",
        "Personality",
        "Emotional_Intelligence",
        "Mental_Development",
        "Human_Behavior",
    ],
    "11_Business_and_Finance_ব্যবসা_ও_অর্থায়ন": [
        "Entrepreneurship_উদ্যোক্তা",
        "Business_Management_ব্যবসা_পরিচালনা",
        "Marketing_মার্কেটিং",
        "Accounting_হিসাববিজ্ঞান",
        "Banking_ব্যাংকিং",
        "Finance_ফাইন্যান্স",
        "Investment_বিনিয়োগ",
        "Stock_Market_শেয়ার_বাজার",
        "Insurance_বীমা",
        "Islamic_Finance_ইসলামী_ফাইন্যান্স",
    ],
    "12_Law_and_Legal_আইন_ও_বিচার": [
        "Bangladesh_Law_বাংলাদেশের_আইন",
        "Constitutional_Law_সাংবিধানিক_আইন",
        "Criminal_Law_ফৌজদারি_আইন",
        "Civil_Law_দেওয়ানি_আইন",
        "International_Law_আন্তর্জাতিক_আইন",
        "Human_Rights_Law_মানবাধিকার_আইন",
        "Islamic_Law_ইসলামী_আইন",
    ],
    "13_Medicine_and_Health_চিকিৎসা_ও_স্বাস্থ্য": [
        "Anatomy_অ্যানাটমি",
        "Physiology_ফিজিওলজি",
        "Medicine_মেডিসিন",
        "Surgery_সার্জারি",
        "Pharmacy_ফার্মেসি",
        "Nutrition_পুষ্টি",
        "Public_Health_জনস্বাস্থ্য",
        "Mental_Health_মানসিক_স্বাস্থ্য",
        "First_Aid_প্রাথমিক_চিকিৎসা",
        "Alternative_Medicine_বিকল্প_চিকিৎসা",
    ],
    "14_Engineering_প্রকৌশল": [
        "Electrical_Engineering",
        "Electronics",
        "Mechanical_Engineering",
        "Civil_Engineering",
        "Chemical_Engineering",
        "Architecture",
        "Textile_Engineering",
        "Agricultural_Engineering",
        "Telecommunications",
    ],
    "15_Education_and_Academics_শিক্ষা_ও_একাডেমিক": [
        "Primary_Education",
        "Secondary_Education",
        "Higher_Secondary",
        "University",
        "Admission_Preparation",
        "Academic_Textbooks",
        "Research_Methodology",
        "Thesis_and_Dissertation",
        "Question_Banks",
        "Competitive_Exams",
    ],
    "16_Language_and_Linguistics_ভাষা_ও_ভাষাবিজ্ঞান": [
        "Bengali_Language_বাংলা_ভাষা",
        "English_Language_ইংরেজি_ভাষা",
        "Arabic_Language_আরবি_ভাষা",
        "Grammar_ব্যাকরণ",
        "Linguistics_ভাষাবিজ্ঞান",
        "Translation_অনুবাদ",
        "Vocabulary_শব্দভাণ্ডার",
        "Dictionary_অভিধান",
    ],
    "17_Biography_and_Autobiography_জীবনী_ও_আত্মজীবনী": [
        "World_Leaders",
        "Bangladeshi_Personalities",
        "Scientists",
        "Writers_and_Poets",
        "Entrepreneurs",
        "Historical_Personalities",
        "Autobiographies",
    ],
    "18_Self_Development_আত্মউন্নয়ন": [
        "Productivity_কর্মদক্ষতা",
        "Time_Management_সময়_ব্যবস্থাপনা",
        "Leadership_নেতৃত্ব",
        "Communication_যোগাযোগ",
        "Critical_Thinking_সমালোচনামূলক_চিন্তা",
        "Problem_Solving_সমস্যা_সমাধান",
        "Habits_অভ্যাস",
        "Motivation_অনুপ্রেরণা",
        "Career_Development_ক্যারিয়ার",
    ],
    "19_Arts_and_Culture_শিল্প_ও_সংস্কৃতি": [
        "Painting_চিত্রকলা",
        "Photography_ফটোগ্রাফি",
        "Music_সংগীত",
        "Dance_নৃত্য",
        "Cinema_চলচ্চিত্র",
        "Theatre_থিয়েটার",
        "Architecture_স্থাপত্য",
        "Calligraphy_ক্যালিগ্রাফি",
        "Handicrafts_হস্তশিল্প",
    ],
    "20_Agriculture_and_Nature_কৃষি_ও_প্রকৃতি": [
        "Agriculture_কৃষি",
        "Gardening_বাগান",
        "Forestry_বনায়ন",
        "Fisheries_মৎস্য",
        "Animal_Husbandry_পশুপালন",
        "Wildlife_বন্যপ্রাণী",
        "Climate_Change_জলবায়ু_পরিবর্তন",
        "Biodiversity_জীববৈচিত্র্য",
    ],
    "21_Travel_and_Geography_ভ্রমণ_ও_ভূগোল": [
        "Bangladesh_বাংলাদেশ",
        "Asia_এশিয়া",
        "Europe_ইউরোপ",
        "Africa_আফ্রিকা",
        "Americas_আমেরিকা",
        "Travel_Guides_ভ্রমণ_গাইড",
        "Travel_Memoirs_ভ্রমণ_স্মৃতিকথা",
        "Maps_and_Atlases_মানচিত্র",
    ],
    "22_Children_and_Young_Adult_শিশু_ও_কিশোর": [
        "Picture_Books",
        "Fairy_Tales",
        "Moral_Stories",
        "Adventure_Stories",
        "Educational_Books",
        "Science_for_Kids",
        "Comics",
        "Teen_Fiction",
        "Teen_Nonfiction",
    ],
    "23_Reference_Books_তথ্যসূত্র": [
        "Encyclopedia_বিশ্বকোষ",
        "Dictionary_অভিধান",
        "Atlas_অ্যাটলাস",
        "Yearbooks_বর্ষপঞ্জি",
        "Almanacs_পঞ্জিকা",
        "Handbooks_হ্যান্ডবুক",
        "Directories_নির্দেশিকা",
        "Bibliography_গ্রন্থপঞ্জি",
        "General_Knowledge_সাধারণ_জ্ঞান",
    ],
    "24_Magazines_and_Periodicals_সাময়িকী": [
        "Literary_Magazines",
        "Science_Magazines",
        "Religious_Magazines",
        "Children's_Magazines",
        "Newspapers",
        "Journals",
        "Newsletters",
    ],
    "25_Others_and_Unclassified_অন্যান্য": [
        "Rare_Books",
        "Historical_Manuscripts",
        "Unclassified",
        "To_Be_Organized",
    ],
}

# Subfolders whose contents are mixed/generic and should be classified per-file
MIXED_SUBFOLDERS = {
    ("01 - Quran & Tafsir", "General"),
    ("01 - Quran & Tafsir", "অনেকগুলো ইসলামিক বই এই ফাইলে"),
    ("01 - Quran & Tafsir", "ইসলামিক সাহিত্য"),
    ("01 - Quran & Tafsir", "নতুন"),
    ("01 - Quran & Tafsir", "প্রায় ৮০ টি ইসলামিক ও প্রয়োজনীয় text ফাইল"),
    ("02 - Hadith & Sunnah", "General"),
    ("02 - Hadith & Sunnah", "অনেকগুলো ইসলামিক বই এই ফাইলে"),
    ("02 - Hadith & Sunnah", "ইসলামিক সাহিত্য"),
    ("02 - Hadith & Sunnah", "নতুন"),
    ("02 - Hadith & Sunnah", "প্রায় ৮০ টি ইসলামিক ও প্রয়োজনীয় text ফাইল"),
    ("03 - Islamic Books & Aqeedah", "General Islamic Books"),
    ("03 - Islamic Books & Aqeedah", "অনেকগুলো ইসলামিক বই এই ফাইলে"),
    ("03 - Islamic Books & Aqeedah", "ইসলামিক সাহিত্য"),
    ("03 - Islamic Books & Aqeedah", "নতুন"),
    ("03 - Islamic Books & Aqeedah", "প্রায় ৮০ টি ইসলামিক ও প্রয়োজনীয় text ফাইল"),
    ("04 - Seerah, History & Biography", "General"),
    ("04 - Seerah, History & Biography", "অনেকগুলো ইসলামিক বই এই ফাইলে"),
    ("04 - Seerah, History & Biography", "ইসলামিক সাহিত্য"),
    ("04 - Seerah, History & Biography", "নতুন"),
    ("04 - Seerah, History & Biography", "প্রায় ৮০ টি ইসলামিক ও প্রয়োজনীয় text ফাইল"),
    ("05 - Arabic Language & Dictionaries", "General"),
    ("06 - Literature & Authors (Mrinal e-Library)", "বিবিধ"),
    ("06 - Literature & Authors (Mrinal e-Library)", "ই-পাব"),
    ("06 - Literature & Authors (Mrinal e-Library)", "এবং সাহিত্য"),
    ("07 - Other & Archives", "Images"),
    ("07 - Other & Archives", "ইসলামী বই"),
    ("07 - Other & Archives", "ইসলামীক বই ৫০০টি+"),
    ("07 - Other & Archives", "মৃণালের ই-লাইব্রেরি"),
}

# Author/topic folder classifications for Mrinal e-Library & dedicated subfolders
SCIENCE_SUBS = {
    "অমল দাসগুপ্ত": ("04_Science_বিজ্ঞান", "Physics_পদার্থবিজ্ঞান"),
    "জামাল নজরুল ইসলাম": ("04_Science_বিজ্ঞান", "Physics_পদার্থবিজ্ঞান"),
    "দেবেন্দ্র ভোরা": ("04_Science_বিজ্ঞান", "Physics_পদার্থবিজ্ঞান"),
    "চমক হাসান": ("04_Science_বিজ্ঞান", "Mathematics_গণিত"),
    "দ্বিজেন শর্মা": ("04_Science_বিজ্ঞান", "Biology_জীববিজ্ঞান"),
    "গোপালচন্দ্র ভট্টাচার্য": ("04_Science_বিজ্ঞান", "Biology_জীববিজ্ঞান"),
    "বন্যা আহমেদ": ("04_Science_বিজ্ঞান", "Biology_জীববিজ্ঞান"),
    "অভিজিৎ রায়": ("04_Science_বিজ্ঞান", "General_Science_সাধারণ_বিজ্ঞান"),
    "ভবানীপ্রসাদ সাহু": ("04_Science_বিজ্ঞান", "General_Science_সাধারণ_বিজ্ঞান"),
}

FICTION_SUBS = {
    "অনীশ দেব": ("03_Fiction_কল্পকাহিনী", "Science_Fiction_সায়েন্স_ফিকশন"),
    "আসিফ মেহদী": ("03_Fiction_কল্পকাহিনী", "Science_Fiction_সায়েন্স_ফিকশন"),
    "কাসিব মুন্না": ("03_Fiction_কল্পকাহিনী", "Science_Fiction_সায়েন্স_ফিকশন"),
    "কাজী আনোয়ার হোসেন": ("03_Fiction_কল্পকাহিনী", "Thriller_থ্রিলার"),
    "আকাশ মালিক": ("03_Fiction_কল্পকাহিনী", "Thriller_থ্রিলার"),
    "ইন্দুভূষণ দাস": ("03_Fiction_কল্পকাহিনী", "Thriller_থ্রিলার"),
    "দীনেন্দ্রকুমার রায়": ("03_Fiction_কল্পকাহিনী", "Detective_গোয়েন্দা"),
    "হেমেন্দ্রকুমার রায়": ("03_Fiction_কল্পকাহিনী", "Detective_গোয়েন্দা"),
    "জরাসন্ধ": ("03_Fiction_কল্পকাহিনী", "Detective_গোয়েন্দা"),
    "অনীশ দাস অপু": ("03_Fiction_কল্পকাহিনী", "Horror_ভৌতিক"),
    "আশীফ এন্তাজ রবি": ("03_Fiction_কল্পকাহিনী", "Mystery_রহস্য"),
    "আদনান শাহরিয়ার": ("03_Fiction_কল্পকাহিনী", "Thriller_থ্রিলার"),
    "তপন কুমার দাস": ("03_Fiction_কল্পকাহিনী", "Adventure_অ্যাডভেঞ্চার"),
}

CHILDREN_SUBS = {
    "টিনটিন সিরিজ": ("22_Children_and_Young_Adult_শিশু_ও_কিশোর", "Comics"),
    "ছোটদের বই": ("22_Children_and_Young_Adult_শিশু_ও_কিশোর", "Fairy_Tales"),
    "দক্ষিণারঞ্জন মিত্র মজুমদার": ("22_Children_and_Young_Adult_শিশু_ও_কিশোর", "Fairy_Tales"),
    "উপেন্দ্রকিশোর রায়": ("22_Children_and_Young_Adult_শিশু_ও_কিশোর", "Fairy_Tales"),
    "সুকুমার রায়": ("22_Children_and_Young_Adult_শিশু_ও_কিশোর", "Fairy_Tales"),
    "কুলদারঞ্জন রায়": ("22_Children_and_Young_Adult_শিশু_ও_কিশোর", "Adventure_Stories"),
}

HISTORY_POLITICS_SOCIAL_SUBS = {
    "বাংলাদেশের ইতিহাস": ("06_History_ইতিহাস", "Bangladesh_History_বাংলাদেশের_ইতিহাস"),
    "বাংলাদেশ": ("06_History_ইতিহাস", "Bangladesh_History_বাংলাদেশের_ইতিহাস"),
    "অতুল সুর": ("06_History_ইতিহাস", "Bangladesh_History_বাংলাদেশের_ইতিহাস"),
    "তপন রায়চৌধুরী": ("06_History_ইতিহাস", "Bangladesh_History_বাংলাদেশের_ইতিহাস"),
    "গৌতম ভদ্র": ("06_History_ইতিহাস", "Bangladesh_History_বাংলাদেশের_ইতিহাস"),
    "হিতেশ রঞ্জন সান্যাল": ("06_History_ইতিহাস", "Bangladesh_History_বাংলাদেশের_ইতিহাস"),
    "বিনয় ঘোষ": ("06_History_ইতিহাস", "Bangladesh_History_বাংলাদেশের_ইতিহাস"),
    "আমার একাত্তর": ("06_History_ইতিহাস", "Liberation_War_মুক্তিযুদ্ধ"),
    "জাহানারা ইমাম": ("06_History_ইতিহাস", "Liberation_War_মুক্তিযুদ্ধ"),
    "আহমদ রফিক": ("06_History_ইতিহাস", "Language_Movement_ভাষা_আন্দোলন"),
    "আবুল মনসুর আহমদ": ("07_Politics_and_Government_রাজনীতি_ও_সরকার", "Political_Theory_রাজনৈতিক_তত্ত্ব"),
    "ভগৎ সিং": ("07_Politics_and_Government_রাজনীতি_ও_সরকার", "Political_Theory_রাজনৈতিক_তত্ত্ব"),
    "হুমায়ুন কবীর": ("07_Politics_and_Government_রাজনীতি_ও_সরকার", "Political_Theory_রাজনৈতিক_তত্ত্ব"),
    "অর্মত্য সেন": ("08_Social_Science_সমাজবিজ্ঞান", "Economics_অর্থনীতি"),
    "অশোক মিত্র": ("08_Social_Science_সমাজবিজ্ঞান", "Economics_অর্থনীতি"),
    "ধীরেশচন্দ্র ভট্টাচার্য": ("08_Social_Science_সমাজবিজ্ঞান", "Economics_অর্থনীতি"),
    "বেগম রোকেয়া": ("08_Social_Science_সমাজবিজ্ঞান", "Gender_Studies_জেন্ডার_স্টাডিজ"),
    "তসলিমা নাসরিন": ("08_Social_Science_সমাজবিজ্ঞান", "Gender_Studies_জেন্ডার_স্টাডিজ"),
    "চিত্রা দেব": ("08_Social_Science_সমাজবিজ্ঞান", "Gender_Studies_জেন্ডার_স্টাডিজ"),
    "আহমদ ছফা": ("08_Social_Science_সমাজবিজ্ঞান", "Culture_সংস্কৃতি"),
    "আহমদ শরীফ": ("08_Social_Science_সমাজবিজ্ঞান", "Culture_সংস্কৃতি"),
    "আনিসুজ্জামান": ("08_Social_Science_সমাজবিজ্ঞান", "Culture_সংস্কৃতি"),
    "আব্দুল্লাহ আবু সায়ীদ": ("08_Social_Science_সমাজবিজ্ঞান", "Culture_সংস্কৃতি"),
    "গোপাল হালদার": ("08_Social_Science_সমাজবিজ্ঞান", "Culture_সংস্কৃতি"),
    "গোলাম মুরশিদ": ("08_Social_Science_সমাজবিজ্ঞান", "Culture_সংস্কৃতি"),
    "ধূর্জটিপ্রসাদ মুখোপাধ্যায়": ("08_Social_Science_সমাজবিজ্ঞান", "Culture_সংস্কৃতি"),
    "আরজ আলী মাতুব্বর": ("09_Philosophy_দর্শন", "Eastern_Philosophy_প্রাচ্য_দর্শন"),
    "দেবীপ্রসাদ চট্টোপাধ্যায়": ("09_Philosophy_দর্শন", "Eastern_Philosophy_প্রাচ্য_দর্শন"),
    "ক্ষিতিমোহন সেন": ("09_Philosophy_দর্শন", "Eastern_Philosophy_প্রাচ্য_দর্শন"),
}

LANG_SELF_ARTS_SUBS = {
    "অভিধান": ("16_Language_and_Linguistics_ভাষা_ও_ভাষাবিজ্ঞান", "Dictionary_অভিধান"),
    "বাংলা একাডেমি": ("02_Literature_সাহিত্য", "Folk_Literature_লোকসাহিত্য"),
    "বাংলা ছন্দ ও অলঙ্কার": ("16_Language_and_Linguistics_ভাষা_ও_ভাষাবিজ্ঞান", "Bengali_Language_বাংলা_ভাষা"),
    "বাংলা প্রবাদ প্রবচন": ("16_Language_and_Linguistics_ভাষা_ও_ভাষাবিজ্ঞান", "Bengali_Language_বাংলা_ভাষা"),
    "কলিম খান": ("16_Language_and_Linguistics_ভাষা_ও_ভাষাবিজ্ঞান", "Linguistics_ভাষাবিজ্ঞান"),
    "হুমায়ুন আজাদ": ("16_Language_and_Linguistics_ভাষা_ও_ভাষাবিজ্ঞান", "Bengali_Language_বাংলা_ভাষা"),
    "হায়াৎ মামুদ": ("16_Language_and_Linguistics_ভাষা_ও_ভাষাবিজ্ঞান", "Bengali_Language_বাংলা_ভাষা"),
    "অনুবাদ সাহিত্য": ("16_Language_and_Linguistics_ভাষা_ও_ভাষাবিজ্ঞান", "Translation_অনুবাদ"),
    "বাংলা মোটিভেশনাল বই": ("18_Self_Development_আত্মউন্নয়ন", "Motivation_অনুপ্রেরণা"),
    "আয়মান সাদিক": ("18_Self_Development_আত্মউন্নয়ন", "Motivation_অনুপ্রেরণা"),
    "ঋত্বিককুমার ঘটক": ("19_Arts_and_Culture_শিল্প_ও_সংস্কৃতি", "Cinema_চলচ্চিত্র"),
    "এস এম সুলতান": ("19_Arts_and_Culture_শিল্প_ও_সংস্কৃতি", "Painting_চিত্রকলা"),
    "হাশেম খান": ("19_Arts_and_Culture_শিল্প_ও_সংস্কৃতি", "Painting_চিত্রকলা"),
    "ধ্রুব এষ": ("19_Arts_and_Culture_শিল্প_ও_সংস্কৃতি", "Painting_চিত্রকলা"),
    "অতুলপ্রসাদ সেন": ("19_Arts_and_Culture_শিল্প_ও_সংস্কৃতি", "Music_সংগীত"),
    "জলের গান": ("19_Arts_and_Culture_শিল্প_ও_সংস্কৃতি", "Music_সংগীত"),
    "দেবব্রত বিশ্বাস": ("19_Arts_and_Culture_শিল্প_ও_সংস্কৃতি", "Music_সংগীত"),
    "হেমাঙ্গ বিশ্বাস": ("19_Arts_and_Culture_শিল্প_ও_সংস্কৃতি", "Music_সংগীত"),
    "বাউল গান": ("19_Arts_and_Culture_শিল্প_ও_সংস্কৃতি", "Music_সংগীত"),
    "আয়েশা ফয়েজ": ("17_Biography_and_Autobiography_জীবনী_ও_আত্মজীবনী", "Autobiographies"),
    "আবু সাইয়িদ": ("06_History_ইতিহাস", "Bangladesh_History_বাংলাদেশের_ইতিহাস"),
}

LITERATURE_SUBS = {
    # Poetry
    "কাজী নজরুল ইসলাম": ("02_Literature_সাহিত্য", "Poetry_কবিতা"),
    "জীবনানন্দ দাশ": ("02_Literature_সাহিত্য", "Poetry_কবিতা"),
    "জসিম উদ্দীন": ("02_Literature_সাহিত্য", "Poetry_কবিতা"),
    "জয় গোস্বামী": ("02_Literature_সাহিত্য", "Poetry_কবিতা"),
    "অমিয় চক্রবর্তী": ("02_Literature_সাহিত্য", "Poetry_কবিতা"),
    "অরুণ মিত্র": ("02_Literature_সাহিত্য", "Poetry_কবিতা"),
    "বুদ্ধদেব বসু": ("02_Literature_সাহিত্য", "Poetry_কবিতা"),
    "বিনয় মজুমদার": ("02_Literature_সাহিত্য", "Poetry_কবিতা"),
    "হেলাল হাফিজ": ("02_Literature_সাহিত্য", "Poetry_কবিতা"),
    "আবুল হাসান": ("02_Literature_সাহিত্য", "Poetry_কবিতা"),
    "আহসান হাবীব": ("02_Literature_সাহিত্য", "Poetry_কবিতা"),
    "কবিতা সিংহ": ("02_Literature_সাহিত্য", "Poetry_কবিতা"),
    "কালিদাস রায়": ("02_Literature_সাহিত্য", "Poetry_কবিতা"),
    "কুসুমকুমারী দাস": ("02_Literature_সাহিত্য", "Poetry_কবিতা"),
    "কৃষ্ণচন্দ্র মজুমদার": ("02_Literature_সাহিত্য", "Poetry_কবিতা"),
    "বীরেন্দ্র চট্টোপাধ্যায়": ("02_Literature_সাহিত্য", "Poetry_কবিতা"),
    "ভারতচন্দ্র রায়গুণাকর": ("02_Literature_সাহিত্য", "Poetry_কবিতা"),
    "বড়ু চণ্ডীদাস": ("02_Literature_সাহিত্য", "Poetry_কবিতা"),
    "চর্যাপদ": ("02_Literature_সাহিত্য", "Poetry_কবিতা"),
    "হেমচন্দ্র বন্দ্যোপাধ্যায়": ("02_Literature_সাহিত্য", "Poetry_কবিতা"),
    "দাউদ হায়দার": ("02_Literature_সাহিত্য", "Poetry_কবিতা"),
    "ত্রিদিব দস্তিদার": ("02_Literature_সাহিত্য", "Poetry_কবিতা"),
    "গোলাম মোস্তফা": ("02_Literature_সাহিত্য", "Poetry_কবিতা"),
    "গোলাম কিবরিয়া পিনু": ("02_Literature_সাহিত্য", "Poetry_কবিতা"),
    "অরুণকুমার সরকার": ("02_Literature_সাহিত্য", "Poetry_কবিতা"),
    "আনন্দ বাগচী": ("02_Literature_সাহিত্য", "Poetry_কবিতা"),
    # Drama & Plays
    "গিরিশচন্দ্র ঘোষ": ("02_Literature_সাহিত্য", "Drama_নাটক"),
    "দীনবন্ধু মিত্র": ("02_Literature_সাহিত্য", "Drama_নাটক"),
    "দ্বিজেন্দ্রলাল রায়": ("02_Literature_সাহিত্য", "Drama_নাটক"),
    "ব্রজেন্দ্র কুমার দে": ("02_Literature_সাহিত্য", "Drama_নাটক"),
    "জিয়া হায়দার": ("02_Literature_সাহিত্য", "Plays_নাট্যসাহিত্য"),
    # Literary Criticism
    "আব্দুল করিম সাহিত্যবিশারদ": ("02_Literature_সাহিত্য", "Literary_Criticism_সাহিত্য_সমালোচনা"),
    "দীনেশচন্দ্র সেন": ("02_Literature_সাহিত্য", "Literary_Criticism_সাহিত্য_সমালোচনা"),
    "হরপ্রসাদ শাস্ত্রী": ("02_Literature_সাহিত্য", "Literary_Criticism_সাহিত্য_সমালোচনা"),
    "অসিতকুমার বন্দ্যোপাধ্যায়": ("02_Literature_সাহিত্য", "Literary_Criticism_সাহিত্য_সমালোচনা"),
    "আব্দুল মান্নান সৈয়দ": ("02_Literature_সাহিত্য", "Literary_Criticism_সাহিত্য_সমালোচনা"),
    "অতুলচন্দ্র গুপ্ত": ("02_Literature_সাহিত্য", "Literary_Criticism_সাহিত্য_সমালোচনা"),
    "অতীন্দ্র মজুমদার": ("02_Literature_সাহিত্য", "Literary_Criticism_সাহিত্য_সমালোচনা"),
    "অমূল্যধন মুখোপাধ্যায়": ("02_Literature_সাহিত্য", "Literary_Criticism_সাহিত্য_সমালোচনা"),
    "হরপ্রসাদ মিত্র": ("02_Literature_সাহিত্য", "Literary_Criticism_সাহিত্য_সমালোচনা"),
    # Humorous
    "তারাপদ রায়": ("02_Literature_সাহিত্য", "Humorous_Literature_রম্যসাহিত্য"),
    "হিমানীশ গোস্বামী": ("02_Literature_সাহিত্য", "Humorous_Literature_রম্যসাহিত্য"),
    "হানিফ সংকেত": ("02_Literature_সাহিত্য", "Humorous_Literature_রম্যসাহিত্য"),
    "কালীপ্রসন্ন সিংহ": ("02_Literature_সাহিত্য", "Humorous_Literature_রম্যসাহিত্য"),
    "টেকচাঁদ ঠাকুর": ("02_Literature_সাহিত্য", "Humorous_Literature_রম্যসাহিত্য"),
    "ত্রৈলোক্যনাথ": ("02_Literature_সাহিত্য", "Humorous_Literature_রম্যসাহিত্য"),
    "অংশুমান চক্রবর্তী": ("02_Literature_সাহিত্য", "Humorous_Literature_রম্যসাহিত্য"),
    # Travel
    "জলধর সেন": ("02_Literature_সাহিত্য", "Travel_Writing_ভ্রমণকাহিনী"),
    # Essays
    "ঈশ্বরচন্দ্র বিদ্যাসাগর": ("02_Literature_সাহিত্য", "Essays_প্রবন্ধ"),
    "অন্নদাশঙ্কর রায়": ("02_Literature_সাহিত্য", "Essays_প্রবন্ধ"),
    "আবুল ফজল": ("02_Literature_সাহিত্য", "Essays_প্রবন্ধ"),
    "কাজী মোতাহার হোসেন": ("02_Literature_সাহিত্য", "Essays_প্রবন্ধ"),
    # Short Stories
    "হাসান আজিজুল হক": ("02_Literature_সাহিত্য", "Short_Stories_ছোটগল্প"),
    "বনফুল": ("02_Literature_সাহিত্য", "Short_Stories_ছোটগল্প"),
    "জগদীশ গুপ্ত": ("02_Literature_সাহিত্য", "Short_Stories_ছোটগল্প"),
    "কৃষণ চন্দর": ("02_Literature_সাহিত্য", "Short_Stories_ছোটগল্প"),
    "গজেন্দ্রকুমার মিত্র": ("02_Literature_সাহিত্য", "Short_Stories_ছোটগল্প"),
    "আবদুশ শাকুর": ("02_Literature_সাহিত্য", "Short_Stories_ছোটগল্প"),
    "আবু ইসহাক": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    # Novels
    "হুমায়ূন আহমেদ": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "বঙ্কিমচন্দ্র চট্টোপাধ্যায়": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "বিভূতিভূষণ বন্দ্যোপাধ্যায়": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "তারাশঙ্কর বন্দ্যোপাধ্যায়": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "আশাপূর্ণা দেবী": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "ইমদাদুল হক মিলন": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "আনিসুল হক": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "কালকূট । সমরেশ বসু": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "বুদ্ধদেব গুহ": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "বিমল কর": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "জহির রায়হান": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "আখতারুজ্জামান ইলিয়াস": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "আনোয়ার পাশা": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "আলাউদ্দিন আল আজাদ": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "হরিশংকর জলদাস": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "তিলোত্তমা মজুমদার": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "বাণী বসু": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "অতীন বন্দ্যোপাধ্যায়": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "অদ্বৈত মল্লবর্মণ": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "অচিন্ত্যকুমার সেনগুপ্ত": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "আবুল বাশার": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "আহমাদ মোস্তফা কামাল": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "উপেন্দ্রনাথ গঙ্গোপাধ্যায়": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "তাহমিনা আনাম": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "দিব্যেন্দু পালিত": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "দেবেশ রায়": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "বরেন বসু": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "হর্ষ দত্ত": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "তারাদাস বন্দ্যোপাধ্যায়": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "তারকনাথ গঙ্গোপ্যাধায়": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "কাবেরী রায়চৌধুরী": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "কিন্নর রায়": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "কৃষ্ণেন্দু মুখোপাধ্যায": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "চিত্তরঞ্জন মাইতি": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
    "কিঙ্কর আহ্‌সান": ("02_Literature_সাহিত্য", "Novels_উপন্যাস"),
}

RELIGION_NON_ISLAM_SUBS = {
    "হিন্দু ধর্ম": ("01_Religion_ধর্ম", "Hinduism_হিন্দুধর্ম"),
    "বৈষ্ণব সাহিত্য": ("01_Religion_ধর্ম", "Hinduism_হিন্দুধর্ম"),
    "ভগবান শ্রী রজনীশ": ("01_Religion_ধর্ম", "Other_Religions_অন্যান্য_ধর্ম"),
}

# Islamic subfolders mapped directly to 01_Religion_ধর্ম/Islam_ইসলাম/<leaf> or non-Islam leaf
ISLAMIC_FOLDER_MAP = {
    # Quran
    "আল কুরআন এর সরল অনুবাদ": ("01_Religion_ধর্ম/Islam_ইসলাম", "Quran_কুরআন"),
    "আল কুরআন মাজিদ": ("01_Religion_ধর্ম/Islam_ইসলাম", "Quran_কুরআন"),
    "আল-কোরআন সম্পর্কে বই": ("01_Religion_ধর্ম/Islam_ইসলাম", "Quran_কুরআন"),
    "কুরআন": ("01_Religion_ধর্ম/Islam_ইসলাম", "Quran_কুরআন"),
    "কুরআন তরজমা": ("01_Religion_ধর্ম/Islam_ইসলাম", "Quran_কুরআন"),
    "কুরআনুল কারীম(ড.জাকারিয়া)": ("01_Religion_ধর্ম/Islam_ইসলাম", "Quran_কুরআন"),
    "দারসে কুরআন": ("01_Religion_ধর্ম/Islam_ইসলাম", "Quran_কুরআন"),
    "05 বিজ্ঞান ও কোরআন সম্পর্কে বই": ("01_Religion_ধর্ম/Islam_ইসলাম", "Quran_কুরআন"),
    # Tafsir
    "আহকামুল কুরআন": ("01_Religion_ধর্ম/Islam_ইসলাম", "Tafsir_তাফসীর"),
    "কাসাসুল কুরআন": ("01_Religion_ধর্ম/Islam_ইসলাম", "Tafsir_তাফসীর"),
    "কিছু তাফসিরের বই": ("01_Religion_ধর্ম/Islam_ইসলাম", "Tafsir_তাফসীর"),
    "তাফসির ইবনে কাসির নতুন সংস্করণ ঝকঝকে পৃন্ট": ("01_Religion_ধর্ম/Islam_ইসলাম", "Tafsir_তাফসীর"),
    "তাফসির ইবনে কাসির পুরাতন": ("01_Religion_ধর্ম/Islam_ইসলাম", "Tafsir_তাফসীর"),
    "তাফসিরে জিলালিল কোরআন ২২ খন্ড": ("01_Religion_ধর্ম/Islam_ইসলাম", "Tafsir_তাফসীর"),
    # Hadith
    "রিয়াদুস সালেহীন": ("01_Religion_ধর্ম/Islam_ইসলাম", "Hadith_হাদিস"),
    "সিহাহ সিত্তাহ": ("01_Religion_ধর্ম/Islam_ইসলাম", "Hadith_হাদিস"),
    "হাদীস শরীফ": ("01_Religion_ধর্ম/Islam_ইসলাম", "Hadith_হাদিস"),
    "যয়ীফ জাল হাদিস সিরিজ": ("01_Religion_ধর্ম/Islam_ইসলাম", "Hadith_হাদিস"),
    "বিষয়ভিত্তিক আয়াত হাদিস": ("01_Religion_ধর্ম/Islam_ইসলাম", "Hadith_হাদিস"),
    "মুসনাদে আহমদ": ("01_Religion_ধর্ম/Islam_ইসলাম", "Hadith_হাদিস"),
    "মুয়াত্তা ইবনে মালেক": ("01_Religion_ধর্ম/Islam_ইসলাম", "Hadith_হাদিস"),
    "খাসায়েসুল কুবরা": ("01_Religion_ধর্ম/Islam_ইসলাম", "Hadith_হাদিস"),
    "সুন্নাত": ("01_Religion_ধর্ম/Islam_ইসলাম", "Hadith_হাদিস"),
    # Fiqh
    "মাজহাব এবং ইমাম আবু হানিফা সম্পর্কে বই": ("01_Religion_ধর্ম/Islam_ইসলাম", "Fiqh_ফিকহ"),
    "মাযহাব": ("01_Religion_ধর্ম/Islam_ইসলাম", "Fiqh_ফিকহ"),
    "আশরাফুল হেদায়া": ("01_Religion_ধর্ম/Islam_ইসলাম", "Fiqh_ফিকহ"),
    "কুরবানী": ("01_Religion_ধর্ম/Islam_ইসলাম", "Fiqh_ফিকহ"),
    "হজ্জ": ("01_Religion_ধর্ম/Islam_ইসলাম", "Fiqh_ফিকহ"),
    "হজ্জ সম্পর্কে বই": ("01_Religion_ধর্ম/Islam_ইসলাম", "Fiqh_ফিকহ"),
    "রোজা,কদর ও ইতিকাফ": ("01_Religion_ধর্ম/Islam_ইসলাম", "Fiqh_ফিকহ"),
    "যাকাতের বিধান": ("01_Religion_ধর্ম/Islam_ইসলাম", "Fiqh_ফিকহ"),
    "ইদ": ("01_Religion_ধর্ম/Islam_ইসলাম", "Fiqh_ফিকহ"),
    "তারাবী": ("01_Religion_ধর্ম/Islam_ইসলাম", "Fiqh_ফিকহ"),
    # Dua & Prayer
    "দোয়া ও ওযিফা": ("01_Religion_ধর্ম/Islam_ইসলাম", "Dua_and_Prayer_দোয়া_ও_নামাজ"),
    "নামাজ সম্পর্কে বই": ("01_Religion_ধর্ম/Islam_ইসলাম", "Dua_and_Prayer_দোয়া_ও_নামাজ"),
    "সালাত (নামাজ)": ("01_Religion_ধর্ম/Islam_ইসলাম", "Dua_and_Prayer_দোয়া_ও_নামাজ"),
    "রুকাইয়া": ("01_Religion_ধর্ম/Islam_ইসলাম", "Dua_and_Prayer_দোয়া_ও_নামাজ"),
    "শবে বরাত": ("01_Religion_ধর্ম/Islam_ইসলাম", "Dua_and_Prayer_দোয়া_ও_নামাজ"),
    # Aqeedah
    "ঈমান ও আকীদা": ("01_Religion_ধর্ম/Islam_ইসলাম", "Aqeedah_আকীদাহ"),
    "তাওহীদ": ("01_Religion_ধর্ম/Islam_ইসলাম", "Aqeedah_আকীদাহ"),
    "শিরক/শির্ক": ("01_Religion_ধর্ম/Islam_ইসলাম", "Aqeedah_আকীদাহ"),
    "বিদাত": ("01_Religion_ধর্ম/Islam_ইসলাম", "Aqeedah_আকীদাহ"),
    "পরকাল/আখিরাত": ("01_Religion_ধর্ম/Islam_ইসলাম", "Aqeedah_আকীদাহ"),
    "কবর": ("01_Religion_ধর্ম/Islam_ইসলাম", "Aqeedah_আকীদাহ"),
    "জান্নাত জাহান্নাম": ("01_Religion_ধর্ম/Islam_ইসলাম", "Aqeedah_আকীদাহ"),
    "মৃত্যু": ("01_Religion_ধর্ম/Islam_ইসলাম", "Aqeedah_আকীদাহ"),
    "জীন জাতি": ("01_Religion_ধর্ম/Islam_ইসলাম", "Aqeedah_আকীদাহ"),
    "01 ফিতনাহ্ সম্পর্কে বই ও হাদীস গ্রন্থ": ("01_Religion_ধর্ম/Islam_ইসলাম", "Aqeedah_আকীদাহ"),
    "02 ইমাম মাহমুদ এবং সাহেব কিরান সম্পর্কে বিস্তারিত": ("01_Religion_ধর্ম/Islam_ইসলাম", "Aqeedah_আকীদাহ"),
    "04 দাজ্জাল সম্পর্কে বই": ("01_Religion_ধর্ম/Islam_ইসলাম", "Aqeedah_আকীদাহ"),
    "06 কিয়ামতের আলামত ও শেষ জামানা সম্পর্কে আলোচনা": ("01_Religion_ধর্ম/Islam_ইসলাম", "Aqeedah_আকীদাহ"),
    "ঈদে মিলাদুন্নাবী সম্পর্কে বই": ("01_Religion_ধর্ম/Islam_ইসলাম", "Aqeedah_আকীদাহ"),
    "ড. আব্দুল্লা জাহাঙ্গীর": ("01_Religion_ধর্ম/Islam_ইসলাম", "Aqeedah_আকীদাহ"),
    "আবু বকর জাকারিয়া": ("01_Religion_ধর্ম/Islam_ইসলাম", "Aqeedah_আকীদাহ"),
    "আব্দুর রাজ্জাক বিন ইউসুফ": ("01_Religion_ধর্ম/Islam_ইসলাম", "Aqeedah_আকীদাহ"),
    "নাস্তিকতা ও সংশয়বাদ": ("01_Religion_ধর্ম/Islam_ইসলাম", "Aqeedah_আকীদাহ"),
    "ডাবল স্ট্যান্ডার্ড": ("01_Religion_ধর্ম/Islam_ইসলাম", "Aqeedah_আকীদাহ"),
    "বৈজ্ঞানিক মুহাম্মদ": ("01_Religion_ধর্ম/Islam_ইসলাম", "Aqeedah_আকীদাহ"),
    "ইসলাম ও বিজ্ঞান": ("01_Religion_ধর্ম/Islam_ইসলাম", "Aqeedah_আকীদাহ"),
    # Seerah, Prophets, Sahaba, History
    "রাহীকুল মাখতুম": ("01_Religion_ধর্ম/Islam_ইসলাম", "Seerah_সীরাত"),
    "সীরাতুন নবী": ("01_Religion_ধর্ম/Islam_ইসলাম", "Seerah_সীরাত"),
    "সীরাতুল মোস্তফা": ("01_Religion_ধর্ম/Islam_ইসলাম", "Seerah_সীরাত"),
    "সীরাতে বিশ্বকোষ": ("01_Religion_ধর্ম/Islam_ইসলাম", "Seerah_সীরাত"),
    "সীরাতে সারোয়ারে আলম": ("01_Religion_ধর্ম/Islam_ইসলাম", "Seerah_সীরাত"),
    "মিরাজ/মেরাজ": ("01_Religion_ধর্ম/Islam_ইসলাম", "Seerah_সীরাত"),
    "নবীনদের কাহিনি": ("01_Religion_ধর্ম/Islam_ইসলাম", "Prophets_নবী_রাসূল"),
    "আসহাবে রাসুলের জিবন কথা": ("01_Religion_ধর্ম/Islam_ইসলাম", "Sahaba_সাহাবী"),
    "সাহাবীদের জীবন ও কর্ম": ("01_Religion_ধর্ম/Islam_ইসলাম", "Sahaba_সাহাবী"),
    "হায়াতুস সাহাবা": ("01_Religion_ধর্ম/Islam_ইসলাম", "Sahaba_সাহাবী"),
    "খালিদ বিন ওয়ালীদ": ("01_Religion_ধর্ম/Islam_ইসলাম", "Sahaba_সাহাবী"),
    "তাবীঈদের জীবন কথা": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_History_ইসলামের_ইতিহাস"),
    "ইমামদের জীবন ও কর্ম": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_History_ইসলামের_ইতিহাস"),
    "আল বিদায়া অননিহায়য়া ইসলামের আদি-অন্ত ইতিহাস": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_History_ইসলামের_ইতিহাস"),
    "ইসলামের ইতিহাস": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_History_ইসলামের_ইতিহাস"),
    "কারবালা": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_History_ইসলামের_ইতিহাস"),
    "ক্রুসেড যুদ্ধ": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_History_ইসলামের_ইতিহাস"),
    "ক্রুসেড সিরিজ": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_History_ইসলামের_ইতিহাস"),
    "আফগানিস্তান": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_History_ইসলামের_ইতিহাস"),
    "ড. আলী মুহাম্মাদ সাল্লাবি": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_History_ইসলামের_ইতিহাস"),
    "স্পেনের রূপসী কন্যা": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_History_ইসলামের_ইতিহাস"),
    "আল মুকাদ্দিমাহ": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_History_ইসলামের_ইতিহাস"),
    # Islamic Economics & Politics
    "ইসলামী অর্থনীতি,ব্যাংক,সুদ ও ব্যবসা": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Economics_ইসলামী_অর্থনীতি"),
    "ইসলাম ও গনতন্ত্র": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Politics_ইসলামী_রাজনীতি"),
    "আবুল আলা মওদুদী": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Politics_ইসলামী_রাজনীতি"),
    "জিহাদ": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Politics_ইসলামী_রাজনীতি"),
    "03 জিহাদ সম্পর্কে বই": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Politics_ইসলামী_রাজনীতি"),
    "গাজওয়াতুল হিন্দ": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Politics_ইসলামী_রাজনীতি"),
    "মোসাদ": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Politics_ইসলামী_রাজনীতি"),
    "আসিফ আদনান": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Politics_ইসলামী_রাজনীতি"),
    # Islamic Philosophy
    "ইমাম গাজ্জালী": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Philosophy_ইসলামী_দর্শন"),
    # Islamic Lifestyle & Dawah
    "ইসলাম ও আমাদের জীবন": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Lifestyle_ইসলামী_জীবনব্যবস্থা"),
    "বিয়ে ও দাম্পত্য": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Lifestyle_ইসলামী_জীবনব্যবস্থা"),
    "পর্দা": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Lifestyle_ইসলামী_জীবনব্যবস্থা"),
    "সন্তান ও মাতাপিতা": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Lifestyle_ইসলামী_জীবনব্যবস্থা"),
    "নারী": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Lifestyle_ইসলামী_জীবনব্যবস্থা"),
    "দাওয়াত": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Lifestyle_ইসলামী_জীবনব্যবস্থা"),
    "গুনাহ ও তওবা": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Lifestyle_ইসলামী_জীবনব্যবস্থা"),
    "অহংকার": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Lifestyle_ইসলামী_জীবনব্যবস্থা"),
    "নফস": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Lifestyle_ইসলামী_জীবনব্যবস্থা"),
    "ফাজায়েলে আমল": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Lifestyle_ইসলামী_জীবনব্যবস্থা"),
    "বেহেশতী জেওর": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Lifestyle_ইসলামী_জীবনব্যবস্থা"),
    "আশরাফ আলী থানবী": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Lifestyle_ইসলামী_জীবনব্যবস্থা"),
    "দেলোয়ার হুসেন সাঈদী": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Lifestyle_ইসলামী_জীবনব্যবস্থা"),
    "তকী উসমানী": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Lifestyle_ইসলামী_জীবনব্যবস্থা"),
    "ইউসুফ কারযাভী": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Lifestyle_ইসলামী_জীবনব্যবস্থা"),
    "আবুল হাসান নদবী": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Lifestyle_ইসলামী_জীবনব্যবস্থা"),
    "ড. কাবীরুল ইসলাম": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Lifestyle_ইসলামী_জীবনব্যবস্থা"),
    "চরমোনাই পীরের বই": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Lifestyle_ইসলামী_জীবনব্যবস্থা"),
    "পর্নোগ্রাফি ও হস্তমৈথুন থেকে বাঁচুন": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Lifestyle_ইসলামী_জীবনব্যবস্থা"),
    "শয়তান": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Lifestyle_ইসলামী_জীবনব্যবস্থা"),
    "শয়তানের বেহেশত": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Lifestyle_ইসলামী_জীবনব্যবস্থা"),
    "নেক সুরতে শয়তানের ধোঁকা": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Lifestyle_ইসলামী_জীবনব্যবস্থা"),
    "আতিক উল্লাহ": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Lifestyle_ইসলামী_জীবনব্যবস্থা"),
    "আই লাভ ইউ": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Lifestyle_ইসলামী_জীবনব্যবস্থা"),
    # Islamic Literature & Children
    "ইসলামী গল্প": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Literature_ইসলামী_সাহিত্য"),
    "আরিফ আজাদ": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Literature_ইসলামী_সাহিত্য"),
    "শামসুল আরেফীন": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Literature_ইসলামী_সাহিত্য"),
    "আলোর কাফেলা": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Literature_ইসলামী_সাহিত্য"),
    "ফেরা": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Literature_ইসলামী_সাহিত্য"),
    "মুক্তবাসিনী": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Literature_ইসলামী_সাহিত্য"),
    "কাসিদায়ে শাহ্ নেয়ামতুল্লাহ্": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Literature_ইসলামী_সাহিত্য"),
    "সানজিক ই উসমান": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Literature_ইসলামী_সাহিত্য"),
    "শিশুদের নাম": ("01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Children_Books_শিশুদের_ইসলাম"),
    # Non-Islam buckets from Islamic collections
    "তুলনামূলক ধর্মতত্ত্ব": ("01_Religion_ধর্ম", "Comparative_Religion_তুলনামূলক_ধর্ম"),
    "ইজহারুল হক": ("01_Religion_ধর্ম", "Comparative_Religion_তুলনামূলক_ধর্ম"),
    "জাকির নায়েক": ("01_Religion_ধর্ম", "Comparative_Religion_তুলনামূলক_ধর্ম"),
    "ইসলাম ও অন্যান্য": ("01_Religion_ধর্ম", "Comparative_Religion_তুলনামূলক_ধর্ম"),
    "আরবী ভাষা শিক্ষা বই": ("16_Language_and_Linguistics_ভাষা_ও_ভাষাবিজ্ঞান", "Arabic_Language_আরবি_ভাষা"),
    "ইসলামি বিশ্বকোষ": ("23_Reference_Books_তথ্যসূত্র", "Encyclopedia_বিশ্বকোষ"),
    "ইসলামী বিশ্বকোষ": ("23_Reference_Books_তথ্যসূত্র", "Encyclopedia_বিশ্বকোষ"),
    "ইসলাম ও চিকিৎসা": ("13_Medicine_and_Health_চিকিৎসা_ও_স্বাস্থ্য", "Alternative_Medicine_বিকল্প_চিকিৎসা"),
}

# Known non-author folder names in Mrinal
NON_AUTHOR_MRINAL_FOLDERS = {
    "অভিধান", "অনুবাদ সাহিত্য", "আমার একাত্তর", "ই-পাব", "এবং সাহিত্য",
    "ছোটদের বই", "টিনটিন সিরিজ", "বাংলা একাডেমি", "বাংলা ছন্দ ও অলঙ্কার",
    "বাংলা প্রবাদ প্রবচন", "বাংলা মোটিভেশনাল বই", "বাংলাদেশ",
    "বাংলাদেশের ইতিহাস", "বাউল গান", "বিবিধ", "বৈষ্ণব সাহিত্য",
    "হিন্দু ধর্ম", "চর্যাপদ", "জলের গান", "মৃণালের ই-লাইব্রেরি",
}

KNOWN_ISLAMIC_AUTHOR_FOLDERS = {
    "আতিক উল্লাহ", "আবু বকর জাকারিয়া", "আবুল আলা মওদুদী", "আবুল হাসান নদবী",
    "আব্দুর রাজ্জাক বিন ইউসুফ", "আরিফ আজাদ", "আশরাফ আলী থানবী", "আসিফ আদনান",
    "ইউসুফ কারযাভী", "ইমাম গাজ্জালী", "জাকির নায়েক", "ড. আব্দুল্লা জাহাঙ্গীর",
    "ড. কাবীরুল ইসলাম", "ড. আলী মুহাম্মাদ সাল্লাবি", "তকী উসমানী",
    "দেলোয়ার হুসেন সাঈদী", "শামসুল আরেফীন",
}

AUTHOR_KEYWORDS = [
    ("হুমায়ূন আহমেদ", "হুমায়ূন আহমেদ"), ("হুমায়ূন আহমেদ", "হুমায়ূন আহমেদ"), ("humayun ahmed", "হুমায়ূন আহমেদ"),
    ("রবীন্দ্রনাথ", "রবীন্দ্রনাথ ঠাকুর"), ("rabindranath", "রবীন্দ্রনাথ ঠাকুর"),
    ("নজরুল ইসলাম", "কাজী নজরুল ইসলাম"), ("nazrul", "কাজী নজরুল ইসলাম"),
    ("শরৎচন্দ্র", "শরৎচন্দ্র চট্টোপাধ্যায়"), ("বঙ্কিমচন্দ্র", "বঙ্কিমচন্দ্র চট্টোপাধ্যায়"),
    ("মানিক বন্দ্যোপাধ্যায়", "মানিক বন্দ্যোপাধ্যায়"), ("বিভূতিভূষণ", "বিভূতিভূষণ বন্দ্যোপাধ্যায়"),
    ("তারাশঙ্কর", "তারাশঙ্কর বন্দ্যোপাধ্যায়"), ("সত্যজিৎ রায়", "সত্যজিৎ রায়"), ("সত্যজিৎ রায়", "সত্যজিৎ রায়"),
    ("জাফর ইকবাল", "মুহম্মদ জাফর ইকবাল"), ("zafar iqbal", "মুহম্মদ জাফর ইকবাল"),
    ("সুনীল গঙ্গোপাধ্যায়", "সুনীল গঙ্গোপাধ্যায়"), ("শীর্ষেন্দু", "শীর্ষেন্দু মুখোপাধ্যায়"),
    ("সমরেশ মজুমদার", "সমরেশ মজুমদার"), ("সমরেশ বসু", "সমরেশ বসু"),
    ("আহমদ ছফা", "আহমদ ছফা"), ("জহির রায়হান", "জহির রায়হান"), ("জহির রায়হান", "জহির রায়হান"),
    ("আরিফ আজাদ", "আরিফ আজাদ"), ("arif azad", "আরিফ আজাদ"),
    ("জাহাঙ্গীর", "ড. খোন্দকার আব্দুল্লাহ জাহাঙ্গীর"), ("আব্দুল্লাহ জাহাঙ্গীর", "ড. খোন্দকার আব্দুল্লাহ জাহাঙ্গীর"),
    ("মওদুদী", "সৈয়দ আবুল আ'লা মওদুদী"), ("maududi", "সৈয়দ আবুল আ'লা মওদুদী"),
    ("ইবনে কাসির", "ইমাম ইবনে কাসির (রহ.)"), ("ibn kathir", "ইমাম ইবনে কাসির (রহ.)"),
    ("সাইয়েদ কুতুব", "সাইয়েদ কুতুব শহীদ"), ("জিলালিল", "সাইয়েদ কুতুব শহীদ"),
    ("গাজ্জালী", "ইমাম আল-গাজ্জালী (রহ.)"), ("ghazali", "ইমাম আল-গাজ্জালী (রহ.)"),
    ("জাকারিয়া", "ড. আবু বকর মুহাম্মাদ যাকারিয়া"), ("জাকারিয়া", "ড. আবু বকর মুহাম্মাদ যাকারিয়া"),
    ("যাকারিয়া", "ড. আবু বকর মুহাম্মাদ যাকারিয়া"), ("zakaria", "ড. আবু বকর মুহাম্মাদ যাকারিয়া"),
    ("জাকির নায়েক", "ড. জাকির নায়েক"), ("জাকির নায়েক", "ড. জাকির নায়েক"), ("zakir naik", "ড. জাকির নায়েক"),
    ("তকী উসমানী", "মুফতি মুহাম্মাদ তাকি উসমানি"), ("তাকি উসমানি", "মুফতি মুহাম্মাদ তাকি উসমানি"), ("taqi usmani", "মুফতি মুহাম্মাদ তাকি উসমানি"),
    ("আশরাফ আলী থানবী", "মাওলানা আশরাফ আলী থানবী (রহ.)"), ("থানবী", "মাওলানা আশরাফ আলী থানবী (রহ.)"),
    ("ইউসুফ কারযাভী", "ড. ইউসুফ আল-কারযাভী"), ("কারযাভী", "ড. ইউসুফ আল-কারযাভী"),
    ("নদবী", "মাওলানা আবুল হাসান আলী নদবী (রহ.)"), ("nadwi", "মাওলানা আবুল হাসান আলী নদবী (রহ.)"),
    ("সাল্লাবি", "ড. আলী মুহাম্মাদ সাল্লাবি"), ("sallabi", "ড. আলী মুহাম্মাদ সাল্লাবি"),
    ("ইমাম বুখারী", "ইমাম মুহাম্মাদ আল-বুখারী (রহ.)"), ("বুখারী", "ইমাম মুহাম্মাদ আল-বুখারী (রহ.)"),
    ("মুসলিম শরীফ", "ইমাম মুসলিম ইবনুল হাজ্জাজ (রহ.)"), ("রিয়াদুস সালেহীন", "ইমাম আন-নববী (রহ.)"),
    ("রিয়াদুস সালেহিন", "ইমাম আন-নববী (রহ.)"), ("আসিম আল হাকিম", "শায়খ আসিম আল-হাকিম"),
    ("ইবনে তাইমিয়া", "ইমাম ইবনে তাইমিয়া (রহ.)"), ("ইবনে তাইমিয়া", "ইমাম ইবনে তাইমিয়া (রহ.)"),
    ("ইবনুল কাইয়্যিম", "ইমাম ইবনুল কাইয়্যিম (রহ.)"), ("ইবনুল কাইয়্যিম", "ইমাম ইবনে তাইমিয়া / ইবনুল কাইয়্যিম"),
    ("মুহাম্মাদ ইবনে আবদুল ওয়াহহাব", "শায়খ মুহাম্মাদ ইবনে আবদুল ওয়াহহাব"),
    ("আসিফ আদনান", "আসিফ আদনান"), ("শামসুল আরেফীন", "শামসুল আরেফীন শক্তি"),
    ("মীযানুর রহমান", "ড. মিজানুর রহমান আজহারী"), ("মিজানুর রহমান আজহারী", "ড. মিজানুর রহমান আজহারী"),
    ("সাঈদী", "আল্লামা দেলোয়ার হোসাইন সাঈদী"), ("দেলোয়ার", "আল্লামা দেলোয়ার হোসাইন সাঈদী"),
    ("আব্দুর রাজ্জাক বিন ইউসুফ", "শায়খ আব্দুর রাজ্জাক বিন ইউসুফ"),
    ("তারিক জামিল", "মাওলানা তারিক জামিল"), ("মাহমুদুল হাসান", "মাওলানা মাহমুদুল হাসান"),
    ("আরিফুল ইসলাম", "আরিফুল ইসলাম"), ("নুমান আলী খান", "উস্তাদ নুমান আলী খান"),
    ("নসীম হিজাযী", "নসীম হিজাযী"), ("নাসিম হিজাযী", "নসীম হিজাযী"),
    ("সাইমুম", "আবুল আসাদ"), ("আবুল আসাদ", "আবুল আসাদ"),
    ("আলতামাশ", "ইনায়েতুল্লাহ আলতামাশ"), ("হারুন ইয়াহইয়া", "হারুন ইয়াহিয়া"), ("harun yahya", "হারুন ইয়াহিয়া"),
    ("মিজানুর রহমান", "ড. মিজানুর রহমান"), ("বিবেকানন্দ", "স্বামী বিবেকানন্দ"), ("vivekananda", "স্বামী বিবেকানন্দ"),
    ("ঝংকার মাহবুব", "ঝংকার মাহবুব"), ("jhankar mahbub", "ঝংকার মাহবুব"),
    ("আয়মান সাদিক", "আয়মান সাদিক"), ("ayman sadiq", "আয়মান সাদিক"),
]

PUBLICATION_RULES = [
    (["বাংলা একাডেমি", "bangla academy", "বাংলাদেশের লোকজ সংস্কৃতি গ্রন্থমালা"], "বাংলা একাডেমি (Bangla Academy)"),
    (["ইসলামিক ফাউন্ডেশন", "islamic foundation", "ইফা ", "ifb"], "ইসলামিক ফাউন্ডেশন বাংলাদেশ (Islamic Foundation)"),
    (["সমকালীন", "somokalin"], "সমকালীন প্রকাশন (Somokalin Prokashon)"),
    (["সিয়ান", "সিয়ান", "sean publication"], "সিয়ান পাবলিকেশন (Sean Publication)"),
    (["গার্ডিয়ান", "guardian"], "গার্ডিয়ান পাবলিকেশন্স (Guardian Publications)"),
    (["রাহনুমা", "rahnuma"], "রাহনুমা প্রকাশনী (Rahnuma Prokashoni)"),
    (["মাকতাবাতুল আসলাফ", "আসলাফ"], "মাকতাবাতুল আসলাফ (Maktabatul Aslaf)"),
    (["মাকতাবাতুল আযহার"], "মাকতাবাতুল আযহার (Maktabatul Azhar)"),
    (["মাকতাবাতুল ইসলাম"], "মাকতাবাতুল ইসলাম (Maktabatul Islam)"),
    (["তাওহীদ পাবলিকেশন", "tawheed"], "তাওহীদ পাবলিকেশন্স (Tawheed Publications)"),
    (["হাদীস একাডেমী", "হাদিস একাডেমি", "hadith academy"], "হাদীস একাডেমী (Hadith Academy)"),
    (["দারুস সালাম", "darussalam"], "দারুস সালাম পাবলিকেশন্স (Darussalam)"),
    (["এমদাদিয়া", "এমদাদিয়া"], "এমদাদিয়া লাইব্রেরি (Emdadia Library)"),
    (["আহসান পাবলিকেশন", "ahsan"], "আহসান পাবলিকেশন (Ahsan Publication)"),
    (["সন্দীপন", "শব্দকথা", "কথাপ্রকাশ"], "কথাপ্রকাশ / সন্দীপন"),
    (["প্রথমা", "prothoma"], "প্রথমা প্রকাশন (Prothoma Prokashon)"),
    (["অন্যপ্রকাশ", "anyaprokash"], "অন্যপ্রকাশ (Anyaprokash)"),
    (["আনন্দ পাবলিশার্স", "ananda"], "আনন্দ পাবলিশার্স (Ananda Publishers)"),
    (["সেবা প্রকাশনী", "সেবা", "তিন গোয়েন্দা", "মাসুদ রানা", "কাজী আনোয়ার হোসেন"], "সেবা প্রকাশনী (Seba Prokashoni)"),
    (["বিশ্বসাহিত্য কেন্দ্র"], "বিশ্বসাহিত্য কেন্দ্র (Bishwo Shahitto Kendro)"),
    (["আদর্শ", "adarsha"], "আদর্শ প্রকাশনী (Adarsha)"),
    (["মাওলা ব্রাদার্স", "mowla"], "মাওলা ব্রাদার্স (Mowla Brothers)"),
    (["সময় প্রকাশন", "সময় প্রকাশন"], "সময় প্রকাশন (Somoy Prokashon)"),
    (["কাকলী প্রকাশনী", "কাকলী"], "কাকলী প্রকাশনী (Kakoli Prokashoni)"),
    (["তাম্রলিপি", "tamralipi"], "তাম্রলিপি (Tamralipi)"),
    (["পাঞ্জেরী", "panjeree"], "পাঞ্জেরী পাবলিকেশন্স (Panjeree)"),
    (["মিত্র ও ঘোষ"], "মিত্র ও ঘোষ পাবলিশার্স (Mitra & Ghosh)"),
    (["দে'জ", "dey's"], "দে'জ পাবলিশিং (Dey's Publishing)"),
    (["কুরআন একাডেমী", "কোরআন একাডেমি"], "বাংলাদেশ কুরআন একাডেমী"),
    (["amarboi.com", "amarboi"], "AmarBoi Digital Edition"),
    (["pdfhorse"], "PDFHorse Digital Edition"),
    (["subahesadiq"], "Subahe Sadiq Digital Archive"),
    (["টিনটিন"], "এগমন্ট / আনন্দ (টিনটিন বাংলা সংস্করণ)"),
]


def safe_fs_name(name: str) -> str:
    s = re.sub(r'[<>:"/\\|?*]', "-", name).strip().rstrip(".")
    return s or "Untitled"


def fmt_size(b: int) -> str:
    if not b:
        return "-"
    for unit in ["B", "KB", "MB", "GB"]:
        if b < 1024:
            return f"{b:.1f} {unit}" if unit != "B" else f"{b} B"
        b /= 1024
    return f"{b:.2f} TB"


def md_escape(s: str) -> str:
    return s.replace("|", "\\|").replace("[", "\\[").replace("]", "\\]").replace("\n", " ").strip()


def classify_book_leaf(item: dict) -> tuple[str, str, str | None, bool]:
    """
    Returns (top_path, leaf_subcat, subfolder_name_or_none, is_mixed_individual_move)
    where top_path is e.g. '01_Religion_ধর্ম/Islam_ইসলাম' or '02_Literature_সাহিত্য'.
    """
    old_cat = item["category"]
    old_sub = item["subfolder"]
    fname = item["name"]
    spath = item.get("source_path", "")
    text = f"{old_sub} {spath} {fname}".lower()

    is_mixed = (old_cat, old_sub) in MIXED_SUBFOLDERS

    if not is_mixed:
        if old_sub in ISLAMIC_FOLDER_MAP:
            tp, leaf = ISLAMIC_FOLDER_MAP[old_sub]
            return tp, leaf, old_sub, False
        if old_sub in RELIGION_NON_ISLAM_SUBS:
            tp, leaf = RELIGION_NON_ISLAM_SUBS[old_sub]
            return tp, leaf, old_sub, False
        if old_sub in SCIENCE_SUBS:
            tp, leaf = SCIENCE_SUBS[old_sub]
            return tp, leaf, old_sub, False
        if old_sub in FICTION_SUBS:
            tp, leaf = FICTION_SUBS[old_sub]
            return tp, leaf, old_sub, False
        if old_sub in CHILDREN_SUBS:
            tp, leaf = CHILDREN_SUBS[old_sub]
            return tp, leaf, old_sub, False
        if old_sub in HISTORY_POLITICS_SOCIAL_SUBS:
            tp, leaf = HISTORY_POLITICS_SOCIAL_SUBS[old_sub]
            return tp, leaf, old_sub, False
        if old_sub in LANG_SELF_ARTS_SUBS:
            tp, leaf = LANG_SELF_ARTS_SUBS[old_sub]
            return tp, leaf, old_sub, False
        if old_sub in LITERATURE_SUBS:
            tp, leaf = LITERATURE_SUBS[old_sub]
            return tp, leaf, old_sub, False
        if old_cat == "06 - Literature & Authors (Mrinal e-Library)":
            return "02_Literature_সাহিত্য", "Collected_Works_রচনাবলী", old_sub, False
        # Fallback for any remaining Islamic subfolder
        return "01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Lifestyle_ইসলামী_জীবনব্যবস্থা", old_sub, False

    # Individual per-file classification for mixed/generic folders (zero books left in open/unclassified!)
    # Check specific non-Islamic items first
    if any(k in text for k in ["vivekananda", "ঋগ্বেদ", "যজুর্ব্বেদ", "সামবেদ", "পুরাণ", "গীতা", "রামায়ণ", "মহাভারত", "হিন্দু", "বেদ", "উপনিষদ"]):
        return "01_Religion_ধর্ম", "Hinduism_হিন্দুধর্ম", "হিন্দু ধর্ম গ্রন্থ", True
    if any(k in text for k in ["বুদ্ধ", "বৌদ্ধ", "ত্রিপিটক", "buddh"]):
        return "01_Religion_ধর্ম", "Buddhism_বৌদ্ধধর্ম", None, True
    if any(k in text for k in ["বাইবেল", "খ্রিষ্ট", "খ্রিস্ট", "christian", "jesus", "bible"]):
        return "01_Religion_ধর্ম", "Christianity_খ্রিষ্টধর্ম", None, True
    if any(k in text for k in ["bangobandhu", "১৯৭১", "1971", "মুক্তিযুদ্ধ", "liberation war", "একাত্তর"]):
        return "06_History_ইতিহাস", "Liberation_War_মুক্তিযুদ্ধ", None, True
    if any(k in text for k in ["মানসাঙ্ক", "mansanka", "গণিত", "math", "algebra", "geometry"]):
        return "04_Science_বিজ্ঞান", "Mathematics_গণিত", None, True
    if any(k in text for k in ["অভিজিৎ রায়", "আলো হাতে চলিয়াছে", "বিজ্ঞান", "science", "physics", "evolution", "বিবর্তন"]):
        return "04_Science_বিজ্ঞান", "General_Science_সাধারণ_বিজ্ঞান", None, True
    if any(k in text for k in ["মাকতাবায়ে শামেলা", "মাক্তাবা শামেলা", "software", "computer", "programming", "python"]):
        return "05_Computer_and_Technology_কম্পিউটার_ও_প্রযুক্তি", "Computer_Science_কম্পিউটার_বিজ্ঞান", None, True
    if any(k in text for k in ["raw-a history", "আওয়ামী", "রাজনীতি", "democracy", "গণতন্ত্র", "সংবিধান", "covert operations"]):
        return "07_Politics_and_Government_রাজনীতি_ও_সরকার", "Political_Parties_রাজনৈতিক_দল", None, True
    if any(k in text for k in ["dictionary", "অভিধান", "vocabulary", "আরবি", "আরবী", "arabic", "ব্যাকরণ", "grammar"]):
        if "কুরআন" in text or "quran" in text:
            return "01_Religion_ধর্ম/Islam_ইসলাম", "Quran_কুরআন", None, True
        return "16_Language_and_Linguistics_ভাষা_ও_ভাষাবিজ্ঞান", "Arabic_Language_আরবি_ভাষা", None, True
    if any(k in text for k in ["ক্যালেন্ডার", "পঞ্জিকা", "calendar"]):
        return "23_Reference_Books_তথ্যসূত্র", "Almanacs_পঞ্জিকা", None, True

    # Non-Islamic Mrinal misc/epub
    if old_cat == "06 - Literature & Authors (Mrinal e-Library)":
        if any(k in text for k in ["গল্প", "story", "stories"]):
            return "02_Literature_সাহিত্য", "Short_Stories_ছোটগল্প", None, True
        if any(k in text for k in ["কবিতা", "কাব্য", "poem", "poetry"]):
            return "02_Literature_সাহিত্য", "Poetry_কবিতা", None, True
        if any(k in text for k in ["নাটক", "drama"]):
            return "02_Literature_সাহিত্য", "Drama_নাটক", None, True
        if any(k in text for k in ["ভ্রমণ", "travel"]):
            return "02_Literature_সাহিত্য", "Travel_Writing_ভ্রমণকাহিনী", None, True
        if any(k in text for k in ["জীবনী", "আত্মজীবনী", "স্মৃতি"]):
            return "02_Literature_সাহিত্য", "Autobiography_আত্মজীবনী", None, True
        if any(k in text for k in ["প্রবন্ধ", "সমালোচনা"]):
            return "02_Literature_সাহিত্য", "Essays_প্রবন্ধ", None, True
        return "02_Literature_সাহিত্য", "Novels_উপন্যাস", None, True

    # Islamic individual classification
    if any(k in text for k in ["তাফসির", "তাফসীর", "tafsir", "কাসাসুল কুরআন", "আহকামুল কুরআন", "শানে নুযূল"]):
        return "01_Religion_ধর্ম/Islam_ইসলাম", "Tafsir_তাফসীর", None, True
    if any(k in text for k in ["কুরআন", "কোরআন", "quran", "ক্বিরআত", "তাজবীদ", "তাজবিদ", "মাজিদ", "সূরা", "সুরা"]):
        return "01_Religion_ধর্ম/Islam_ইসলাম", "Quran_কুরআন", None, True
    if any(k in text for k in ["হাদিস", "হাদীস", "hadith", "বুখারী", "মুসলিম", "তিরমিযী", "নাসাঈ", "আবু দাউদ", "ইবনে মাজাহ", "মিশকাত", "রিয়াদুস", "সুন্নাত", "sunnah", "আসারুস", "মুসনাদ", "ফিরদাউস", "ফিরদৌস", "শামায়েল"]):
        return "01_Religion_ধর্ম/Islam_ইসলাম", "Hadith_হাদিস", None, True
    if any(k in text for k in ["নামাজ", "নামায", "সালাত", "দোয়া", "দোয়া", "দুআ", "দু'আ", "মুনাজাত", "ওযু", "অজু", "যিকির", "জিকির", "তাসবীহ", "রুকাইয়া", "শিফা", "salah", "salat", "dua"]):
        return "01_Religion_ধর্ম/Islam_ইসলাম", "Dua_and_Prayer_দোয়া_ও_নামাজ", None, True
    if any(k in text for k in ["ফিকহ", "ফতোয়া", "ফাতাওয়া", "মাসআলা", "মাসায়েল", "হালাল", "হারাম", "রোজা", "রোযা", "সিয়াম", "সিয়াম", "যাকাত", "জাকাত", "হজ্জ", "হজ", "ওমরাহ", "কুরবানী", "কোরবানি", "ইতিকাফ", "মাজহাব", "মাযহাব", "তালাক", "উত্তরাধিকার", "ফারায়েজ", "fiqh", "fatwa"]):
        return "01_Religion_ধর্ম/Islam_ইসলাম", "Fiqh_ফিকহ", None, True
    if any(k in text for k in ["নবী ", "নবীদের", "রাসুল", "রাসূল", "নূহ", "ইব্রাহিম", "ইবরাহীম", "মূসা", "মুসা", "ঈসা", "দাউদ", "সুলাইমান", "ইউসুফ", "আদম", "prophet"]):
        if any(s in text for s in ["সীরাত", "সিরাত", "মুহাম্মদ", "মুহাম্মাদ", "রাসুলুল্লাহ", "রাসূলুল্লাহ", "নবীজি", "নবী করীম", "seerah", "sirat", "মদিনা", "মক্কা", "বদর", "ওহুদ", "হুদাইবিয়া", "বিদায় হজ"]):
            return "01_Religion_ধর্ম/Islam_ইসলাম", "Seerah_সীরাত", None, True
        return "01_Religion_ধর্ম/Islam_ইসলাম", "Prophets_নবী_রাসূল", None, True
    if any(k in text for k in ["সীরাত", "সিরাত", "seerah", "sirat", "রাহীকুল", "নবীজী", "নবীজি", "রাসুলুল্লাহ"]):
        return "01_Religion_ধর্ম/Islam_ইসলাম", "Seerah_সীরাত", None, True
    if any(k in text for k in ["সাহাবী", "সাহাবি", "সাহাবা", "আবু বকর", "ওমর", "উমর", "উসমান", "আলী (রা", "খালিদ বিন", "আয়েশা", "ফাতেমা", "বেলাল", "সালমান ফারসি", "আসহাবে", "sahaba", "imaams"]):
        return "01_Religion_ধর্ম/Islam_ইসলাম", "Sahaba_সাহাবী", None, True
    if any(k in text for k in ["অর্থনীতি", "সুদ", "ব্যাংক", "ব্যবসা", "বাণিজ্য", "রিবা", "economics"]):
        return "01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Economics_ইসলামী_অর্থনীতি", None, True
    if any(k in text for k in ["রাজনীতি", "খিলাফত", "খেলাফত", "জিহাদ", "ইসলামী রাষ্ট্র", "উম্মাহ", "গণতন্ত্র", "politics"]):
        return "01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Politics_ইসলামী_রাজনীতি", None, True
    if any(k in text for k in ["দর্শন", "তাসাউফ", "আধ্যাত্মিক", "গাজ্জালী", "ইকবাল", "দর্শন", "philosophy"]):
        return "01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Philosophy_ইসলামী_দর্শন", None, True
    if any(k in text for k in ["শিশু", "কিশোর", "সোনামণি", "ছোটদের", "বর্ণমালা", "children", "kids"]):
        return "01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Children_Books_শিশুদের_ইসলাম", None, True
    if any(k in text for k in ["ইতিহাস", "যুদ্ধ", "ক্রুসেড", "স্পেন", "অটোমান", "উসমানীয়", "আন্দালুস", "কারবালা", "বাগদাদ", "history", "আব্বাসীয়", "উমাইয়া"]):
        return "01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_History_ইসলামের_ইতিহাস", None, True
    if any(k in text for k in ["আকীদা", "আকিদা", "ঈমান", "তাওহীদ", "তৌহিদ", "শিরক", "শির্ক", "বিদআত", "বিদাত", "দাজ্জাল", "কিয়ামত", "কিয়ামত", "ফিতনা", "জান্নাত", "জাহান্নাম", "কবর", "আখিরাত", "মৃত্যু", "নাস্তিক", "aqeedah", "fitan"]):
        return "01_Religion_ধর্ম/Islam_ইসলাম", "Aqeedah_আকীদাহ", None, True
    if any(k in text for k in ["গল্প", "উপন্যাস", "কাহিনী", "কাহিনি", "সিরিজ", "সাইমুম", "কবিতা", "সাহিত্য", "উপহার", "অশ্রু", "আঁধার", "অন্য পথের"]):
        return "01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Literature_ইসলামী_সাহিত্য", None, True

    # Default based on original Islamic collection category
    if old_cat == "01 - Quran & Tafsir":
        return "01_Religion_ধর্ম/Islam_ইসলাম", "Quran_কুরআন", None, True
    if old_cat == "02 - Hadith & Sunnah":
        return "01_Religion_ধর্ম/Islam_ইসলাম", "Hadith_হাদিস", None, True
    if old_cat == "04 - Seerah, History & Biography":
        return "01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_History_ইসলামের_ইতিহাস", None, True
    if old_cat == "05 - Arabic Language & Dictionaries":
        return "16_Language_and_Linguistics_ভাষা_ও_ভাষাবিজ্ঞান", "Arabic_Language_আরবি_ভাষা", None, True
    if "ইসলামিক সাহিত্য" in old_sub or "সাইমুম" in text:
        return "01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Literature_ইসলামী_সাহিত্য", None, True
    return "01_Religion_ধর্ম/Islam_ইসলাম", "Islamic_Lifestyle_ইসলামী_জীবনব্যবস্থা", None, True


def extract_author(item: dict) -> str:
    old_cat = item["category"]
    old_sub = item["subfolder"]
    fname = item["name"]

    # 1. Author folder from Mrinal e-Library
    if old_cat == "06 - Literature & Authors (Mrinal e-Library)" and old_sub not in NON_AUTHOR_MRINAL_FOLDERS:
        return old_sub.strip()

    # 2. Dedicated Islamic author folder
    if old_sub in KNOWN_ISLAMIC_AUTHOR_FOLDERS:
        return old_sub.strip()

    # 3. Strip extension and inspect filename for " - Author", " ।। Author", " by Author"
    stem = re.sub(r"\.[A-Za-z0-9]{2,5}$", "", fname).strip()
    lower_all = f"{old_sub} {fname}".lower()
    for kw, author in AUTHOR_KEYWORDS:
        if kw in lower_all:
            return author

    # Pattern: "Title ।। Author" or "Title - Author" or "Title by Author"
    for sep in ["।।", "||", " – ", " - ", " by ", " By ", " BY ", "–", "-"]:
        if sep in stem:
            candidate = stem.split(sep)[-1].strip()
            # Clean trailing bracket/year info like [1992] or (1)
            candidate = re.sub(r"\s*[\[(][^\])\n]{1,30}[\])]\s*$", "", candidate).strip()
            if (
                3 <= len(candidate) <= 45
                and not re.search(r"^\d+$", candidate)
                and not re.search(r"^[\d\s.\-_]+$", candidate)
                and "part" not in candidate.lower()
                and "vol" not in candidate.lower()
                and "khondo" not in candidate.lower()
                and "খন্ড" not in candidate
                and "খণ্ড" not in candidate
                and "pdf" not in candidate.lower()
            ):
                # If single-hyphen split produced a very short English suffix like "1st" or "edition", skip
                if sep == "-" and len(candidate.split()) == 1 and len(candidate) < 6:
                    continue
                return candidate.replace("-", " ").strip() if "-" in candidate and not any("\u0980" <= c <= "\u09ff" for c in candidate) else candidate

    return "Various / Compiled (সংকলিত)"


def extract_publication(item: dict) -> str:
    text = f"{item['name']} {item.get('source_path', '')} {item['subfolder']} {item.get('source_collection', '')}".lower()
    for keys, pub_name in PUBLICATION_RULES:
        if any(k in text for k in keys):
            return pub_name

    # Fallback to source digital library collection
    src = item.get("source_collection", "")
    if src == "মৃণালের ই-লাইব্রেরি":
        return "মৃণালের ই-লাইব্রেরি (Mrinal e-Library Edition)"
    if src == "ইসলামীক বই ৫০০টি+":
        return "ইসলামীক ডিজিটাল লাইব্রেরি (Islamic 500+ Collection)"
    if src == "বই বিতরন (১৭/০৮/২০২২)":
        return "বই বিতরণ ডিজিটাল সংকলন (Boi Bitoron 2022)"
    return "ইসলামী ডিজিটাল আর্কাইভ (Islamic e-Book Archive)"


def gdrive_mkdir(name: str, parent_id: str) -> str:
    for attempt in range(4):
        res = subprocess.run(
            [GDRIVE, "mutate", "mkdir", name, "--parent", parent_id],
            capture_output=True, text=True, encoding="utf-8"
        )
        if res.returncode == 0:
            m = re.search(r"\(ID:\s*([A-Za-z0-9_-]+)\)", res.stdout)
            if m:
                return m.group(1)
        time.sleep(1 + attempt)
    raise RuntimeError(f"mkdir failed for {name} under {parent_id}: {res.stderr}")


def gdrive_mv(file_id: str, target_parent_id: str) -> None:
    for attempt in range(4):
        res = subprocess.run(
            [GDRIVE, "mutate", "mv", file_id, target_parent_id],
            capture_output=True, text=True, encoding="utf-8"
        )
        if res.returncode == 0:
            return
        time.sleep(1 + attempt)
    raise RuntimeError(f"mv failed for {file_id} -> {target_parent_id}: {res.stderr}")


def gdrive_trash(file_id: str) -> None:
    subprocess.run([GDRIVE, "mutate", "trash", file_id], capture_output=True, text=True, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--github-only", action="store_true")
    args = parser.parse_args()

    plan = json.loads((DATA_DIR / "copy_plan.json").read_text(encoding="utf-8"))
    fmap = json.loads((DATA_DIR / "folder_map.json").read_text(encoding="utf-8"))
    progress = json.loads((DATA_DIR / "catalog_progress.json").read_text(encoding="utf-8"))

    # Classify every book
    enriched = []
    folder_moves = {}  # old_sub_key -> (target_leaf_path, clean_sub_name)
    file_moves = []    # (new_file_id, target_leaf_path, item)

    for it in plan:
        top_path, leaf, sub_name, is_mixed = classify_book_leaf(it)
        leaf_path = f"{top_path}/{leaf}"
        author = extract_author(it)
        publication = extract_publication(it)
        new_file_id = progress[it["source_id"]]
        rec = {
            "source_id": it["source_id"],
            "file_id": new_file_id,
            "name": it["name"],
            "size": it["size"],
            "mimeType": it["mimeType"],
            "top_category": top_path.split("/")[0],
            "leaf_path": leaf_path,
            "leaf_category": leaf,
            "subfolder": sub_name,
            "author": author,
            "publication": publication,
            "link": f"https://drive.google.com/file/d/{new_file_id}/view",
        }
        enriched.append(rec)
        if is_mixed:
            file_moves.append((new_file_id, leaf_path, sub_name))
        else:
            old_key = f"{it['category']}||{it['subfolder']}"
            folder_moves[old_key] = (leaf_path, sub_name)

    if args.dry_run:
        top_counts = Counter(r["top_category"] for r in enriched)
        leaf_counts = Counter(r["leaf_path"] for r in enriched)
        author_counts = Counter(r["author"] for r in enriched)
        pub_counts = Counter(r["publication"] for r in enriched)
        print(f"Total books: {len(enriched)}")
        print(f"Folder moves: {len(folder_moves)}, Individual file moves: {len(file_moves)}")
        print("\nTop categories:")
        for tc in sorted(TAXONOMY.keys()):
            print(f"  {tc}: {top_counts[tc]}")
        print(f"\nUnique authors: {len(author_counts)}, Top 15:")
        for a, c in author_counts.most_common(15):
            print(f"  {a}: {c}")
        print(f"\nUnique publications: {len(pub_counts)}, Top 15:")
        for p, c in pub_counts.most_common(15):
            print(f"  {p}: {c}")
        unclass = sum(c for k, c in leaf_counts.items() if k.startswith("25_"))
        print(f"\nBooks in 25_Others_and_Unclassified: {unclass}")
        return

    # State file for resumable Google Drive reorganization
    state_file = DATA_DIR / "taxonomy_state.json"
    state = json.loads(state_file.read_text(encoding="utf-8")) if state_file.exists() else {
        "folders": {},       # rel_path -> folder_id
        "moved_folders": [], # old_key list
        "moved_files": [],   # new_file_id list
        "trashed": [],       # old folder IDs trashed
    }

    if not args.github_only:
        # 1. Create the full 25-category folder tree in Google Drive
        print("Step 1: Creating 25-category folder hierarchy in Google Drive...", flush=True)
        # First create 25 top-level folders
        todo_top = [tc for tc in TAXONOMY.keys() if tc not in state["folders"]]
        if todo_top:
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
                futs = {ex.submit(gdrive_mkdir, tc, ROOT_DRIVE_ID): tc for tc in todo_top}
                for f in concurrent.futures.as_completed(futs):
                    tc = futs[f]
                    state["folders"][tc] = f.result()
            state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

        # Create mid-level folders (Islam_ইসলাম, Hinduism_হিন্দুধর্ম, etc. under 01_Religion_ধর্ম)
        todo_mid = []
        for tc, sub in TAXONOMY.items():
            if isinstance(sub, dict):
                for mid in sub.keys():
                    p = f"{tc}/{mid}"
                    if p not in state["folders"]:
                        todo_mid.append((mid, state["folders"][tc], p))
        if todo_mid:
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
                futs = {ex.submit(gdrive_mkdir, name, pid): p for name, pid, p in todo_mid}
                for f in concurrent.futures.as_completed(futs):
                    state["folders"][futs[f]] = f.result()
            state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

        # Create all leaf category folders
        todo_leaf = []
        for tc, sub in TAXONOMY.items():
            if isinstance(sub, dict):
                for mid, leaves in sub.items():
                    for lf in leaves:
                        p = f"{tc}/{mid}/{lf}"
                        if p not in state["folders"]:
                            todo_leaf.append((lf, state["folders"][f"{tc}/{mid}"], p))
            else:
                for lf in sub:
                    p = f"{tc}/{lf}"
                    if p not in state["folders"]:
                        todo_leaf.append((lf, state["folders"][tc], p))
        if todo_leaf:
            print(f"Creating {len(todo_leaf)} leaf category folders in Drive...", flush=True)
            with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
                futs = {ex.submit(gdrive_mkdir, name, pid): p for name, pid, p in todo_leaf}
                done = 0
                for f in concurrent.futures.as_completed(futs):
                    state["folders"][futs[f]] = f.result()
                    done += 1
                    if done % 50 == 0:
                        print(f"  Created {done}/{len(todo_leaf)} leaf folders", flush=True)
                        state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
            state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Taxonomy folders ready in Drive: {len(state['folders'])} folders", flush=True)

        # 2. Move clean author/topic subfolders into their target leaf folders
        moved_fset = set(state["moved_folders"])
        todo_fmoves = [(k, v[0], v[1]) for k, v in folder_moves.items() if k not in moved_fset]
        if todo_fmoves:
            print(f"Moving {len(todo_fmoves)} topic/author subfolders in Drive...", flush=True)
            with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
                futs = {
                    ex.submit(gdrive_mv, fmap["subfolders"][k], state["folders"][lp]): (k, lp, sn)
                    for k, lp, sn in todo_fmoves
                }
                done = 0
                for f in concurrent.futures.as_completed(futs):
                    k, lp, sn = futs[f]
                    f.result()
                    state["folders"][f"{lp}/{sn}"] = fmap["subfolders"][k]
                    state["moved_folders"].append(k)
                    done += 1
                    if done % 50 == 0:
                        print(f"  Moved {done}/{len(todo_fmoves)} subfolders", flush=True)
                        state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
            state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        else:
            # Ensure state["folders"] records all subfolder IDs
            for k, (lp, sn) in folder_moves.items():
                if f"{lp}/{sn}" not in state["folders"] and k in fmap["subfolders"]:
                    state["folders"][f"{lp}/{sn}"] = fmap["subfolders"][k]

        # 3. Create any needed named subfolders for mixed items (e.g. হিন্দু ধর্ম গ্রন্থ)
        for _, lp, sn in file_moves:
            if sn and f"{lp}/{sn}" not in state["folders"]:
                state["folders"][f"{lp}/{sn}"] = gdrive_mkdir(sn, state["folders"][lp])
        state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

        # 4. Move individual files from mixed/generic folders into exact leaf folders
        moved_files_set = set(state["moved_files"])
        todo_files = [(fid, lp, sn) for fid, lp, sn in file_moves if fid not in moved_files_set]
        if todo_files:
            print(f"Moving {len(todo_files)} individual books from mixed folders into exact leaf categories...", flush=True)
            with concurrent.futures.ThreadPoolExecutor(max_workers=14) as ex:
                futs = {}
                for fid, lp, sn in todo_files:
                    dest_path = f"{lp}/{sn}" if sn else lp
                    futs[ex.submit(gdrive_mv, fid, state["folders"][dest_path])] = fid
                done = 0
                for f in concurrent.futures.as_completed(futs):
                    fid = futs[f]
                    f.result()
                    state["moved_files"].append(fid)
                    done += 1
                    if done % 100 == 0:
                        print(f"  Moved {done}/{len(todo_files)} individual books", flush=True)
                        state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
            state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

        # 5. Trash the old 7 top-level folders (and emptied generic subfolders)
        trashed_set = set(state["trashed"])
        old_ids_to_trash = list(fmap["categories"].values())
        for old_key in MIXED_SUBFOLDERS:
            k_str = f"{old_key[0]}||{old_key[1]}"
            if k_str in fmap["subfolders"]:
                old_ids_to_trash.append(fmap["subfolders"][k_str])
        todo_trash = [oid for oid in old_ids_to_trash if oid not in trashed_set]
        if todo_trash:
            print(f"Trashing {len(todo_trash)} old empty category/generic folders...", flush=True)
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
                list(ex.map(gdrive_trash, todo_trash))
            state["trashed"].extend(todo_trash)
            state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    # Save enriched books.json
    (REPO_DIR / "books.json").write_text(
        json.dumps(enriched, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )

    # Generate GitHub directory hierarchy & README.md in EVERY folder!
    print("Generating GitHub directory hierarchy, per-folder README.md, AUTHORS.md, and PUBLICATIONS.md...", flush=True)
    # Remove old generated folders safely
    old_cats_dir = REPO_DIR / "categories"
    if old_cats_dir.exists():
        shutil.rmtree(old_cats_dir)
    for tc in TAXONOMY.keys():
        p = REPO_DIR / safe_fs_name(tc)
        if p.exists():
            shutil.rmtree(p)
    for extra_dir in ["Authors_লেখক", "Publications_প্রকাশনী"]:
        p = REPO_DIR / extra_dir
        if p.exists():
            shutil.rmtree(p)

    # Index books by path
    by_top = defaultdict(list)
    by_mid = defaultdict(list)
    by_leaf = defaultdict(list)
    by_sub = defaultdict(list)
    by_author = defaultdict(list)
    by_pub = defaultdict(list)

    for b in enriched:
        by_top[b["top_category"]].append(b)
        parts = b["leaf_path"].split("/")
        if len(parts) == 3:
            by_mid[f"{parts[0]}/{parts[1]}"].append(b)
        by_leaf[b["leaf_path"]].append(b)
        if b["subfolder"]:
            by_sub[f"{b['leaf_path']}/{b['subfolder']}"].append(b)
        by_author[b["author"]].append(b)
        by_pub[b["publication"]].append(b)

    def folder_url(drive_path: str) -> str:
        fid = state["folders"].get(drive_path, ROOT_DRIVE_ID)
        return f"https://drive.google.com/drive/folders/{fid}"

    def rel_link(*segments: str) -> str:
        return "./" + "/".join(quote(safe_fs_name(s)) for s in segments) + "/README.md"

    def write_book_table(lines: list[str], books: list[dict]) -> None:
        lines.append(f"## 📖 Books ({len(books):,})")
        lines.append("")
        if not books:
            lines.append("_No books placed directly in this section yet — see subfolders above or contribute via PR._")
            lines.append("")
            return
        lines.append("| # | Book Title | Author | Publication / Series | Size | Google Drive Link |")
        lines.append("|---:|---|---|---|---:|---|")
        for idx, b in enumerate(sorted(books, key=lambda x: x["name"]), 1):
            lines.append(
                f"| {idx} | {md_escape(b['name'])} | {md_escape(b['author'])} | {md_escape(b['publication'])} | {fmt_size(b['size'])} | [Open in Drive]({b['link']}) |"
            )
        lines.append("")

    # Generate folders & README.md for every node in TAXONOMY
    for tc, sub in TAXONOMY.items():
        tc_fs = REPO_DIR / safe_fs_name(tc)
        tc_fs.mkdir(parents=True, exist_ok=True)
        tc_books = by_top[tc]
        tc_lines = [
            f"# 📂 {tc}",
            "",
            f"[⬅️ Back to Library Home](../README.md) | [📁 Open Folder in Google Drive]({folder_url(tc)})",
            "",
            f"**Total Books:** {len(tc_books):,} | **Total Size:** {fmt_size(sum(b['size'] for b in tc_books))}",
            "",
            "## 🗂️ Subcategories",
            "",
            "| Subcategory | Books | GitHub Index | Google Drive Folder |",
            "|---|---:|---|---|",
        ]

        if isinstance(sub, dict):
            for mid, leaves in sub.items():
                mid_path = f"{tc}/{mid}"
                mid_books = by_mid[mid_path] if leaves else by_leaf[mid_path]
                tc_lines.append(
                    f"| **{mid}** | {len(mid_books):,} | [Browse]({rel_link(mid)}) | [Open in Drive]({folder_url(mid_path)}) |"
                )

                mid_fs = tc_fs / safe_fs_name(mid)
                mid_fs.mkdir(parents=True, exist_ok=True)
                mid_lines = [
                    f"# 📂 {mid}",
                    "",
                    f"[⬅️ Back to Home](../../README.md) / [{tc}](../README.md) | [📁 Open Folder in Google Drive]({folder_url(mid_path)})",
                    "",
                    f"**Total Books:** {len(mid_books):,} | **Total Size:** {fmt_size(sum(b['size'] for b in mid_books))}",
                    "",
                ]

                if leaves:
                    mid_lines.extend([
                        "## 🗂️ Categories",
                        "",
                        "| Category | Books | GitHub Index | Google Drive Folder |",
                        "|---|---:|---|---|",
                    ])
                    for lf in leaves:
                        lf_path = f"{mid_path}/{lf}"
                        lf_books = by_leaf[lf_path]
                        mid_lines.append(
                            f"| **{lf}** | {len(lf_books):,} | [Browse]({rel_link(lf)}) | [Open in Drive]({folder_url(lf_path)}) |"
                        )
                        _write_leaf_and_subfolders(
                            mid_fs, lf, lf_path, lf_books, by_sub, folder_url, rel_link, write_book_table, depth_back="../../.."
                        )
                    mid_lines.append("")
                else:
                    # Direct leaf under Religion (e.g. Hinduism, Comparative_Religion)
                    _write_leaf_subfolders_into(
                        mid_fs, mid_path, mid_books, by_sub, folder_url, rel_link, write_book_table, mid_lines, depth_back="../.."
                    )

                (mid_fs / "README.md").write_text("\n".join(mid_lines), encoding="utf-8")
        else:
            for lf in sub:
                lf_path = f"{tc}/{lf}"
                lf_books = by_leaf[lf_path]
                tc_lines.append(
                    f"| **{lf}** | {len(lf_books):,} | [Browse]({rel_link(lf)}) | [Open in Drive]({folder_url(lf_path)}) |"
                )
                _write_leaf_and_subfolders(
                    tc_fs, lf, lf_path, lf_books, by_sub, folder_url, rel_link, write_book_table, depth_back="../.."
                )

        tc_lines.append("")
        write_book_table(tc_lines, tc_books)
        (tc_fs / "README.md").write_text("\n".join(tc_lines), encoding="utf-8")

    # Generate AUTHORS.md & Authors_লেখক/README.md
    author_lines = [
        "# ✍️ Find Books by Author (লেখক অনুযায়ী বই খুঁজুন)",
        "",
        f"[⬅️ Back to Library Home](README.md) | [📁 Google Drive Root]({folder_url(ROOT_DRIVE_ID)})",
        "",
        f"**Total Authors / Compilers:** {len(by_author):,} | **Total Books:** {len(enriched):,}",
        "",
        "## Quick Author Index",
        "",
        "| Author | Books |",
        "|---|---:|",
    ]
    sorted_authors = sorted(by_author.keys(), key=lambda a: (-len(by_author[a]), a))
    for a in sorted_authors:
        anchor = re.sub(r"[^\w\u0980-\u09FF-]+", "-", a.lower()).strip("-")
        author_lines.append(f"| [{md_escape(a)}](#{anchor}) | {len(by_author[a]):,} |")
    author_lines.append("")
    for a in sorted_authors:
        books = sorted(by_author[a], key=lambda x: x["name"])
        author_lines.extend([
            f"### {md_escape(a)} ({len(books):,})",
            "",
            "| # | Book Title | Category | Publication | Size | Drive Link |",
            "|---:|---|---|---|---:|---|",
        ])
        for idx, b in enumerate(books, 1):
            author_lines.append(
                f"| {idx} | {md_escape(b['name'])} | {md_escape(b['leaf_category'])} | {md_escape(b['publication'])} | {fmt_size(b['size'])} | [Open in Drive]({b['link']}) |"
            )
        author_lines.append("")
    (REPO_DIR / "AUTHORS.md").write_text("\n".join(author_lines), encoding="utf-8")

    # Generate PUBLICATIONS.md
    pub_lines = [
        "# 🏢 Find Books by Publication / Series (প্রকাশনী অনুযায়ী বই খুঁজুন)",
        "",
        f"[⬅️ Back to Library Home](README.md) | [📁 Google Drive Root]({folder_url(ROOT_DRIVE_ID)})",
        "",
        f"**Total Publications / Series:** {len(by_pub):,} | **Total Books:** {len(enriched):,}",
        "",
        "## Publications Summary",
        "",
        "| Publication / Series | Books |",
        "|---|---:|",
    ]
    sorted_pubs = sorted(by_pub.keys(), key=lambda p: (-len(by_pub[p]), p))
    for p in sorted_pubs:
        anchor = re.sub(r"[^\w\u0980-\u09FF-]+", "-", p.lower()).strip("-")
        pub_lines.append(f"| [{md_escape(p)}](#{anchor}) | {len(by_pub[p]):,} |")
    pub_lines.append("")
    for p in sorted_pubs:
        books = sorted(by_pub[p], key=lambda x: x["name"])
        pub_lines.extend([
            f"### {md_escape(p)} ({len(books):,})",
            "",
            "| # | Book Title | Author | Category | Size | Drive Link |",
            "|---:|---|---|---|---:|---|",
        ])
        for idx, b in enumerate(books, 1):
            pub_lines.append(
                f"| {idx} | {md_escape(b['name'])} | {md_escape(b['author'])} | {md_escape(b['leaf_category'])} | {fmt_size(b['size'])} | [Open in Drive]({b['link']}) |"
            )
        pub_lines.append("")
    (REPO_DIR / "PUBLICATIONS.md").write_text("\n".join(pub_lines), encoding="utf-8")

    # Generate Root README.md
    total_size = sum(b["size"] for b in enriched)
    root_lines = [
        "# 📚 Bangladesh's Biggest E-Book Library (`bangladesh biggest e book library`)",
        "",
        "বাংলাদেশের বৃহত্তম ই-বুক লাইব্রেরি — A complete, categorized bilingual digital library of **6,364+ e-books** organized across **25 subject categories**, **every folder documented with its own `README.md`**, and full search by **Category**, **Author**, and **Publication**.",
        "",
        f"- 📁 **Google Drive Root Folder (`bangladesh biggest e book library`):** [Open in Google Drive](https://drive.google.com/drive/folders/{ROOT_DRIVE_ID})",
        f"- 🌐 **Interactive Searchable Web Library:** https://salman-anik.github.io/bangladesh-biggest-ebook-library/",
        f"- ✍️ **Browse by Author ({len(by_author):,} authors):** [AUTHORS.md](AUTHORS.md)",
        f"- 🏢 **Browse by Publication ({len(by_pub):,} publications):** [PUBLICATIONS.md](PUBLICATIONS.md)",
        f"- 📖 **Total Books:** {len(enriched):,} ({fmt_size(total_size)})",
        "",
        "## 🗂️ Categories (All 25 Sections)",
        "",
        "| # | Category Folder | Books | GitHub Folder Index | Google Drive Folder |",
        "|---:|---|---:|---|---|",
    ]
    for idx, tc in enumerate(TAXONOMY.keys(), 1):
        cnt = len(by_top[tc])
        root_lines.append(
            f"| {idx} | **{tc}** | {cnt:,} | [Browse {tc}]({rel_link(tc)}) | [Open in Drive]({folder_url(tc)}) |"
        )
    root_lines.extend([
        "",
        "## 🕌 Featured: Religion → Islam (`01_Religion_ধর্ম/Islam_ইসলাম`)",
        "",
        f"[📁 Open Islam Folder in Google Drive]({folder_url('01_Religion_ধর্ম/Islam_ইসলাম')}) | [📖 View Full Islam Index](01_Religion_%E0%A6%A7%E0%A6%B0%E0%A7%8D%E0%A6%AE/Islam_%E0%A6%87%E0%A6%B8%E0%A6%B2%E0%A6%BE%E0%A6%AE/README.md)",
        "",
        "| Subcategory | Books | GitHub Folder | Google Drive Folder |",
        "|---|---:|---|---|",
    ])
    for lf in TAXONOMY["01_Religion_ধর্ম"]["Islam_ইসলাম"]:
        lp = f"01_Religion_ধর্ম/Islam_ইসলাম/{lf}"
        gh_p = f"./{quote('01_Religion_ধর্ম')}/{quote('Islam_ইসলাম')}/{quote(lf)}/README.md"
        root_lines.append(
            f"| **{lf}** | {len(by_leaf[lp]):,} | [Browse]({gh_p}) | [Open in Drive]({folder_url(lp)}) |"
        )
    root_lines.append("")
    (REPO_DIR / "README.md").write_text("\n".join(root_lines), encoding="utf-8")
    print("All README.md, AUTHORS.md, PUBLICATIONS.md, and books.json generated cleanly!", flush=True)


def _write_leaf_subfolders_into(parent_fs, leaf_path, leaf_books, by_sub, folder_url, rel_link, write_book_table, lines, depth_back):
    sub_names = sorted(set(b["subfolder"] for b in leaf_books if b["subfolder"]))
    if sub_names:
        lines.extend([
            "## 📁 Author / Topic Subfolders",
            "",
            "| Subfolder | Books | GitHub Folder | Google Drive Folder |",
            "|---|---:|---|---|",
        ])
        for sn in sub_names:
            sp = f"{leaf_path}/{sn}"
            sbooks = by_sub[sp]
            lines.append(
                f"| **{md_escape(sn)}** | {len(sbooks):,} | [Browse]({rel_link(sn)}) | [Open in Drive]({folder_url(sp)}) |"
            )
            sub_fs = parent_fs / safe_fs_name(sn)
            sub_fs.mkdir(parents=True, exist_ok=True)
            s_lines = [
                f"# 📁 {sn}",
                "",
                f"[⬅️ Back to Home]({depth_back}/../README.md) / [Parent](../README.md) | [📁 Open Folder in Google Drive]({folder_url(sp)})",
                "",
                f"**Total Books:** {len(sbooks):,} | **Total Size:** {fmt_size(sum(b['size'] for b in sbooks))}",
                "",
            ]
            write_book_table(s_lines, sbooks)
            (sub_fs / "README.md").write_text("\n".join(s_lines), encoding="utf-8")
        lines.append("")
    write_book_table(lines, leaf_books)


def _write_leaf_and_subfolders(parent_fs, lf, lf_path, lf_books, by_sub, folder_url, rel_link, write_book_table, depth_back):
    lf_fs = parent_fs / safe_fs_name(lf)
    lf_fs.mkdir(parents=True, exist_ok=True)
    lf_lines = [
        f"# 📂 {lf}",
        "",
        f"[⬅️ Back to Home]({depth_back}/README.md) / [Parent](../README.md) | [📁 Open Folder in Google Drive]({folder_url(lf_path)})",
        "",
        f"**Total Books:** {len(lf_books):,} | **Total Size:** {fmt_size(sum(b['size'] for b in lf_books))}",
        "",
    ]
    _write_leaf_subfolders_into(
        lf_fs, lf_path, lf_books, by_sub, folder_url, rel_link, write_book_table, lf_lines, depth_back
    )
    (lf_fs / "README.md").write_text("\n".join(lf_lines), encoding="utf-8")


if __name__ == "__main__":
    main()
