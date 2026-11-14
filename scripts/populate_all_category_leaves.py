import concurrent.futures
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_DIR / "scripts"))

import build_25cat_library as b25  # noqa: E402
import collect_and_ingest_books as cab  # noqa: E402

SKIP_LEAVES = {
    "25_Others_and_Unclassified_অন্যান্য/Unclassified",
    "25_Others_and_Unclassified_অন্যান্য/To_Be_Organized",
}

SPARSE_TOP_CATEGORIES = {
    "10_Psychology_and_Mind_মনোবিজ্ঞান_ও_মানসিকতা",
    "17_Biography_and_Autobiography_জীবনী_ও_আত্মজীবনী",
    "21_Travel_and_Geography_ভ্রমণ_ও_ভূগোল",
    "23_Reference_Books_তথ্যসূত্র",
    "25_Others_and_Unclassified_অন্যান্য",
}

# Explicit Archive.org search query overrides for tricky, bilingual, or Bangladesh-specific leaves
LEAF_QUERY_OVERRIDES = {
    "01_Religion_ধর্ম/Comparative_Religion": '(title:"comparative religion" OR subject:"religions" OR subject:"comparative religion")',
    "01_Religion_ধর্ম/Christianity_খ্রিস্টধর্ম": '(title:"Christianity" OR subject:"Christianity" OR subject:"Bible")',
    "01_Religion_ধর্ম/Buddhism_বৌদ্ধধর্ম": '(title:"Buddhism" OR subject:"Buddhism" OR subject:"Buddhist")',
    "02_Literature_সাহিত্য/Children's_Literature_শিশুসাহিত্য": '(subject:"children\'s literature" OR subject:"juvenile fiction" OR title:"fairy tales")',
    "02_Literature_সাহিত্য/Letters_পত্রসাহিত্য": '(subject:"letters" AND (subject:"literature" OR title:"letters"))',
    "02_Literature_সাহিত্য/Prose_গদ্য": '(subject:"essays" OR title:"prose" OR subject:"English prose")',
    "02_Literature_সাহিত্য/Rhymes_ছড়া": '(title:"nursery rhymes" OR subject:"nursery rhymes" OR title:"rhymes")',
    "02_Literature_সাহিত্য/Autobiography_আত্মজীবনী": '(subject:"autobiography" OR title:"autobiography")',
    "02_Literature_সাহিত্য/Memoirs_স্মৃতিকথা": '(title:"memoirs" OR subject:"memoirs")',
    "03_Fiction_কল্পকাহিনী/Dystopian_ডিস্টোপিয়ান": '(subject:"dystopias" OR subject:"utopias" OR title:"dystopia")',
    "03_Fiction_কল্পকাহিনী/Ghost_Stories_ভূতের_গল্প": '(title:"ghost stories" OR subject:"ghost stories")',
    "03_Fiction_কল্পকাহিনী/Historical_Fiction_ঐতিহাসিক_কল্পকাহিনী": '(subject:"historical fiction")',
    "03_Fiction_কল্পকাহিনী/Psychological_Fiction_মনস্তাত্ত্বিক": '(subject:"psychological fiction")',
    "03_Fiction_কল্পকাহিনী/Political_Fiction_রাজনৈতিক_কল্পকাহিনী": '(subject:"political fiction")',
    "03_Fiction_কল্পকাহিনী/War_Fiction_যুদ্ধভিত্তিক": '(subject:"war stories" OR subject:"war fiction")',
    "03_Fiction_কল্পকাহিনী/Social_Fiction_সামাজিক": '(subject:"social fiction" OR subject:"domestic fiction")',
    "05_Computer_and_Technology_কম্পিউটার_ও_প্রযুক্তি/Artificial_Intelligence_AI_কৃত্রিম_বুদ্ধিমত্তা": '(title:"artificial intelligence" OR subject:"artificial intelligence")',
    "05_Computer_and_Technology_কম্পিউটার_ও_প্রযুক্তি/Data_Analytics_ডেটা_অ্যানালিটিক্স": '(title:"data analysis" OR title:"data analytics" OR subject:"data mining")',
    "05_Computer_and_Technology_কম্পিউটার_ও_প্রযুক্তি/Emerging_Technology_নতুন_প্রযুক্তি": '(title:"quantum computing" OR title:"nanotechnology" OR title:"blockchain" OR title:"internet of things")',
    "05_Computer_and_Technology_কম্পিউটার_ও_প্রযুক্তি/Web_Development_ওয়েব_ডেভেলপমেন্ট": '(title:"HTML" OR title:"web development" OR title:"JavaScript" OR title:"CSS")',
    "05_Computer_and_Technology_কম্পিউটার_ও_প্রযুক্তি/Networking_নেটওয়ার্কিং": '(title:"computer networks" OR title:"TCP/IP" OR subject:"computer networks")',
    "05_Computer_and_Technology_কম্পিউটার_ও_প্রযুক্তি/Database_ডেটাবেজ": '(title:"database" OR title:"SQL" OR subject:"database management")',
    "06_History_ইতিহাস/British_Period_ব্রিটিশ_শাসন": '((title:"British India" OR subject:"British India" OR title:"East India Company") OR (title:"Bengal" AND title:"British"))',
    "06_History_ইতিহাস/Mughal_Period_মুঘল_যুগ": '(title:"Mughal" OR subject:"Mughal Empire" OR title:"Akbar")',
    "06_History_ইতিহাস/Historical_Documents_ঐতিহাসিক_দলিল": '(title:"historical documents" OR subject:"archives" OR title:"constitutions" OR title:"charters")',
    "11_Business_and_Finance_ব্যবসা_ও_অর্থায়ন/Islamic_Finance_ইসলামী_ফাইন্যান্স": '(title:"Islamic finance" OR title:"Islamic banking" OR title:"Islamic economics")',
    "12_Law_and_Legal_আইন_ও_বিচার/Bangladesh_Law_বাংলাদেশের_আইন": '((title:"Bangladesh" OR title:"Bengal") AND (title:"law" OR title:"act" OR title:"constitution" OR subject:"law"))',
    "12_Law_and_Legal_আইন_ও_বিচার/Islamic_Law_ইসলামী_আইন": '(title:"Islamic law" OR subject:"Islamic law" OR (subject:"jurisprudence" AND title:"Islam"))',
    "15_Education_and_Academics_শিক্ষা_ও_একাডেমিক/University": '(title:"university" AND (title:"syllabus" OR title:"lectures" OR title:"handbook"))',
    "15_Education_and_Academics_শিক্ষা_ও_একাডেমিক/Admission_Preparation": '(title:"entrance examination" OR title:"admission test" OR ((title:"GRE" OR title:"SAT") AND title:"preparation"))',
    "15_Education_and_Academics_শিক্ষা_ও_একাডেমিক/Research_Methodology": '(title:"research methodology" OR title:"research methods" OR subject:"research methodology")',
    "15_Education_and_Academics_শিক্ষা_ও_একাডেমিক/Thesis_and_Dissertation": '((title:"thesis" OR title:"dissertation") AND title:"writing")',
    "15_Education_and_Academics_শিক্ষা_ও_একাডেমিক/Question_Banks": '(title:"question bank" OR title:"examination questions" OR title:"sample questions")',
    "15_Education_and_Academics_শিক্ষা_ও_একাডেমিক/Competitive_Exams": '((title:"civil service" AND title:"examination") OR title:"competitive examination")',
    "17_Biography_and_Autobiography_জীবনী_ও_আত্মজীবনী/Bangladeshi_Personalities": '((title:"Bangladesh" OR title:"Bengal") AND (subject:"biography" OR title:"biography" OR title:"Tagore" OR title:"Mujib"))',
    "17_Biography_and_Autobiography_জীবনী_ও_আত্মজীবনী/World_Leaders": '((subject:"statesmen" AND subject:"biography") OR (title:"Lincoln" AND subject:"biography"))',
    "17_Biography_and_Autobiography_জীবনী_ও_আত্মজীবনী/Scientists": '((subject:"scientists" AND subject:"biography") OR (title:"Newton" AND subject:"biography"))',
    "17_Biography_and_Autobiography_জীবনী_ও_আত্মজীবনী/Writers_and_Poets": '((subject:"authors" AND subject:"biography") OR (subject:"poets" AND subject:"biography"))',
    "17_Biography_and_Autobiography_জীবনী_ও_আত্মজীবনী/Entrepreneurs": '(subject:"businesspeople" OR (title:"entrepreneur" AND subject:"biography"))',
    "17_Biography_and_Autobiography_জীবনী_ও_আত্মজীবনী/Historical_Personalities": '(subject:"biography" AND subject:"history")',
    "18_Self_Development_আত্মউন্নয়ন/Productivity_কর্মদক্ষতা": '(title:"productivity" OR (title:"efficiency" AND subject:"success"))',
    "18_Self_Development_আত্মউন্নয়ন/Habits_অভ্যাস": '(title:"habits" OR subject:"habit")',
    "18_Self_Development_আত্মউন্নয়ন/Career_Development_ক্যারিয়ার": '(title:"career" AND (title:"guide" OR title:"development" OR subject:"vocational guidance"))',
    "18_Self_Development_আত্মউন্নয়ন/Emotional_Intelligence": '(title:"emotional intelligence" OR title:"self-control")',
    "18_Self_Development_আত্মউন্নয়ন/Mental_Development": '(title:"mind" OR title:"self-improvement" OR title:"concentration")',
    "19_Arts_and_Culture_শিল্প_ও_সংস্কৃতি/Calligraphy_ক্যালিগ্রাফি": '(title:"calligraphy" OR subject:"calligraphy" OR title:"lettering")',
    "19_Arts_and_Culture_শিল্প_ও_সংস্কৃতি/Handicrafts_হস্তশিল্প": '(title:"handicrafts" OR subject:"handicraft" OR title:"crafts")',
    "21_Travel_and_Geography_ভ্রমণ_ও_ভূগোল/Bangladesh_বাংলাদেশ": '(title:"Bangladesh" AND (title:"geography" OR title:"travel" OR subject:"Bangladesh"))',
    "21_Travel_and_Geography_ভ্রমণ_ও_ভূগোল/Travel_Guides_ভ্রমণ_গাইড": '(title:"travel guide" OR subject:"guidebooks")',
    "21_Travel_and_Geography_ভ্রমণ_ও_ভূগোল/Travel_Memoirs_ভ্রমণ_স্মৃতিকথা": '(subject:"description and travel" OR subject:"voyages and travels")',
    "21_Travel_and_Geography_ভ্রমণ_ও_ভূগোল/Maps_and_Atlases_মানচিত্র": '(title:"atlas" OR subject:"atlases" OR subject:"cartography")',
    "22_Children_and_Young_Adult_শিশু_ও_কিশোর/Picture_Books": '(subject:"picture books for children" OR title:"picture book")',
    "22_Children_and_Young_Adult_শিশু_ও_কিশোর/Moral_Stories": '(title:"moral stories" OR title:"fables" OR subject:"fables")',
    "22_Children_and_Young_Adult_শিশু_ও_কিশোর/Educational_Books": '((title:"elementary" AND (title:"reader" OR title:"lessons")) AND subject:"children")',
    "22_Children_and_Young_Adult_শিশু_ও_কিশোর/Science_for_Kids": '(title:"science for kids" OR (title:"science" AND subject:"juvenile literature"))',
    "22_Children_and_Young_Adult_শিশু_ও_কিশোর/Teen_Fiction": '(subject:"young adult fiction")',
    "22_Children_and_Young_Adult_শিশু_ও_কিশোর/Teen_Nonfiction": '(subject:"young adult nonfiction" OR subject:"juvenile literature")',
    "23_Reference_Books_তথ্যসূত্র/General_Knowledge_সাধারণ_জ্ঞান": '(title:"general knowledge" OR title:"world almanac" OR title:"facts")',
    "24_Magazines_and_Periodicals_সাময়িকী/Literary_Magazines": '(title:"literary magazine" OR (subject:"literature" AND subject:"periodicals"))',
    "24_Magazines_and_Periodicals_সাময়িকী/Science_Magazines": '(title:"popular science" OR (subject:"science" AND subject:"periodicals"))',
    "24_Magazines_and_Periodicals_সাময়িকী/Religious_Magazines": '((subject:"religion" AND subject:"periodicals") OR (title:"islamic" AND subject:"periodicals"))',
    "24_Magazines_and_Periodicals_সাময়িকী/Children's_Magazines": '(subject:"children\'s periodicals" OR (title:"St. Nicholas" AND subject:"periodicals"))',
    "24_Magazines_and_Periodicals_সাময়িকী/Newspapers": '(subject:"newspapers" OR title:"gazette")',
    "24_Magazines_and_Periodicals_সাময়িকী/Journals": '(title:"journal" AND subject:"periodicals")',
    "24_Magazines_and_Periodicals_সাময়িকী/Newsletters": '(title:"newsletter" AND subject:"periodicals")',
    "25_Others_and_Unclassified_অন্যান্য/Rare_Books": '(subject:"rare books" OR (language:ben AND title:"Bengal"))',
    "25_Others_and_Unclassified_অন্যান্য/Historical_Manuscripts": '(subject:"manuscripts" OR title:"manuscripts")',
}


