"""Canonical 256-leaf classifier for Bangladesh-Biggest-eBook-Library.

Uses strict token boundaries for Bengali/English/Arabic words (never naive
substring matches inside unrelated words or author surnames like 'ইসলাম',
'শিব', 'বুদ্ধ', 'হজ', 'নবী', 'কবর', 'বেদ') and checks explicit source genres,
author-specific literary works, secular topics, non-Islam religions, and
Islamic taxonomy rules in strict precedence.
"""

from __future__ import annotations

import re
import unicodedata

CANONICAL_LEAVES: set[str] = {
    "Religion/Islam/Quran",
    "Religion/Islam/Tafsir",
    "Religion/Islam/Hadith",
    "Religion/Islam/Fiqh",
    "Religion/Islam/Aqeedah",
    "Religion/Islam/Seerah",
    "Religion/Islam/Prophets",
    "Religion/Islam/Sahaba",
    "Religion/Islam/Islamic History",
    "Religion/Islam/Islamic Lifestyle",
    "Religion/Islam/Dua and Prayer",
    "Religion/Islam/Islamic Economics",
    "Religion/Islam/Islamic Politics",
    "Religion/Islam/Islamic Philosophy",
    "Religion/Islam/Islamic Literature",
    "Religion/Islam/Islamic Children Books",
    "Religion/Hinduism",
    "Religion/Buddhism",
    "Religion/Christianity",
    "Religion/Other Religions",
    "Religion/Comparative Religion",
    "Literature/Poetry",
    "Literature/Novels",
    "Literature/Short Stories",
    "Literature/Essays",
    "Literature/Drama",
    "Literature/Plays",
    "Literature/Humorous Literature",
    "Literature/Travel Writing",
    "Literature/Letters",
    "Literature/Literary Criticism",
    "Literature/Autobiography",
    "Literature/Memoirs",
    "Literature/Folk Literature",
    "Literature/Children's Literature",
    "Literature/Prose",
    "Literature/Rhymes",
    "Literature/Collected Works",
    "Fiction/Romance",
    "Fiction/Mystery",
    "Fiction/Detective",
    "Fiction/Thriller",
    "Fiction/Horror",
    "Fiction/Ghost Stories",
    "Fiction/Science Fiction",
    "Fiction/Fantasy",
    "Fiction/Historical Fiction",
    "Fiction/Adventure",
    "Fiction/Psychological Fiction",
    "Fiction/Political Fiction",
    "Fiction/War Fiction",
    "Fiction/Social Fiction",
    "Fiction/Dystopian",
    "Science/Mathematics",
    "Science/Physics",
    "Science/Chemistry",
    "Science/Biology",
    "Science/Astronomy",
    "Science/Geography",
    "Science/Geology",
    "Science/Environmental Science",
    "Science/Genetics",
    "Science/Neuroscience",
    "Science/General Science",
    "Computer and Technology/Computer Science",
    "Computer and Technology/Programming",
    "Computer and Technology/Artificial Intelligence AI",
    "Computer and Technology/Machine Learning",
    "Computer and Technology/Data Science",
    "Computer and Technology/Data Analytics",
    "Computer and Technology/Cybersecurity",
    "Computer and Technology/Networking",
    "Computer and Technology/Web Development",
    "Computer and Technology/Software Engineering",
    "Computer and Technology/Database",
    "Computer and Technology/Robotics",
    "Computer and Technology/Emerging Technology",
    "History/Bangladesh History",
    "History/World History",
    "History/Ancient History",
    "History/Medieval History",
    "History/Modern History",
    "History/Liberation War",
    "History/Language Movement",
    "History/British Period",
    "History/Mughal Period",
    "History/Archaeology",
    "History/Historical Documents",
    "Politics and Government/Political Theory",
    "Politics and Government/Political Parties",
    "Politics and Government/Democracy",
    "Politics and Government/Constitution",
    "Politics and Government/Governance",
    "Politics and Government/International Relations",
    "Politics and Government/Diplomacy",
    "Politics and Government/Public Administration",
    "Politics and Government/Human Rights",
    "Social Science/Sociology",
    "Social Science/Anthropology",
    "Social Science/Psychology",
    "Social Science/Economics",
    "Social Science/Education",
    "Social Science/Social Work",
    "Social Science/Gender Studies",
    "Social Science/Population Studies",
    "Social Science/Culture",
    "Social Science/Development Studies",
    "Philosophy/Logic",
    "Philosophy/Ethics",
    "Philosophy/Metaphysics",
    "Philosophy/Eastern Philosophy",
    "Philosophy/Western Philosophy",
    "Philosophy/Islamic Philosophy",
    "Philosophy/Modern Philosophy",
    "Psychology and Mind/Cognitive Psychology",
    "Psychology and Mind/Behavioral Psychology",
    "Psychology and Mind/Social Psychology",
    "Psychology and Mind/Personality",
    "Psychology and Mind/Emotional Intelligence",
    "Psychology and Mind/Mental Development",
    "Psychology and Mind/Human Behavior",
    "Business and Finance/Entrepreneurship",
    "Business and Finance/Business Management",
    "Business and Finance/Marketing",
    "Business and Finance/Accounting",
    "Business and Finance/Banking",
    "Business and Finance/Finance",
    "Business and Finance/Investment",
    "Business and Finance/Stock Market",
    "Business and Finance/Insurance",
    "Business and Finance/Islamic Finance",
    "Law and Legal/Bangladesh Law",
    "Law and Legal/Constitutional Law",
    "Law and Legal/Criminal Law",
    "Law and Legal/Civil Law",
    "Law and Legal/International Law",
    "Law and Legal/Human Rights Law",
    "Law and Legal/Islamic Law",
    "Medicine and Health/Anatomy",
    "Medicine and Health/Physiology",
    "Medicine and Health/Medicine",
    "Medicine and Health/Surgery",
    "Medicine and Health/Pharmacy",
    "Medicine and Health/Nutrition",
    "Medicine and Health/Public Health",
    "Medicine and Health/Mental Health",
    "Medicine and Health/First Aid",
    "Medicine and Health/Alternative Medicine",
    "Engineering/Electrical Engineering",
    "Engineering/Electronics",
    "Engineering/Mechanical Engineering",
    "Engineering/Civil Engineering",
    "Engineering/Chemical Engineering",
    "Engineering/Architecture",
    "Engineering/Textile Engineering",
    "Engineering/Agricultural Engineering",
    "Engineering/Telecommunications",
    "Education and Academics/Primary Education",
    "Education and Academics/Secondary Education",
    "Education and Academics/Higher Secondary",
    "Education and Academics/University",
    "Education and Academics/Admission Preparation",
    "Education and Academics/Academic Textbooks",
    "Education and Academics/Research Methodology",
    "Education and Academics/Thesis and Dissertation",
    "Education and Academics/Question Banks",
    "Education and Academics/Competitive Exams",
    "Education and Academics/Pre-Primary",
    "Education and Academics/Class 1",
    "Education and Academics/Class 2",
    "Education and Academics/Class 3",
    "Education and Academics/Class 4",
    "Education and Academics/Class 5",
    "Education and Academics/Class 6",
    "Education and Academics/Class 7",
    "Education and Academics/Class 8",
    "Education and Academics/Class 9",
    "Education and Academics/Class 10",
    "Language and Linguistics/Bengali Language",
    "Language and Linguistics/English Language",
    "Language and Linguistics/Arabic Language",
    "Language and Linguistics/Grammar",
    "Language and Linguistics/Linguistics",
    "Language and Linguistics/Translation",
    "Language and Linguistics/Vocabulary",
    "Language and Linguistics/Dictionary",
    "Biography and Autobiography/World Leaders",
    "Biography and Autobiography/Bangladeshi Personalities",
    "Biography and Autobiography/Scientists",
    "Biography and Autobiography/Writers and Poets",
    "Biography and Autobiography/Entrepreneurs",
    "Biography and Autobiography/Historical Personalities",
    "Biography and Autobiography/Autobiographies",
    "Self Development/Productivity",
    "Self Development/Time Management",
    "Self Development/Leadership",
    "Self Development/Communication",
    "Self Development/Critical Thinking",
    "Self Development/Problem Solving",
    "Self Development/Habits",
    "Self Development/Motivation",
    "Self Development/Career Development",
    "Arts and Culture/Painting",
    "Arts and Culture/Photography",
    "Arts and Culture/Music",
    "Arts and Culture/Dance",
    "Arts and Culture/Cinema",
    "Arts and Culture/Theatre",
    "Arts and Culture/Architecture",
    "Arts and Culture/Calligraphy",
    "Arts and Culture/Handicrafts",
    "Agriculture and Nature/Agriculture",
    "Agriculture and Nature/Gardening",
    "Agriculture and Nature/Forestry",
    "Agriculture and Nature/Fisheries",
    "Agriculture and Nature/Animal Husbandry",
    "Agriculture and Nature/Wildlife",
    "Agriculture and Nature/Climate Change",
    "Agriculture and Nature/Biodiversity",
    "Travel and Geography/Bangladesh",
    "Travel and Geography/Asia",
    "Travel and Geography/Europe",
    "Travel and Geography/Africa",
    "Travel and Geography/Americas",
    "Travel and Geography/Travel Guides",
    "Travel and Geography/Travel Memoirs",
    "Travel and Geography/Maps and Atlases",
    "Children and Young Adult/Picture Books",
    "Children and Young Adult/Fairy Tales",
    "Children and Young Adult/Moral Stories",
    "Children and Young Adult/Adventure Stories",
    "Children and Young Adult/Educational Books",
    "Children and Young Adult/Science for Kids",
    "Children and Young Adult/Comics",
    "Children and Young Adult/Teen Fiction",
    "Children and Young Adult/Teen Nonfiction",
    "Reference Books/Encyclopedia",
    "Reference Books/Dictionary",
    "Reference Books/Atlas",
    "Reference Books/Yearbooks",
    "Reference Books/Almanacs",
    "Reference Books/Handbooks",
    "Reference Books/Directories",
    "Reference Books/Bibliography",
    "Reference Books/General Knowledge",
    "Magazines and Periodicals/Literary Magazines",
    "Magazines and Periodicals/Science Magazines",
    "Magazines and Periodicals/Religious Magazines",
    "Magazines and Periodicals/Children's Magazines",
    "Magazines and Periodicals/Newspapers",
    "Magazines and Periodicals/Journals",
    "Magazines and Periodicals/Newsletters",
    "Others and Unclassified/Rare Books",
    "Others and Unclassified/Historical Manuscripts",
    "Others and Unclassified/Unclassified",
    "Others and Unclassified/To Be Organized",
}