def target_for_leaf(lp: str) -> int:
    tc = lp.split("/")[0]
    return 2 if tc in SPARSE_TOP_CATEGORIES else 1


def get_classified_leaves() -> list[str]:
    leaves = []

    def walk(node, prefix=""):
        if isinstance(node, list):
            for x in node:
                lp = f"{prefix}/{x}"
                if lp not in SKIP_LEAVES:
                    leaves.append(lp)
        elif isinstance(node, dict):
            for k, v in node.items():
                walk(v, f"{prefix}/{k}" if prefix else k)

    walk(b25.TAXONOMY)
    return leaves


def extract_english_topic(leaf_path: str) -> str:
    leaf = leaf_path.split("/")[-1]
    eng = re.sub(r"[\u0980-\u09FF]+", "", leaf)
    eng = eng.replace("_", " ")
    eng = re.sub(r"\s+", " ", eng).strip()
    return eng


def build_queries_for_leaf(leaf_path: str) -> list[str]:
    eng = extract_english_topic(leaf_path)
    top_eng = extract_english_topic(re.sub(r"^\d+_", "", leaf_path.split("/")[0]))
    if leaf_path in LEAF_QUERY_OVERRIDES:
        primary = LEAF_QUERY_OVERRIDES[leaf_path]
        fallback = f'({eng})' if eng else primary
        broad = f'({top_eng})' if top_eng else fallback
        return [primary, fallback, broad]

    q_phrase = f'(title:"{eng}" OR subject:"{eng}")'
    words = [w for w in re.split(r"\s+", eng) if w.lower() not in {"and", "the", "of", "for", "ai"} and len(w) > 2]
    q_words = " AND ".join(f'"{w}"' for w in words[:3]) if words else f'"{eng}"'
    top_words = [w for w in re.split(r"\s+", top_eng) if w.lower() not in {"and", "the", "of"} and len(w) > 2]
    q_top = f'(({q_words}) OR ("{top_words[0]}" AND "{words[0]}"))' if (words and top_words) else q_words
    return [q_phrase, f'({q_words})', q_top]


def refine_extra_leaf(rec: dict) -> str:
    """Re-classify extra_books.json records into narrower leaves when keywords clearly match."""
    name = (rec.get("name") or "").lower()
    lp = rec.get("leaf_path") or ""

    if lp in SKIP_LEAVES:
        return "25_Others_and_Unclassified_অন্যান্য/Rare_Books"

    # Engineering refinements
    if lp.startswith("14_Engineering_প্রকৌশল/"):
        if any(k in name for k in ["textile", "garment", "fabric", "spinning", "weaving", "বস্ত্র", "টেক্সটাইল"]):
            return "14_Engineering_প্রকৌশল/Textile_Engineering"
        if any(k in name for k in ["chemical engineering", "process control", "mass transfer", "কেমিক্যাল"]):
            return "14_Engineering_প্রকৌশল/Chemical_Engineering"
        if any(k in name for k in ["architecture", "building design", "স্থাপত্য"]):
            return "14_Engineering_প্রকৌশল/Architecture"
        if any(k in name for k in ["telecom", "wireless", "antenna", "communication system", "signal", "টেলিকমিউনিকেশন"]):
            return "14_Engineering_প্রকৌশল/Telecommunications"
        if any(k in name for k in ["agricultural engineering", "irrigation", "farm machinery", "কৃষি যন্ত্র"]):
            return "14_Engineering_প্রকৌশল/Agricultural_Engineering"
        if any(k in name for k in ["electronic", "semiconductor", "microcontroller", "vlsi", "digital logic", "sedra", "boylestad", "malvino", "op-amp", "ইলেকট্রনিক্স"]):
            return "14_Engineering_প্রকৌশল/Electronics"
        if any(k in name for k in ["mechanical", "fluid", "machine", "welding", "refrigeration", "automobile", "মেকানিক্যাল", "অটোমোবাইল", "ওয়েল্ডিং", "রেফ্রিজারেশন", "মেশিন"]):
            return "14_Engineering_প্রকৌশল/Mechanical_Engineering"
        if any(k in name for k in ["civil", "structural", "concrete", "surveying", "geotech", "সিভিল", "সার্ভেয়িং", "ড্রাফটিং"]):
            return "14_Engineering_প্রকৌশল/Civil_Engineering"

    # CS refinements
    if lp.startswith("05_Computer_and_Technology_কম্পিউটার_ও_প্রযুক্তি/"):
        if any(k in name for k in ["machine learning", "deep learning", "neural network"]):
            return "05_Computer_and_Technology_কম্পিউটার_ও_প্রযুক্তি/Machine_Learning_মেশিন_লার্নিং"
        if any(k in name for k in ["artificial intelligence", "ai ", "chatgpt", "কৃত্রিম বুদ্ধিমত্তা"]):
            return "05_Computer_and_Technology_কম্পিউটার_ও_প্রযুক্তি/Artificial_Intelligence_AI_কৃত্রিম_বুদ্ধিমত্তা"
        if any(k in name for k in ["cybersecurity", "security", "hacking", "cryptography", "হ্যাকিং", "সাইবার"]):
            return "05_Computer_and_Technology_কম্পিউটার_ও_প্রযুক্তি/Cybersecurity_সাইবার_নিরাপত্তা"
        if any(k in name for k in ["web", "html", "css", "javascript", "react", "php", "ওয়েব"]):
            return "05_Computer_and_Technology_কম্পিউটার_ও_প্রযুক্তি/Web_Development_ওয়েব_ডেভেলপমেন্ট"
        if any(k in name for k in ["database", "sql", "mongodb", "ডাটাবেজ"]):
            return "05_Computer_and_Technology_কম্পিউটার_ও_প্রযুক্তি/Database_ডেটাবেজ"
        if any(k in name for k in ["network", "tcp", "routing", "ccna", "নেটওয়ার্ক"]):
            return "05_Computer_and_Technology_কম্পিউটার_ও_প্রযুক্তি/Networking_নেটওয়ার্কিং"
        if any(k in name for k in ["python", "java", "c++", "c#", "programming", "প্রোগ্রামিং", "কোডিং"]):
            return "05_Computer_and_Technology_কম্পিউটার_ও_প্রযুক্তি/Programming_প্রোগ্রামিং"
        if any(k in name for k in ["software engineering", "design pattern", "agile", "সফটওয়্যার"]):
            return "05_Computer_and_Technology_কম্পিউটার_ও_প্রযুক্তি/Software_Engineering_সফটওয়্যার_ইঞ্জিনিয়ারিং"
        if any(k in name for k in ["data science", "pandas", "statistics", "ডেটা সায়েন্স"]):
            return "05_Computer_and_Technology_কম্পিউটার_ও_প্রযুক্তি/Data_Science_ডেটা_সায়েন্স"

    # Business refinements
    if lp.startswith("11_Business_and_Finance_ব্যবসা_ও_অর্থায়ন/"):
        if any(k in name for k in ["marketing", "বিপণন", "মার্কেটিং"]):
            return "11_Business_and_Finance_ব্যবসা_ও_অর্থায়ন/Marketing_মার্কেটিং"
        if any(k in name for k in ["bank", "ব্যাংকিং"]):
            return "11_Business_and_Finance_ব্যবসা_ও_অর্থায়ন/Banking_ব্যাংকিং"
        if any(k in name for k in ["invest", "বিনিয়োগ"]):
            return "11_Business_and_Finance_ব্যবসা_ও_অর্থায়ন/Investment_বিনিয়োগ"
        if any(k in name for k in ["stock", "share", "শেয়ার"]):
            return "11_Business_and_Finance_ব্যবসা_ও_অর্থায়ন/Stock_Market_শেয়ার_বাজার"
        if any(k in name for k in ["insurance", "বীমা"]):
            return "11_Business_and_Finance_ব্যবসা_ও_অর্থায়ন/Insurance_বীমা"
        if any(k in name for k in ["islamic", "ইসলামী অর্থনীতি", "ইসলামী ব্যাংকিং"]):
            return "11_Business_and_Finance_ব্যবসা_ও_অর্থায়ন/Islamic_Finance_ইসলামী_ফাইন্যান্স"

    # Subject textbooks in NCTB or general collections that fit empty leaves cleanly
    if "রসায়ন" in name or "রসায়ন" in name or "chemistry" in name:
        return "04_Science_বিজ্ঞান/Chemistry_রসায়ন"
    if "পরিবেশ" in name or "environmental" in name:
        return "04_Science_বিজ্ঞান/Environmental_Science_পরিবেশবিজ্ঞান"
    if "জ্যোতির্বিজ্ঞান" in name or "astronomy" in name:
        return "04_Science_বিজ্ঞান/Astronomy_জ্যোতির্বিজ্ঞান"
    if "ভূতত্ত্ব" in name or "geology" in name:
        return "04_Science_বিজ্ঞান/Geology_ভূতত্ত্ব"
    if "ইংরেজি" in name or "english" in name:
        if "grammar" in name or "ব্যাকরণ" in name:
            return "16_Language_and_Linguistics_ভাষা_ও_ভাষাবিজ্ঞান/Grammar_ব্যাকরণ"
        if "nctb" not in name:
            return "16_Language_and_Linguistics_ভাষা_ও_ভাষাবিজ্ঞান/English_Language_ইংরেজি_ভাষা"
    if "অভিধান" in name or "dictionary" in name:
        return "23_Reference_Books_তথ্যসূত্র/Dictionary_অভিধান"
    if "সাধারণ জ্ঞান" in name or "general knowledge" in name:
        return "23_Reference_Books_তথ্যসূত্র/General_Knowledge_সাধারণ_জ্ঞান"
    if "মনোবিজ্ঞান" in name or "psychology" in name:
        return "10_Psychology_and_Mind_মনোবিজ্ঞান_ও_মানসিকতা/Cognitive_Psychology"
    if "সংবিধান" in name or "constitution" in name:
        return "07_Politics_and_Government_রাজনীতি_ও_সরকার/Constitution_সংবিধান"
    if "গণতন্ত্র" in name or "democracy" in name:
        return "07_Politics_and_Government_রাজনীতি_ও_সরকার/Democracy_গণতন্ত্র"
    if "মানবাধিকার" in name or "human rights" in name:
        return "07_Politics_and_Government_রাজনীতি_ও_সরকার/Human_Rights_মানবাধিকার"
    if "সমাজকর্ম" in name or "social work" in name:
        return "08_Social_Science_সমাজবিজ্ঞান/Social_Work_সমাজকর্ম"
    if "জনসংখ্যা" in name or "population" in name:
        return "08_Social_Science_সমাজবিজ্ঞান/Population_Studies_জনসংখ্যা"
    if "যুক্তিবিদ্যা" in name or "logic" in name:
        return "09_Philosophy_দর্শন/Logic_যুক্তিবিদ্যা"
    if "নীতিশাস্ত্র" in name or "ethics" in name:
        return "09_Philosophy_দর্শন/Ethics_নীতিশাস্ত্র"
    if "পুষ্টি" in name or "nutrition" in name or "গার্হস্থ্য" in name:
        return "13_Medicine_and_Health_চিকিৎসা_ও_স্বাস্থ্য/Nutrition_পুষ্টি"
    if "ফার্মেসি" in name or "pharmacy" in name:
        return "13_Medicine_and_Health_চিকিৎসা_ও_স্বাস্থ্য/Pharmacy_ফার্মেসি"
    if "বাগান" in name or "gardening" in name:
        return "20_Agriculture_and_Nature_কৃষি_ও_প্রকৃতি/Gardening_বাগান"
    if "মৎস্য" in name or "মাছ" in name or "fisheries" in name:
        return "20_Agriculture_and_Nature_কৃষি_ও_প্রকৃতি/Fisheries_মৎস্য"
    if "পশুপালন" in name or "পোল্ট্রি" in name or "livestock" in name:
        return "20_Agriculture_and_Nature_কৃষি_ও_প্রকৃতি/Animal_Husbandry_পশুপালন"

    return lp