EB_GENRE_MAP: list[tuple[str, str]] = [
    ("সায়েন্স ফিকশন", "Fiction/Science Fiction"),
    ("বৈজ্ঞানিক কল্পকাহিনী", "Fiction/Science Fiction"),
    ("গোয়েন্দা", "Fiction/Detective"),
    ("ডিটেকটিভ", "Fiction/Detective"),
    ("ভৌতিক", "Fiction/Horror"),
    ("হরর", "Fiction/Horror"),
    ("ভূতের বই", "Fiction/Ghost Stories"),
    ("থ্রিলার", "Fiction/Thriller"),
    ("রহস্য", "Fiction/Mystery"),
    ("সেবা প্রকাশনী", "Fiction/Thriller"),
    ("বাংলাদেশ ও মুক্তিযুদ্ধ", "History/Liberation War"),
    ("আত্মজীবনী ও স্মৃতিকথা", "Literature/Autobiography"),
    ("ভ্রমণ কাহিনী", "Literature/Travel Writing"),
    ("কিশোর সাহিত্য", "Literature/Children's Literature"),
    ("শিশু", "Literature/Children's Literature"),
    ("ছোটগল্প", "Literature/Short Stories"),
    ("গল্পগ্রন্থ", "Literature/Short Stories"),
    ("গল্পের বই", "Literature/Short Stories"),
    ("কাব্যগ্রন্থ", "Literature/Poetry"),
    ("কবিতা", "Literature/Poetry"),
    ("নাটক", "Literature/Drama"),
    ("রচনাসমগ্র", "Literature/Collected Works"),
    ("রচনাবলী", "Literature/Collected Works"),
    ("রচনা সংকলন", "Literature/Collected Works"),
    ("কৌতুক", "Literature/Humorous Literature"),
    ("রম্যরচনা", "Literature/Humorous Literature"),
    ("প্রবন্ধ ও গবেষণা", "Literature/Essays"),
    ("উপন্যাস", "Literature/Novels"),
    ("অনুবাদ বই", "Literature/Collected Works"),
    ("ইতিহাস ও সংস্কৃতি", "History/Bangladesh History"),
    ("আত্মউন্নয়ন", "Self Development/Motivation"),
    ("গণিত, বিজ্ঞান ও প্রযুক্তি", "Science/General Science"),
    ("গান", "Arts and Culture/Music"),
    ("পত্রিকা", "Magazines and Periodicals/Literary Magazines"),
    ("সাহিত্য ও ভাষা", "Literature/Literary Criticism"),
    ("সংস্কৃত", "Religion/Hinduism"),
    ("ইসলামিক বই", "Religion/Islam/Islamic Lifestyle"),
    ("ধর্ম ও দর্শন", "Philosophy/Eastern Philosophy"),
    ("ধর্মীয় বই", "Religion/Hinduism"),
    ("English Books", "Literature/Novels"),
]