def download_valid_pdf(url: str, dest: Path, max_bytes: int = 3_000_000) -> bool:
    for attempt in range(2):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=25) as resp:
                if resp.status != 200:
                    continue
                ct = (resp.headers.get("Content-Type") or "").lower()
                if "text/html" in ct:
                    return False
                cl = int(resp.headers.get("Content-Length") or 0)
                if cl and cl > max_bytes:
                    return False
                data = resp.read(max_bytes + 1)
                if len(data) < 25_000 or len(data) > max_bytes:
                    return False
                if b"%PDF-" not in data[:1024]:
                    return False
                dest.write_bytes(data)
                return True
        except Exception:
            time.sleep(0.4)
    return False


def search_archive(query: str, rows: int = 24) -> list[dict]:
    full_q = f'mediatype:texts AND format:"Text PDF" AND NOT collection:inlibrary AND {query}'
    url = (
        "https://archive.org/advancedsearch.php?q="
        + urllib.parse.quote(full_q)
        + f"&fl[]=identifier,title,creator&rows={rows}&page=1&output=json"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = json.loads(urllib.request.urlopen(req, timeout=20).read().decode("utf-8"))
    return data.get("response", {}).get("docs", [])


def find_pdf_in_metadata(ident: str, max_bytes: int = 3_000_000) -> str | None:
    try:
        req = urllib.request.Request(f"https://archive.org/metadata/{ident}/files", headers={"User-Agent": "Mozilla/5.0"})
        meta = json.loads(urllib.request.urlopen(req, timeout=12).read().decode("utf-8"))
        pdfs = [
            f for f in meta.get("result", [])
            if f.get("name", "").lower().endswith(".pdf") and 25_000 <= int(f.get("size") or 0) <= max_bytes
        ]
        if not pdfs:
            return None
        pdfs.sort(key=lambda f: int(f.get("size") or 0))
        return f"https://archive.org/download/{ident}/" + urllib.parse.quote(pdfs[0]["name"])
    except Exception:
        return None


def main():
    cab.TMP_DIR.mkdir(parents=True, exist_ok=True)
    state = json.loads(cab.STATE_FILE.read_text(encoding="utf-8"))
    base_books = json.loads((REPO_DIR / "books.json").read_text(encoding="utf-8"))
    extra_books = json.loads(cab.EXTRA_FILE.read_text(encoding="utf-8")) if cab.EXTRA_FILE.exists() else []

    def save_extra():
        with cab.LOCK:
            tmp = cab.EXTRA_FILE.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(extra_books, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp, cab.EXTRA_FILE)

    # ------------------------------------------------------------------
    # PASS 1: Fine-grained classification inside extra_books.json
    # ------------------------------------------------------------------
    print("\n=== PASS 1: Fine-grained classification of extra_books.json ===", flush=True)
    moved_moves = []
    for rec in extra_books:
        new_lp = refine_extra_leaf(rec)
        if new_lp != rec.get("leaf_path") and new_lp in state["folders"]:
            moved_moves.append((rec, new_lp))

    print(f"Extra records eligible for narrower leaf placement: {len(moved_moves)}", flush=True)
    if moved_moves:
        def do_mv(pair):
            rec, new_lp = pair
            b25.gdrive_mv(rec["file_id"], state["folders"][new_lp])
            return rec, new_lp

        mv_ok = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
            for fut in concurrent.futures.as_completed([ex.submit(do_mv, p) for p in moved_moves]):
                rec, new_lp = fut.result()
                parts = new_lp.split("/")
                rec["top_category"] = parts[0]
                rec["leaf_path"] = new_lp
                rec["leaf_category"] = parts[-1]
                mv_ok += 1
        save_extra()
        print(f"Re-classified and moved {mv_ok} Drive files into narrower leaf folders.", flush=True)

    # Deduplication & current counts
    all_now = base_books + extra_books
    seen_source_ids = {b.get("source_id") for b in all_now if b.get("source_id")}
    seen_file_ids = {b["file_id"] for b in all_now}
    seen_norm_names = {cab.norm_name(b["name"]) for b in all_now}
    lc = Counter(b["leaf_path"] for b in all_now)

    classified_leaves = get_classified_leaves()
    sparse_leaves = [lp for lp in classified_leaves if lc[lp] < target_for_leaf(lp)]
    print(
        f"\n=== PASS 2: Fast 20-worker internet collection for {len(sparse_leaves)}/{len(classified_leaves)} sparse leaf folders ===",
        flush=True,
    )

    uploaded_total = 0

    def process_leaf(lp: str) -> int:
        nonlocal uploaded_total
        need = target_for_leaf(lp) - lc[lp]
        if need <= 0:
            return 0
        folder_id = state["folders"].get(lp)
        if not folder_id:
            return 0

        added_here = 0
        queries = build_queries_for_leaf(lp)
        for q_idx, q in enumerate(queries):
            if added_here >= need:
                break
            max_bytes = 3_000_000 if q_idx < 2 else 6_000_000
            try:
                docs = search_archive(q, rows=20)
            except Exception as e:
                print(f"  [Archive warn] {lp}: {e}", flush=True)
                continue

            for doc in docs:
                if added_here >= need:
                    break
                ident = doc.get("identifier")
                if not ident:
                    continue
                sid = f"ia:{ident}"
                title_raw = doc.get("title") or ident
                if isinstance(title_raw, list):
                    title_raw = title_raw[0]
                creator_raw = doc.get("creator") or "Various / Internet Archive"
                if isinstance(creator_raw, list):
                    creator_raw = ", ".join(str(x) for x in creator_raw[:2])
                fname = cab.safe_filename(f"{title_raw}.pdf")
                nname = cab.norm_name(fname)

                with cab.LOCK:
                    if sid in seen_source_ids or nname in seen_norm_names:
                        continue
                    seen_source_ids.add(sid)
                    seen_norm_names.add(nname)

                dl_url = find_pdf_in_metadata(ident, max_bytes=max_bytes)
                if not dl_url:
                    continue

                local_p = cab.TMP_DIR / cab.safe_filename(f"{ident}_{os.getpid()}_{threading.get_ident()}.pdf")
                if not download_valid_pdf(dl_url, local_p, max_bytes=max_bytes):
                    local_p.unlink(missing_ok=True)
                    continue

                fsize = local_p.stat().st_size
                new_id = cab.gdrive_upload(local_p, folder_id)
                local_p.unlink(missing_ok=True)
                if not new_id:
                    continue

                subprocess.run(
                    [cab.GDRIVE, "mutate", "rename", new_id, fname],
                    capture_output=True, text=True, encoding="utf-8"
                )
                rec = cab.build_rec(
                    sid,
                    new_id,
                    fname,
                    fsize,
                    "application/pdf",
                    lp,
                    str(creator_raw)[:80],
                    "Internet Archive Open Library (archive.org)",
                )
                with cab.LOCK:
                    extra_books.append(rec)
                    seen_file_ids.add(new_id)
                    lc[lp] += 1
                    uploaded_total += 1
                    cnt_snap = uploaded_total
                added_here += 1
                print(f"  + [{lp}] ({added_here}/{need}) {fname[:55]}", flush=True)
                if cnt_snap % 15 == 0:
                    save_extra()
        return added_here

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
        list(ex.map(process_leaf, sparse_leaves))

    save_extra()

    # ------------------------------------------------------------------
    # PASS 3: Sync exact Google Drive sizes for size == 0 records
    # ------------------------------------------------------------------
    touched_leaves = sorted({b["leaf_path"] for b in extra_books if not b.get("size")})
    if touched_leaves:
        print(f"\n=== PASS 3: Syncing Drive file sizes across {len(touched_leaves)} leaf folders ===", flush=True)
        id_to_meta = {}

        def fetch_leaf(lp: str):
            fid = state["folders"].get(lp)
            return cab.gdrive_ls(fid) if fid else []

        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
            for items in ex.map(fetch_leaf, touched_leaves):
                for it in items:
                    id_to_meta[it["id"]] = it

        updated = 0
        for b in extra_books:
            if not b.get("size") and b["file_id"] in id_to_meta:
                it = id_to_meta[b["file_id"]]
                b["size"] = int(it.get("size") or 0)
                if it.get("mimeType"):
                    b["mimeType"] = it["mimeType"]
                updated += 1
        print(f"Updated exact Drive sizes for {updated} books.", flush=True)
        save_extra()

    # Final verification summary
    all_final = base_books + extra_books
    tc = Counter(b["top_category"] for b in all_final)
    lc_final = Counter(b["leaf_path"] for b in all_final)
    populated_leaves = sum(1 for lp in classified_leaves if lc_final[lp] > 0)
    still_empty = [lp for lp in classified_leaves if lc_final[lp] == 0]
    unclassified_cnt = sum(lc_final[lp] for lp in SKIP_LEAVES)

    print("\n=== ALL-CATEGORY COLLECTION COMPLETE ===", flush=True)
    print(f"Total books in catalog: {len(all_final)}", flush=True)
    print(f"Top categories populated: {sum(1 for k in b25.TAXONOMY if tc[k] > 0)}/25", flush=True)
    print(f"Classified leaf folders populated: {populated_leaves}/{len(classified_leaves)}", flush=True)
    print(f"Unclassified/To_Be_Organized count (must be 0): {unclassified_cnt}", flush=True)
    for k in b25.TAXONOMY:
        print(f"  {k}: {tc[k]}", flush=True)
    if still_empty:
        print(f"Still empty ({len(still_empty)}):", flush=True)
        for lp in still_empty:
            print(f"  - {lp}", flush=True)


if __name__ == "__main__":
    main()