# Famous secular / classic Bengali & world authors whose surnames must never trigger religious misrouting
LITERARY_AUTHORS = tuple(
    unicodedata.normalize("NFC", a).lower()
    for a in (
        "রবীন্দ্রনাথ", "শরৎচন্দ্র", "বঙ্কিমচন্দ্র", "বিদ্যাসাগর", "ঈশ্বরচন্দ্র", "মধুসূদন",
        "কাজী নজরুল ইসলাম", "নজরুল ইসলাম", "জীবনানন্দ", "সুকুমার", "উপেন্দ্রকিশোর",
        "দক্ষিণারঞ্জন", "অবনীন্দ্রনাথ", "মানিক বন্দ্যোপাধ্যায়", "বিভূতিভূষণ", "তারাশঙ্কর",
        "সত্যজিৎ রায়", "হুমায়ূন আহমেদ", "মুহম্মদ জাফর ইকবাল", "জাফর ইকবাল", "শীর্ষেন্দু",
        "সুনীল গঙ্গোপাধ্যায়", "সমরেশ বসু", "সমরেশ মজুমদার", "মণিশংকর", "শংকর",
        "বুদ্ধদেব বসু", "বুদ্ধদেব গুহ", "সুভাষ মুখোপাধ্যায়", "সৈয়দ মুজতবা আলী",
        "শামসুর রাহমান", "আল মাহমুদ", "নির্মলেন্দু", "আহমদ ছফা", "শহীদুল্লা কায়সার",
        "জহির রায়হান", "আখতারুজ্জামান ইলিয়াস", "সেলিনা হোসেন", "হুমায়ুন আজাদ",
        "ইমদাদুল হক মিলন", "আনিসুল হক", "তসলিমা নাসরিন", "বেগম রোকেয়া", "রকিব হাসান",
        "কাজী আনোয়ার", "মুনতাসীর মামুন", "শিবরাম চক্রবর্তী", "নারায়ণ গঙ্গোপাধ্যায়",
        "হেমেন্দ্রকুমার", "নীহাররঞ্জন", "শরদিন্দু", "প্রেমেন্দ্র", "আশাপূর্ণা", "মহাশ্বেতা",
        "লীলা মজুমদার", "দীনবন্ধু", "মীর মশাররফ", "জসীমউদ্দীন", "ফররুখ আহমদ", "সুকান্ত",
        "সৈয়দ ওয়ালীউল্লাহ", "শওকত ওসমান", "হাসান আজিজুল", "রাবেয়া খাতুন", "নবনীতা দেবসেন",
        "জয় গোস্বামী", "শঙ্খ ঘোষ", "বদরুদ্দীন উমর", "আকবর আলি খান", "মুনীর চৌধুরী",
        "কালীপ্রসন্ন সিংহ", "যদুনাথ সরকার", "অতুল সুর", "অমলেন্দু দে", "কাশেম বিন আবু বকর",
        "শিব খেরা", "রশীদ করীম", "আবুল মনসুর আহমদ", "বলাইচাঁদ মুখোপাধ্যায়", "বনফুল",
        "আশাপূর্ণা দেবী", "অতীন বন্দ্যোপাধ্যায়", "হরিশংকর জলদাস", "আশুতোষ মুখোপাধ্যায়",
        "আশুতোষ ভট্টাচার্য", "বাণী বসু", "বিমল কর", "অমিয় চক্রবর্তী",
        "অন্নদাশঙ্কর রায়", "হরপ্রসাদ শাস্ত্রী", "হেলাল হাফিজ", "দেবীপ্রসাদ",
        "আবদুল্লাহ আবু সায়ীদ", "আব্দুল্লাহ আবু সায়ীদ", "কৃষণ চন্দর", "অচিন্ত্যকুমার সেনগুপ্ত",
        "আহমাদ মোস্তফা কামাল", "কিঙ্কর আহসান", "অনীশ দেব", "অবনীন্দ্রনাথ",
        "conan doyle", "agatha christie", "shakespeare", "tagore", "jules verne",
        "george orwell", "fyodor", "tolstoy", "chekhov", "kafka", "hemingway",
        "paulo coelho", "dan brown", "stephen hawking", "harari", "carl sagan",
    )
)

LEGACY_LEAF_HINTS: list[tuple[str, str]] = [
    ("01 - quran & tafsir", "Religion/Islam/Quran"),
    ("02 - hadith & sunnah", "Religion/Islam/Hadith"),
    ("03 - islamic books & aqeedah", "Religion/Islam/Aqeedah"),
    ("04 - seerah, history & biography", "Religion/Islam/Seerah"),
    ("05 - arabic language & dictionaries", "Language and Linguistics/Arabic Language"),
    ("06 - literature & authors", "Literature/Novels"),
]

_BOUND_CACHE: dict[tuple[str, ...], re.Pattern] = {}


def _norm(text: str) -> str:
    return unicodedata.normalize("NFC", text or "").lower()


def _has_word(text: str, words: tuple[str, ...]) -> bool:
    """Match normalized words using full Bangla/ASCII/Arabic script boundaries."""
    if not text or not words:
        return False
    key = tuple(_norm(w) for w in words)
    pat = _BOUND_CACHE.get(key)
    if pat is None:
        alts = "|".join(re.escape(w) for w in sorted(key, key=len, reverse=True))
        pat = re.compile(rf"(?<![A-Za-z0-9\u0980-\u09ff\u0600-\u06ff])(?:{alts})(?:ের|ে|কে|র|য়|তে|গুলি|গুলো|সমূহ|টির|টি|টা)?(?![A-Za-z0-9\u0980-\u09ff\u0600-\u06ff])")
        _BOUND_CACHE[key] = pat
    return bool(pat.search(text))


def _has_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(_norm(p) in text for p in phrases)


def classify_clean_leaf(
    title: str = "",
    author: str = "",
    genres: list[str] | None = None,
    existing_leaf: str = "",
    publication: str = "",
    source_path: str = "",
) -> str:
    """Return a canonical English category/leaf path for any book record."""
    genres_list = genres or []
    t_norm = _norm(title)
    a_norm = _norm(author)
    sp_norm = _norm(source_path)
    pub_norm = _norm(publication)
    genre_blob = " ".join(_norm(g) for g in genres_list)

    # IMPORTANT: match script keywords ONLY on title + genres + source_path (NOT author surnames!)
    topic_text = f"{t_norm} {genre_blob} {sp_norm}"
    full_text = f"{t_norm} {a_norm} {genre_blob} {sp_norm}"

    # 1. Preserve authoritative special-collection leaf paths
    if "nctb" in pub_norm or existing_leaf.startswith("Education and Academics/Class") or existing_leaf == "Education and Academics/Pre-Primary":
        if existing_leaf in CANONICAL_LEAVES:
            return existing_leaf

    if "university physics" in pub_norm and "medical" in pub_norm:
        return "Medicine and Health/Public Health"

    if "covid-19" in pub_norm:
        return "Medicine and Health/Public Health"

    if existing_leaf == "Religion/Islam/Hadith" and "sunnah" in pub_norm:
        return "Religion/Islam/Hadith"

    # 2. Explicit eBanglaLibrary genre mapping (highest fidelity!)
    if genre_blob:
        for kw, leaf in EB_GENRE_MAP:
            if _norm(kw) in genre_blob:
                if leaf == "Science/General Science":
                    if _has_any(topic_text, ("গণিত", "math", "বীজগণিত", "জ্যামিতি", "পাই", "সংখ্যা")):
                        return "Science/Mathematics"
                    if _has_any(topic_text, ("পদার্থ", "physics", "মহাকাশ", "কোয়ান্টাম", "আপেক্ষিকতা", "স্টিফেন হকিং")):
                        return "Science/Physics"
                    if _has_any(topic_text, ("কম্পিউটার", "প্রোগ্রামিং", "পাইথন", "software", "programming")):
                        return "Computer and Technology/Computer Science"
                if leaf == "Philosophy/Eastern Philosophy" and _has_word(topic_text, ("ইসলাম", "কুরআন", "হাদিস", "রাসূল", "নবী", "সাহাবী", "ফিকহ")):
                    return "Religion/Islam/Islamic Philosophy"
                return leaf

    # 3. Trust explicit non-fallback leaf if valid and NOT a noisy fallback bucket
    FALLBACK_BUCKETS = {
        "Religion/Islam/Quran",
        "Religion/Islam/Islamic Lifestyle",
        "Literature/Novels",
        "Literature/Collected Works",
        "Others and Unclassified/Unclassified",
        "Others and Unclassified/To Be Organized",
    }
    ex_norm = _norm(existing_leaf)
    clean_ex = unicodedata.normalize("NFC", existing_leaf)
    clean_ex = clean_ex[5:] if clean_ex.startswith("text/") else clean_ex
    clean_ex = clean_ex[4:] if clean_ex.startswith("pdf/") else clean_ex
    if clean_ex in CANONICAL_LEAVES and clean_ex not in FALLBACK_BUCKETS:
        if "النحو" in topic_text or "আরবি ব্যাকরণ" in topic_text:
            return "Language and Linguistics/Arabic Language"
        return clean_ex

    is_legacy_islamic = any(k in ex_norm or k in sp_norm for k in (
        "01 - quran", "02 - hadith", "03 - islamic", "04 - seerah",
        "ইসলামী বই", "ইসলামীক বই", "বই বিতরন",
    ))

    # Explicit Arabic language books (এসো আরবি শিখি, নাহু, ছারফ, আদদুরুসুল...)
    if "05 - arabic language" in ex_norm or "আরবী ভাষা শিক্ষা" in sp_norm or _has_any(topic_text, (
        "আদদুরুসুল আরাবিয়্যা", "আল লুগাতুল আরাবিয়াতুল", "এসো আরবি শিখি", "এসো ছারফ শিখি", "এসো নাহু শিখি", "এসো ফিকাহ শিখি", "আল তামরীন আল কিতাবী", "النحو", "quranic grammar"
    )):
        if "এসো ফিকাহ" in topic_text:
            return "Religion/Islam/Fiqh"
        return "Language and Linguistics/Arabic Language"

    # Mrinal subfolder specific domain rules
    if "বাংলা ছন্দ ও অলঙ্কার" in sp_norm or "বাংলা প্রবাদ প্রবচন" in sp_norm or "বাংলা একাডেমি" in sp_norm:
        if "প্রবাদ" in sp_norm:
            return "Literature/Folk Literature"
        return "Language and Linguistics/Bengali Language"
    if "ছোটদের বই" in sp_norm:
        return "Literature/Children's Literature"
    if "বৈষ্ণব সাহিত্য" in sp_norm:
        return "Religion/Hinduism"
    if "আয়মান সাদিক" in sp_norm or "আয়মান সাদিক" in a_norm:
        return "Self Development/Career Development"
    if "অতুল সুর" in sp_norm or "অমলেন্দু দে" in sp_norm or "যদুনাথ সরকার" in sp_norm:
        return "History/Ancient History" if "সুর" in sp_norm else "History/Bangladesh History"
    if "দেবীপ্রসাদ" in sp_norm or "আরজ আলী" in sp_norm:
        if not ("রম্য" in t_norm or "03 - islamic" in ex_norm):
            return "Philosophy/Eastern Philosophy"

    # 4. Specific character/series & secular domains
    if _has_any(full_text, ("ফেলুদা", "ব্যোমকেশ", "কাকাবাবু", "মাসুদ রানা", "তিন গোয়েন্দা", "তিন গোয়েন্দা", "মিসির আলি", "শুভ্র", "শার্লক", "শেরলক", "গোয়েন্দা", "detective", "রহস্য পত্রিকা", "অগাথা", "কিরীটী", "শবর", "মিতিন মাসি", "পাণ্ডব গোয়েন্দা", "প্রদোষচন্দ্র", "টিনটোরেটোর")):
        if "মাসুদ রানা" in full_text:
            return "Fiction/Thriller"
        return "Fiction/Detective"
    if _has_any(full_text, ("সায়েন্স ফিকশন", "বৈজ্ঞানিক কল্পকাহিনী", "কল্পবিজ্ঞান", "science fiction", "sci-fi", "মহাকাশ অভিযান", "আইজ্যাক আসিমভ", "আসিমভ", "জুল ভার্ন", "প্রফেসর শঙ্কু")) or (_has_word(topic_text, ("ফাউন্ডেশন",)) and "ইসলামিক" not in full_text):
        return "Fiction/Science Fiction"
    if _has_word(topic_text, ("হিমু",)):
        return "Literature/Novels"
    if _has_any(topic_text, ("ভৌতিক", "হরর", "অশরীরী", "horror", "ghost", "ড্রাকুলা")) or _has_word(topic_text, ("ভূত", "প্রেত", "ভূতের")):
        return "Fiction/Horror"
    if _has_any(topic_text, ("থ্রিলার", "thriller", "অ্যাডভেঞ্চার", "adventure", "রবিনসন ক্রুসো", "ট্রেজার আইল্যান্ড")):
        return "Fiction/Thriller"

    # Liberation War, History, Constitution, Politics, Cyber, Science, Business
    if _has_any(topic_text, ("মুক্তিযুদ্ধ", "একাত্তর", "১৯৭১", "1971", "স্বাধীনতা যুদ্ধ", "বুদ্ধিজীবী হত্যা")):
        return "History/Liberation War"
    if _has_any(topic_text, ("ভাষা আন্দোলন", "বায়ান্ন", "১৯৫২")):
        return "History/Language Movement"
    if _has_any(topic_text, ("সংবিধান", "constitution")):
        return "Politics and Government/Constitution"
    if _has_any(topic_text, ("সাইবার", "ফিশিং", "হ্যাকিং", "ডিজিটাল প্রতারণা", "python", "javascript", "programming", "কম্পিউটার", "সফটওয়্যার", "database", "algorithm", "machine learning", "artificial intelligence")):
        return "Computer and Technology/Computer Science"
    if _has_any(topic_text, ("গণিত", "বীজগণিত", "জ্যামিতি", "ক্যালকুলাস", "মানসাঙ্ক", "mansanka", "mathematics", "calculus", "geometry")):
        return "Science/Mathematics"
    if (_has_any(topic_text, ("পদার্থবিজ্ঞান", "quantum", "জ্যোতির্বিজ্ঞান", "astronomy", "স্টিফেন হকিং", "বিবর্তন", "জীববিজ্ঞান", "রসায়ন", "science")) or _has_word(topic_text, ("বিজ্ঞান", "physics", "মহাবিশ্ব"))) and not _has_word(topic_text, ("কোরআন", "কুরআন")):
        return "Science/General Science"
    if (_has_any(topic_text, ("চিকিৎসা", "স্বাস্থ্য", "হোমিও", "আয়ুর্বেদ", "পুষ্টি", "medicine", "health", "anatomy"))) and not _has_word(topic_text, ("কোরআনী", "আমলে", "রুহানী", "হাদীস", "কুরআন", "কোরআন", "রোজা", "রোযা")):
        return "Medicine and Health/Medicine"
    if (_has_any(topic_text, ("দণ্ডবিধি", "penal code", "অধিকার আইন")) or _has_word(topic_text, ("আইন", "law"))) and not is_legacy_islamic and not _has_word(topic_text, ("কুফর", "হিন্দুআইন", "শরীয়ত", "ইসলামী")):
        return "Law and Legal/Bangladesh Law"
    if _has_any(topic_text, ("মার্কেটিং", "শেয়ার বাজার", "বিনিয়োগ", "ব্যাংকিং", "চিরস্থায়ী বন্দোবস্ত", "finance", "economics", "business", "marketing", "rich dad", "atomic habits")) or _has_word(topic_text, ("ব্যবসা", "অর্থনীতি")):
        if _has_word(topic_text, ("ইসলাম", "ইসলামী", "সুদ", "রিবা")):
            return "Religion/Islam/Islamic Economics"
        return "Business and Finance/Entrepreneurship"
    if _has_any(topic_text, ("তুমিও জিতবে", "আত্মউন্নয়ন", "আত্মউন্নয়ন", "মোটিভেশন", "motivation", "productivity", "self help", "habits")) or ("শিব খেরা" in a_norm):
        return "Self Development/Motivation"
    if _has_any(topic_text, ("ব্যাকরণ", "অভিধান", "ডিকশনারি", "স্পোকেন ইংলিশ", "grammar", "dictionary", "vocabulary", "ielts", "translation")):
        if "আরবি" in topic_text or "আরবী" in topic_text or "arabic" in topic_text or "النحو" in topic_text:
            return "Language and Linguistics/Arabic Language"
        if "english" in topic_text or "ইংরেজি" in topic_text or "ielts" in topic_text:
            return "Language and Linguistics/English Language"
        return "Language and Linguistics/Bengali Language"

    # Literary genres & secular authors (BEFORE religious substring checks!)
    is_secular_author = any(au in a_norm or au in sp_norm for au in LITERARY_AUTHORS)

    if _has_any(topic_text, ("কাব্যগ্রন্থ", "কাব্যসমগ্র", "সনেট", "গীতাঞ্জলি", "সঞ্চিতা", "সঞ্চয়িতা", "অগ্নিবীণা", "ফণি-মনসা", "চক্রবাক", "poetry", "poems")) or _has_word(topic_text, ("কবিতা", "কাব্য", "পদ্য")):
        return "Literature/Poetry"
    if _has_any(topic_text, ("নাট্যগ্রন্থ", "নাট্যসমগ্র", "নাট্যাবলী", "একাঙ্কিকা", "drama")) or _has_word(topic_text, ("নাটক", "কবর")) and (is_secular_author or "মুনীর" in a_norm):
        return "Literature/Drama"
    if _has_any(topic_text, ("ভ্রমণকাহিনী", "ভ্রমণ কাহিনী", "দেশে বিদেশে", "পথে প্রবাসে", "travelogue")) or _has_word(topic_text, ("ভ্রমণ", "travel")):
        return "Literature/Travel Writing"
    if _has_any(topic_text, ("ছোটগল্প", "গল্পসমগ্র", "গল্পগুচ্ছ", "গল্পসংকলন", "শ্রেষ্ঠ গল্প", "নির্বাচিত গল্প", "হক সাহেবের হাসির গল্প", "দমফাটা হাসির গল্প", "ব্যথার দান", "রিক্তের বেদন", "শিউলিমালা", "short stories")):
        return "Literature/Short Stories"
    if _has_any(topic_text, ("আহমদ দিদাত", "ahmed deedat", "তুলনামূলক ধর্ম", "comparative religion")):
        return "Religion/Comparative Religion"
    if _has_any(topic_text, ("রচনাবলী", "রচনাবলি", "রচনাসমগ্র", "উপন্যাস সমগ্র", "উপন্যাসসমগ্র", "complete works", "collected works")) and not is_legacy_islamic:
        return "Literature/Collected Works"
    if _has_any(topic_text, ("মাসিক আল-আবরার", "আল-আবরার", "সাপ্তাহিক আরাফাত", "সাম্নাহিক আরাফাত", "عرفات الاسبوعية", "ﻋﺮﻓﺎت")):
        return "Magazines and Periodicals/Religious Magazines"
    if _has_any(topic_text, ("সাহিত্যচর্চা", "সংস্কৃতির ভাঙা সেতু", "সংস্কৃতির সংকট", "রাজবন্দীর জবানবন্দি", "যুগবাণী", "রুদ্রমঙ্গল", "দুর্দিনের যাত্রী", "পত্রগুচ্ছ", "হুতোমপ্যাঁচার নক্সা", "সাহিত্য-সাধনা", "ওয়াজেদ আলির উপন্যাস", "সাহিত্য সমালোচনা")) or (_has_word(topic_text, ("প্রবন্ধ", "সমালোচনা", "essay")) and not is_legacy_islamic and not _has_word(topic_text, ("তাবলীগ", "ইসলাম", "কুরআন", "কোরআন", "হাদিস", "হাদীস", "মাজহাব", "মাযহাব", "আহলে"))):
        if "সাহিত্য-সাধনা" in topic_text or "ওয়াজেদ আলির উপন্যাস" in topic_text or "সাহিত্য সমালোচনা" in topic_text:
            return "Literature/Literary Criticism"
        return "Literature/Essays"
    if (_has_any(topic_text, ("হাসির গল্প", "টেনিদা", "ঘনাদা", "গোপাল ভাঁড়", "নাসিরুদ্দিন হোজ্জা", "বিরবল", "হর্ষবর্ধণ")) or _has_word(topic_text, ("রম্য", "কৌতুক"))) and not is_legacy_islamic:
        return "Literature/Humorous Literature"
    if _has_any(topic_text, ("আত্মজীবনী", "স্মৃতিকথা", "অসমাপ্ত আত্মজীবনী", "কারাগারের রোজনামচা", "আমার দেখা নয়াচীন", "জীবনী", "জীবনকথা", "biography", "autobiography", "memoir")) and not _has_word(topic_text, ("নবী", "রাসূল", "রাসুল", "সাহাবী", "ইসলাম", "মুসলিম")):
        return "Biography and Autobiography/Autobiographies"
    if _has_any(topic_text, ("রূপকথা", "ঠাকুরমার ঝুলি", "টুনটুনি", "নন্টে ফন্টে", "হাঁদা ভোঁদা", "বাঁটুল", "চাঁদের পাহাড়", "ক্ষীরের পুতুল", "বুড়ো আংলা", "টিনটিন", "হ্যারি পটার", "কমিক্স", "উন্মাদ", "unnmad")):
        if any(k in topic_text for k in ("টিনটিন", "নন্টে ফন্টে", "বাঁটুল", "কমিক্স", "comics", "উন্মাদ", "unnmad")):
            return "Children and Young Adult/Comics"
        return "Literature/Children's Literature"
    if _has_any(topic_text, ("গৌড়লেখমালা", "বাঙালীর ইতিহাস", "বাংলার ইতিহাস", "উনিশ শতকের বাঙালী", "বাঙলাদেশের কৃষক", "অবাক বাংলাদেশ", "শিবাজী")) or (_has_word(topic_text, ("ইতিহাস", "history")) and not is_legacy_islamic and not _has_word(topic_text, ("ইসলাম", "ইসলামের", "খিলাফত", "মুসলিম", "সাহাবী", "ইহুদী"))):
        return "History/Bangladesh History"

    # If the author is a known secular/literary figure (Tagore, Nazrul, Satyajit, Humayun, Buddhadeb, Shibaram, Kashem bin Abu Bakar, Badruddin Umar, Akbar Ali Khan, etc.)
    # do NOT let generic religion checks capture their secular novels unless the TITLE is explicitly religious!
    if is_secular_author:
        if "দর্শন" in topic_text:
            return "Philosophy/Eastern Philosophy"
        return "Literature/Novels"

    # Explicit non-Islam religion rules (strict whole-word boundaries on topic_text ONLY!)
    if _has_any(topic_text, ("মহাভারত", "রামায়ণ", "রামায়ণ", "উপনিষদ", "শ্রীমদ্ভগবদ্গীতা", "ভগবদ্গীতা", "স্বামী বিবেকানন্দ", "রামকৃষ্ণ পরমহংস", "চৈতন্যচরিতামৃত")) or _has_word(topic_text, ("গীতা", "বেদ", "পুরাণ", "হিন্দু", "শ্রীকৃষ্ণ", "চৈতন্য", "সনাতন", "কর্মযোগ", "জ্ঞানযোগ", "ভক্তিযোগ", "রাজযোগ", "hindu", "veda", "gita")):
        return "Religion/Hinduism"
    if _has_word(topic_text, ("বৌদ্ধ", "গৌতম বুদ্ধ", "বুদ্ধ", "ত্রিপিটক", "জাতক", "ধম্মপদ", "buddhism")):
        return "Religion/Buddhism"
    if _has_word(topic_text, ("বাইবেল", "খ্রিস্ট", "খ্রিষ্ট", "খ্রিস্টধর্ম", "যীশু", "bible", "christianity")):
        return "Religion/Christianity"

    # Explicit Islamic rules (strict word boundary on topic_text ONLY!)
    if _has_any(topic_text, ("তাফসির", "তাফসীর", "tafsir", "ইবনে কাসির", "ইবনে কাসীর", "ফি যিলালিল", "মাআরেফুল", "তাফহীমুল", "تفسير")):
        return "Religion/Islam/Tafsir"
    if _has_word(topic_text, ("কুরআন", "কোরআন", "আল-কুরআন", "আল-কোরআন", "quran", "তাজবীদ", "তাজবিদ", "কিরাত", "সূরা", "সুরা", "কোরআনী")) or _has_any(topic_text, ("قرآن", "القرآن")):
        return "Religion/Islam/Quran"
    if _has_word(topic_text, ("হাদিস", "হাদীস", "hadith", "বুখারী", "বুখারি", "মুসলিম শরীফ", "তিরমিযী", "তিরমিজি", "নাসাঈ", "আবু দাউদ", "ইবনে মাজাহ", "মিশকাত", "রিয়াদুস", "রিয়াদুস", "হিসনুল")) or _has_any(topic_text, ("حديث", "سنن", "صحيح")):
        return "Religion/Islam/Hadith"
    if _has_any(topic_text, ("রাহীকুল মাখতুম", "সীরাতুন নবী", "সীরাতুল মোস্তফা", "রাসূলুল্লাহ", "রাসুলুল্লাহ", "seerah", "ﷺ")) or _has_word(topic_text, ("সীরাত", "সিরাত", "নবীজী", "নবীজি", "মহানবী", "বিশ্বনবী")):
        return "Religion/Islam/Seerah"
    if _has_word(topic_text, ("সাহাবী", "সাহাবি", "সাহাবা", "হায়াতুস সাহাবা", "আসহাবে রাসূল", "খালিদ বিন ওয়ালীদ")):
        return "Religion/Islam/Sahaba"
    if _has_word(topic_text, ("নবীদের", "নবীনদের", "কাসাসুল আম্বিয়া")) or _has_any(topic_text, ("নবী আঃ", "ইব্রাহিম আঃ", "মূসা আঃ", "ঈসা আঃ", "ইউসুফ আঃ")):
        return "Religion/Islam/Prophets"
    if _has_word(topic_text, ("নামাজ", "নামায", "সালাত", "দোয়া", "দোয়া", "দুআ", "ওযু", "অজু", "যিকির", "জিকির", "মুনাজাত", "তারাবী", "ইতিকাফ", "ফজর")):
        return "Religion/Islam/Dua and Prayer"
    if _has_word(topic_text, ("ফিকহ", "ফতোয়া", "ফাতাওয়া", "মাসআলা", "মাসায়েল", "রোজা", "রোযা", "সিয়াম", "যাকাত", "জাকাত", "হজ্জ", "হজ", "কুরবানী", "কোরবানি", "তালাক", "হালাল", "হারাম", "মাজহাব", "মাযহাব", "fiqh", "fatwa", "শরীয়াহ", "শরিয়াহ", "শরীয়ত")) or _has_any(topic_text, ("islamic jurisprudence", "islamic law")):
        return "Religion/Islam/Fiqh"
    if _has_word(topic_text, ("আকীদা", "আকিদা", "তাওহীদ", "তৌহিদ", "শিরক", "শির্ক", "বিদআত", "বিদাত", "কিয়ামত", "কিয়ামত", "দাজ্জাল", "ফিতনা", "আখিরাত", "জান্নাত", "জান্নাতী", "জাহান্নাম", "ইমাম মাহদী", "কবর", "aqeedah", "কুফর")) or _has_any(topic_text, ("মরনের পর", "মরণের পর")):
        return "Religion/Islam/Aqeedah"
    if _has_any(topic_text, ("ইসলামের ইতিহাস", "আন্দালুস", "কারবালা", "medieval uzbekistan", "uzbek scholars", "shaybani", "abul hasan ali nadwi", "muhammad hamidullah", "madrasa education", "500 most influential muslims", "siddique hasan khan", "medical sciences in islamic history")) or _has_word(topic_text, ("খিলাফত", "খেলাফত", "উসমানীয়", "ক্রুসেড")):
        return "Religion/Islam/Islamic History"
    if _has_any(topic_text, ("ইসলামী রাষ্ট্র", "ইসলামী রাজনীতি", "গাজওয়াতুল")) or _has_word(topic_text, ("জিহাদ", "জিহাদী", "উম্মাহ")):
        return "Religion/Islam/Islamic Politics"
    if _has_word(topic_text, ("ইসলাম", "মুসলিম", "ইসলামী", "দাওয়াত", "দাওয়াহ", "পর্দা", "হিজাব", "তাবলীগ", "ইসলামিক", "তাযকিয়া", "আল্লাহ", "আল্লাহর", "রিজিক", "সুন্নাত", "islam")) or _has_any(topic_text, ("zakir naik", "জাকির নায়েক", "shifa ul arwah", "দ্যা রিভার্টস", "ক্যান্টিনে")) or "النحو" in topic_text:
        if "النحو" in topic_text:
            return "Language and Linguistics/Arabic Language"
        return "Religion/Islam/Islamic Lifestyle"

    if _has_any(topic_text, ("southern thailand",)):
        return "History/World History"

    if re.search(r"[\u0600-\u06ff]{3,}", topic_text):
        return "Religion/Islam/Islamic Lifestyle"

    if "university physics" in pub_norm:
        return "Science/Physics"

    # Fallback by legacy folder hints
    for hint, target_leaf in LEGACY_LEAF_HINTS:
        if hint in ex_norm or hint in sp_norm:
            return target_leaf

    # Literary sources default cleanly to Literature/Novels!
    if any(p in pub_norm or p in sp_norm for p in ("bongboi", "kindle bangla", "ebanglalibrary", "bdebooks", "mrinal", "মৃণাল", "sm-collection")):
        return "Literature/Novels"

    if clean_ex in CANONICAL_LEAVES:
        if any(s in pub_norm for s in ("irfan", "israt", "bd public")):
            return clean_ex
        return "Literature/Novels"

    return "Others and Unclassified/Unclassified"
