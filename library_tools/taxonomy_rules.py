"""Canonical taxonomy, author normalization, language detection, series detection,
and target Google Drive folder mapping for Bangladesh-Biggest-eBook-Library.
"""
from __future__ import annotations

import re
import unicodedata

BN_RE = re.compile(r"[\u0980-\u09FF]")
AR_RE = re.compile(r"[\u0600-\u06FF]")
LATIN_RE = re.compile(r"[A-Za-z]")

UNKNOWN_AUTHOR_TOKENS = {
    "", "unknown", "unknown author", "various", "various / unknown",
    "various unknown", "various / compiled", "various compiled",
    "various / compiled (সংকলিত)", "various compiled (সংকলিত)",
    "various compiled (songkolit)", "compiled", "সংকলিত", "লেখক অজানা",
    "অজানা", "n/a", "none", "null", "anonymous", "e", "রা e", "ম e",
    "linguisticmiracle.com", "tanbircox", "pdfbd", "banglapdf", "amarboi",
    "boierhut", "murchona", "boighor", "ebanglalibrary", "islamicbook.ws",
    "muslim", "islamic", "editor", "edited", "সম্পাদিত",
}

# Canonical author map: lowercased/normalized variant -> (bangla_canonical, english_canonical)
AUTHOR_CANONICAL: dict[str, tuple[str, str]] = {
    "হুমায়ূন আহমেদ": ("হুমায়ূন আহমেদ", "Humayun Ahmed"),
    "humayun ahmed": ("হুমায়ূন আহমেদ", "Humayun Ahmed"),
    "humajun ahmed": ("হুমায়ূন আহমেদ", "Humayun Ahmed"),
    "রবীন্দ্রনাথ ঠাকুর": ("রবীন্দ্রনাথ ঠাকুর", "Rabindranath Tagore"),
    "rabindranath tagore": ("রবীন্দ্রনাথ ঠাকুর", "Rabindranath Tagore"),
    "কাজী আনোয়ার হোসেন": ("কাজী আনোয়ার হোসেন", "Kazi Anwar Hossain"),
    "kazi anojar hossain": ("কাজী আনোয়ার হোসেন", "Kazi Anwar Hossain"),
    "kazi anwar hossain": ("কাজী আনোয়ার হোসেন", "Kazi Anwar Hossain"),
    "সুনীল গঙ্গোপাধ্যায়": ("সুনীল গঙ্গোপাধ্যায়", "Sunil Gangopadhyay"),
    "sunil gangopadhyay": ("সুনীল গঙ্গোপাধ্যায়", "Sunil Gangopadhyay"),
    "সত্যজিৎ রায়": ("সত্যজিৎ রায়", "Satyajit Ray"),
    "satyajit ray": ("সত্যজিৎ রায়", "Satyajit Ray"),
    "মুহম্মদ জাফর ইকবাল": ("মুহম্মদ জাফর ইকবাল", "Muhammed Zafar Iqbal"),
    "muhammed zafar iqbal": ("মুহম্মদ জাফর ইকবাল", "Muhammed Zafar Iqbal"),
    "আবুল আসাদ": ("আবুল আসাদ", "Abul Asad"),
    "abul asad": ("আবুল আসাদ", "Abul Asad"),
    "বুদ্ধদেব গুহ": ("বুদ্ধদেব গুহ", "Buddhadeb Guha"),
    "buddhodeb guh": ("বুদ্ধদেব গুহ", "Buddhadeb Guha"),
    "buddhadeb guha": ("বুদ্ধদেব গুহ", "Buddhadeb Guha"),
    "বুদ্ধদেব বসু": ("বুদ্ধদেব বসু", "Buddhadeb Basu"),
    "buddhodeb basu": ("বুদ্ধদেব বসু", "Buddhadeb Basu"),
    "কাজী নজরুল ইসলাম": ("কাজী নজরুল ইসলাম", "Kazi Nazrul Islam"),
    "kazi nazrul islam": ("কাজী নজরুল ইসলাম", "Kazi Nazrul Islam"),
    "সমরেশ বসু": ("সমরেশ বসু", "Samaresh Basu"),
    "somoresh basu": ("সমরেশ বসু", "Samaresh Basu"),
    "সমরেশ মজুমদার": ("সমরেশ মজুমদার", "Samaresh Majumdar"),
    "somoresh mojumodar": ("সমরেশ মজুমদার", "Samaresh Majumdar"),
    "samaresh majumdar": ("সমরেশ মজুমদার", "Samaresh Majumdar"),
    "শীর্ষেন্দু মুখোপাধ্যায়": ("শীর্ষেন্দু মুখোপাধ্যায়", "Shirshendu Mukhopadhyay"),
    "শীর্ষেন্দু মুখােপাধ্যায়": ("শীর্ষেন্দু মুখোপাধ্যায়", "Shirshendu Mukhopadhyay"),
    "shirshendu mukhopadhyay": ("শীর্ষেন্দু মুখোপাধ্যায়", "Shirshendu Mukhopadhyay"),
    "shirshendu mukhaepadhdhaj": ("শীর্ষেন্দু মুখোপাধ্যায়", "Shirshendu Mukhopadhyay"),
    "আশাপূর্ণা দেবী": ("আশাপূর্ণা দেবী", "Ashapurna Devi"),
    "ashapurna devi": ("আশাপূর্ণা দেবী", "Ashapurna Devi"),
    "অনিল ভৌমিক": ("অনিল ভৌমিক", "Anil Bhoumik"),
    "onil bhoumik": ("অনিল ভৌমিক", "Anil Bhoumik"),
    "শরদিন্দু বন্দ্যোপাধ্যায়": ("শরদিন্দু বন্দ্যোপাধ্যায়", "Sharadindu Bandyopadhyay"),
    "shorodindu bandyopadhyay": ("শরদিন্দু বন্দ্যোপাধ্যায়", "Sharadindu Bandyopadhyay"),
    "সৈয়দ মুজতবা আলী": ("সৈয়দ মুজতবা আলী", "Syed Mujtaba Ali"),
    "soijd mujotoba ali": ("সৈয়দ মুজতবা আলী", "Syed Mujtaba Ali"),
    "কাসেম বিন আবুবাকার": ("কাসেম বিন আবুবাকার", "Kashem Bin Abubakar"),
    "kasem bin abubakar": ("কাসেম বিন আবুবাকার", "Kashem Bin Abubakar"),
    "কোয়েল তালুকদার": ("কোয়েল তালুকদার", "Koyel Talukdar"),
    "kojel talukodar": ("কোয়েল তালুকদার", "Koyel Talukdar"),
    "শরৎচন্দ্র চট্টোপাধ্যায়": ("শরৎচন্দ্র চট্টোপাধ্যায়", "Sarat Chandra Chattopadhyay"),
    "sarat chandra chattopadhyay": ("শরৎচন্দ্র চট্টোপাধ্যায়", "Sarat Chandra Chattopadhyay"),
    "উইলিয়াম শেক্সপিয়ার": ("উইলিয়াম শেক্সপিয়ার", "William Shakespeare"),
    "uilijam sheksopijar": ("উইলিয়াম শেক্সপিয়ার", "William Shakespeare"),
    "william shakespeare": ("উইলিয়াম শেক্সপিয়ার", "William Shakespeare"),
    "হিমাদ্রিকিশোর দাশগুপ্ত": ("হিমাদ্রিকিশোর দাশগুপ্ত", "Himadrikishor Dasgupta"),
    "himadrikishor dashogupt": ("হিমাদ্রিকিশোর দাশগুপ্ত", "Himadrikishor Dasgupta"),
    "বঙ্কিমচন্দ্র চট্টোপাধ্যায়": ("বঙ্কিমচন্দ্র চট্টোপাধ্যায়", "Bankim Chandra Chattopadhyay"),
    "bankim chandra chattopadhyay": ("বঙ্কিমচন্দ্র চট্টোপাধ্যায়", "Bankim Chandra Chattopadhyay"),
    "রকিব হাসান": ("রকিব হাসান", "Rakib Hasan"),
    "rokib hasan": ("রকিব হাসান", "Rakib Hasan"),
    "শক্তি চট্টোপাধ্যায়": ("শক্তি চট্টোপাধ্যায়", "Shakti Chattopadhyay"),
    "shokti chattopadhyay": ("শক্তি চট্টোপাধ্যায়", "Shakti Chattopadhyay"),
    "আসাদ বিন হাফিজ": ("আসাদ বিন হাফিজ", "Asad Bin Hafiz"),
    "asad bin haphij": ("আসাদ বিন হাফিজ", "Asad Bin Hafiz"),
    "বিভূতিভূষণ বন্দ্যোপাধ্যায়": ("বিভূতিভূষণ বন্দ্যোপাধ্যায়", "Bibhutibhushan Bandyopadhyay"),
    "bibhutibhushan bandyopadhyay": ("বিভূতিভূষণ বন্দ্যোপাধ্যায়", "Bibhutibhushan Bandyopadhyay"),
    "তসলিমা নাসরিন": ("তসলিমা নাসরিন", "Taslima Nasrin"),
    "tosolima nasorin": ("তসলিমা নাসরিন", "Taslima Nasrin"),
    "বাণী বসু": ("বাণী বসু", "Bani Basu"),
    "bani basu": ("বাণী বসু", "Bani Basu"),
    "সঞ্জীব চট্টোপাধ্যায়": ("সঞ্জীব চট্টোপাধ্যায়", "Sanjib Chattopadhyay"),
    "sonjib chattopadhyay": ("সঞ্জীব চট্টোপাধ্যায়", "Sanjib Chattopadhyay"),
    "সৈয়দ মুস্তাফা সিরাজ": ("সৈয়দ মুস্তাফা সিরাজ", "Syed Mustafa Siraj"),
    "soijd mustapha siraj": ("সৈয়দ মুস্তাফা সিরাজ", "Syed Mustafa Siraj"),
    "সুচিত্রা ভট্টাচার্য": ("সুচিত্রা ভট্টাচার্য", "Suchitra Bhattacharya"),
    "suchitra bhattacharya": ("সুচিত্রা ভট্টাচার্য", "Suchitra Bhattacharya"),
    "হুমায়ুন আজাদ": ("হুমায়ুন আজাদ", "Humayun Azad"),
    "humajun ajad": ("হুমায়ুন আজাদ", "Humayun Azad"),
    "অভীক দত্ত": ("অভীক দত্ত", "Avik Dutta"),
    "obhik dutta": ("অভীক দত্ত", "Avik Dutta"),
    "মলয় রায়চৌধুরী": ("মলয় রায়চৌধুরী", "Malay Roy Choudhury"),
    "moloj rajchoudhuri": ("মলয় রায়চৌধুরী", "Malay Roy Choudhury"),
    "আর্থার কোনান ডয়েল": ("আর্থার কোনান ডয়েল", "Arthur Conan Doyle"),
    "arthar konan dojel": ("আর্থার কোনান ডয়েল", "Arthur Conan Doyle"),
    "arthur conan doyle": ("আর্থার কোনান ডয়েল", "Arthur Conan Doyle"),
    "নবনীতা দেবসেন": ("নবনীতা দেবসেন", "Nabaneeta Dev Sen"),
    "বিমল কর": ("বিমল কর", "Bimal Kar"),
    "bimol kor": ("বিমল কর", "Bimal Kar"),
    "হেমেন্দ্রকুমার রায়": ("হেমেন্দ্রকুমার রায়", "Hemendrakumar Roy"),
    "hemendrokumar ray": ("হেমেন্দ্রকুমার রায়", "Hemendrakumar Roy"),
    "নারায়ণ সান্যাল": ("নারায়ণ সান্যাল", "Narayan Sanyal"),
    "অনীশ দেব": ("অনীশ দেব", "Anish Deb"),
    "onish deb": ("অনীশ দেব", "Anish Deb"),
    "দেবারতি মুখোপাধ্যায়": ("দেবারতি মুখোপাধ্যায়", "Debarati Mukhopadhyay"),
    "সুকুমারী ভট্টাচার্য": ("সুকুমারী ভট্টাচার্য", "Sukumari Bhattacharji"),
    "জুল ভার্ন": ("জুল ভার্ন", "Jules Verne"),
    "jul bharn": ("জুল ভার্ন", "Jules Verne"),
    "jules verne": ("জুল ভার্ন", "Jules Verne"),
    "অ্যার্জে": ("অ্যার্জে", "Hergé"),
    "আশুতোষ মুখোপাধ্যায়": ("আশুতোষ মুখোপাধ্যায়", "Ashutosh Mukhopadhyay"),
    "ashutosh mukhopadhyay": ("আশুতোষ মুখোপাধ্যায়", "Ashutosh Mukhopadhyay"),
    "নীহাররঞ্জন গুপ্ত": ("নীহাররঞ্জন গুপ্ত", "Niharranjan Gupta"),
    "niharoronjon gupta": ("নীহাররঞ্জন গুপ্ত", "Niharranjan Gupta"),
    "নির্মলেন্দু গুণ": ("নির্মলেন্দু গুণ", "Nirmalendu Goon"),
    "শঙ্খ ঘোষ": ("শঙ্খ ঘোষ", "Sankha Ghosh"),
    "পাঁচকড়ি দে": ("পাঁচকড়ি দে", "Panchkari Dey"),
    "শামসুদ্দীন নওয়াব": ("শামসুদ্দীন নওয়াব", "Shamsuddin Nawab"),
    "ঈশ্বরচন্দ্র বিদ্যাসাগর": ("ঈশ্বরচন্দ্র বিদ্যাসাগর", "Ishwar Chandra Vidyasagar"),
    "ishorochondr biddasagor": ("ঈশ্বরচন্দ্র বিদ্যাসাগর", "Ishwar Chandra Vidyasagar"),
    "জসীম উদ্দীন": ("জসীম উদ্দীন", "Jasimuddin"),
    "জসীমউদ্দীন": ("জসীম উদ্দীন", "Jasimuddin"),
    "প্রফুল্ল রায়": ("প্রফুল্ল রায়", "Prafulla Roy"),
    "লীলা মজুমদার": ("লীলা মজুমদার", "Lila Majumdar"),
    "জীবনানন্দ দাশ": ("জীবনানন্দ দাশ", "Jibanananda Das"),
    "jibanananda das": ("জীবনানন্দ দাশ", "Jibanananda Das"),
    "তারাশঙ্কর বন্দ্যোপাধ্যায়": ("তারাশঙ্কর বন্দ্যোপাধ্যায়", "Tarashankar Bandyopadhyay"),
    "tarashankar bandyopadhyay": ("তারাশঙ্কর বন্দ্যোপাধ্যায়", "Tarashankar Bandyopadhyay"),
    "নিমাই ভট্টাচার্য": ("নিমাই ভট্টাচার্য", "Nimai Bhattacharya"),
    "আগাথা ক্রিস্টি": ("আগাথা ক্রিস্টি", "Agatha Christie"),
    "agatha christie": ("আগাথা ক্রিস্টি", "Agatha Christie"),
    "বার্ট্রান্ড রাসেল": ("বার্ট্রান্ড রাসেল", "Bertrand Russell"),
    "bertrand russell": ("বার্ট্রান্ড রাসেল", "Bertrand Russell"),
    "আনিসুল হক": ("আনিসুল হক", "Anisul Hoque"),
    "anisul hok": ("আনিসুল হক", "Anisul Hoque"),
    "আহমদ ছফা": ("আহমদ ছফা", "Ahmed Sofa"),
    "ahmad chhopha": ("আহমদ ছফা", "Ahmed Sofa"),
    "অতীন বন্দ্যোপাধ্যায়": ("অতীন বন্দ্যোপাধ্যায়", "Atin Bandyopadhyay"),
    "otin bandyopadhyay": ("অতীন বন্দ্যোপাধ্যায়", "Atin Bandyopadhyay"),
    "মানিক বন্দ্যোপাধ্যায়": ("মানিক বন্দ্যোপাধ্যায়", "Manik Bandyopadhyay"),
    "মানিক বন্দ্যোপাধ্যায়": ("মানিক বন্দ্যোপাধ্যায়", "Manik Bandyopadhyay"),
    "বেগম রোকেয়া": ("বেগম রোকেয়া", "Begum Rokeya"),
    "বেগম রোকেয়া": ("বেগম রোকেয়া", "Begum Rokeya"),
    "বেগম রোকেয়া সাখাওয়াত হোসেন": ("বেগম রোকেয়া", "Begum Rokeya"),
    "begom rokeja": ("বেগম রোকেয়া", "Begum Rokeya"),
    "begom rokeja sakhaojat hossain": ("বেগম রোকেয়া", "Begum Rokeya"),
    "অবনীন্দ্রনাথ ঠাকুর": ("অবনীন্দ্রনাথ ঠাকুর", "Abanindranath Tagore"),
    "obonindronath tagore": ("অবনীন্দ্রনাথ ঠাকুর", "Abanindranath Tagore"),
    "রমেশচন্দ্র মজুমদার": ("রমেশচন্দ্র মজুমদার", "Ramesh Chandra Majumdar"),
    "romeshochondr mojumodar": ("রমেশচন্দ্র মজুমদার", "Ramesh Chandra Majumdar"),
    "মাইকেল মধুসূদন দত্ত": ("মাইকেল মধুসূদন দত্ত", "Michael Madhusudan Dutt"),
    "maikel modhusudon dutta": ("মাইকেল মধুসূদন দত্ত", "Michael Madhusudan Dutt"),
    "সুধীন্দ্রনাথ দত্ত": ("সুধীন্দ্রনাথ দত্ত", "Sudhindranath Dutta"),
    "sudhindronath dutta": ("সুধীন্দ্রনাথ দত্ত", "Sudhindranath Dutta"),
    "সুভাষ মুখোপাধ্যায়": ("সুভাষ মুখোপাধ্যায়", "Subhash Mukhopadhyay"),
    "subhash mukhopadhyay": ("সুভাষ মুখোপাধ্যায়", "Subhash Mukhopadhyay"),
    "অচিন্ত্যকুমার সেনগুপ্ত": ("অচিন্ত্যকুমার সেনগুপ্ত", "Achintyakumar Sengupta"),
    "ochinttokumar senogupt": ("অচিন্ত্যকুমার সেনগুপ্ত", "Achintyakumar Sengupta"),
    "জেমস হ্যাডলি চেজ": ("জেমস হ্যাডলি চেজ", "James Hadley Chase"),
    "jemos hyadoli chej": ("জেমস হ্যাডলি চেজ", "James Hadley Chase"),
    "পাওলো কোয়েলহো": ("পাওলো কোয়েলহো", "Paulo Coelho"),
    "paolo kojeloho": ("পাওলো কোয়েলহো", "Paulo Coelho"),
    "paulo coelho": ("পাওলো কোয়েলহো", "Paulo Coelho"),
    "মীর মশাররফ হোসেন": ("মীর মশাররফ হোসেন", "Mir Mosharraf Hossain"),
    "সুকুমার রায়": ("সুকুমার রায়", "Sukumar Ray"),
    "উপেন্দ্রকিশোর রায়চৌধুরী": ("উপেন্দ্রকিশোর রায়চৌধুরী", "Upendrakishore Ray Chowdhury"),
    "নারায়ণ গঙ্গোপাধ্যায়": ("নারায়ণ গঙ্গোপাধ্যায়", "Narayan Gangopadhyay"),
    "শিবরাম চক্রবর্তী": ("শিবরাম চক্রবর্তী", "Shibram Chakraborty"),
    "সৈয়দ ওয়ালীউল্লাহ": ("সৈয়দ ওয়ালীউল্লাহ", "Syed Waliullah"),
    "জহির রায়হান": ("জহির রায়হান", "Zahir Raihan"),
    "শহীদুল্লা কায়সার": ("শহীদুল্লা কায়সার", "Shahidullah Kaiser"),
    "আখতারুজ্জামান ইলিয়াস": ("আখতারুজ্জামান ইলিয়াস", "Akhtaruzzaman Elias"),
    "সেলিনা হোসেন": ("সেলিনা হোসেন", "Selina Hossain"),
    "ইমদাদুল হক মিলন": ("ইমদাদুল হক মিলন", "Imdadul Haq Milan"),
    "প্রেমেন্দ্র মিত্র": ("প্রেমেন্দ্র মিত্র", "Premendra Mitra"),
    "মহাশ্বেতা দেবী": ("মহাশ্বেতা দেবী", "Mahasweta Devi"),
    "শওকত ওসমান": ("শওকত ওসমান", "Shawkat Osman"),
    "হাসান আজিজুল হক": ("হাসান আজিজুল হক", "Hasan Azizul Huq"),
    "জর্জ অরওয়েল": ("জর্জ অরওয়েল", "George Orwell"),
    "george orwell": ("জর্জ অরওয়েল", "George Orwell"),
    "ড. জাকির নায়েক": ("ড. জাকির নায়েক", "Dr. Zakir Naik"),
    "ডা. জাকির নায়েক": ("ড. জাকির নায়েক", "Dr. Zakir Naik"),
    "জাকির নায়েক": ("ড. জাকির নায়েক", "Dr. Zakir Naik"),
    "সাইয়েদ আবুল আ'লা মওদূদী": ("সাইয়েদ আবুল আ'লা মওদূদী", "Syed Abul A'la Maududi"),
    "মাওলানা আশরাফ আলী থানভী": ("মাওলানা আশরাফ আলী থানভী", "Maulana Ashraf Ali Thanwi"),
    "ইবনে কাসীর": ("ইবনে কাসীর", "Ibn Kathir"),
    "ibn kathir": ("ইবনে কাসীর", "Ibn Kathir"),
    "nctb": ("এনসিটিবি", "NCTB"),
    "nctb (জাতীয় শিক্ষাক্রম ও পাঠ্যপুস্তক বোর্ড)": ("এনসিটিবি", "NCTB"),
    "national curriculum and textbook board (nctb)": ("এনসিটিবি", "NCTB"),
    "জাতীয় শিক্ষাক্রম ও পাঠ্যপুস্তক বোর্ড": ("এনসিটিবি", "NCTB"),
    "এনসিটিবি": ("এনসিটিবি", "NCTB"),
}

ROMANIZED_BANGLA_RE = re.compile(
    r"\b(?:"
    r"shrenir|shreni|prathomik|madhyamik|ucchomadhyamik|ibotedaji|ibtedayi|dakhil|"
    r"uponyas|chotogolpo|golpo|kobita|somogro|rochonaboli|rochosomogro|"
    r"khondo|porbo|odhyay|itihas|sahitya|byakoron|obhidhan|shikkha|bigyan|"
    r"onushilon|onushiloni|proshno|somadhan|bishad|pother|shesher|nondito|"
    r"apon|porichoj|porichoy|prothom|dwitij|tritij|choturth|ponchom|shoshth|"
    r"soptom|oshtom|nobom|doshom|kotha|kichhu|gopon|rohosso|tajobid|masala|"
    r"masayel|namaj|janajar|salat|roja|zakat|aqeedah|seerah|sirat|saimum|"
    r"masud\s*rana|misir\s*ali|himu|tin\s*goyenda|shishu|bichitra|amar\s*bangla"
    r")\b",
    re.I,
)

# Series definitions: (canonical series name, regex on title/author/source)
SERIES_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("হিমু সিরিজ", re.compile(r"(?:^|\b| )হিমু(?:র| কে| ও| এবং| সমগ্র| সিরিজ)?|\bHimu\b", re.I)),
    ("মিসির আলি সিরিজ", re.compile(r"মিসির\s*আলি|Misir\s*Ali", re.I)),
    ("শুভ্র সিরিজ", re.compile(r"(?:^|\b| )শুভ্র(?:র| সমগ্র)?|\bShubhro\b", re.I)),
    ("ফেলুদা সিরিজ", re.compile(r"ফেলুদা|প্রদোষচন্দ্র\s*মিত্র|\bFeluda\b", re.I)),
    ("প্রফেসর শঙ্কু সিরিজ", re.compile(r"প্রফেসর\s*শঙ্কু|শঙ্কু\s*সমগ্র|Professor\s*Shonku", re.I)),
    ("ব্যোমকেশ বক্সী সিরিজ", re.compile(r"ব্যোমকেশ|\bByomkesh\b", re.I)),
    ("কাকাবাবু সিরিজ", re.compile(r"কাকাবাবু|\bKakababu\b", re.I)),
    ("কিরীটী রায় সিরিজ", re.compile(r"কিরীটী|কিরিটি|\bKiriti\b", re.I)),
    ("মাসুদ রানা সিরিজ", re.compile(r"মাসুদ\s*রানা|Masud\s*Rana", re.I)),
    ("তিন গোয়েন্দা সিরিজ", re.compile(r"তিন\s*গো[য়েেয়]ন্দা|Tin\s*Goyenda", re.I)),
    ("কুয়াশা সিরিজ", re.compile(r"কুয়াশা\s*[-–—]?\s*[০-৯0-9]|কুয়াশা\s*সিরিজ|\bKuasha\b", re.I)),
    ("সাইমুম সিরিজ", re.compile(r"সাইমুম|Saimum", re.I)),
    ("টিনটিন কমিক্স", re.compile(r"টিনটিন|\bTintin\b", re.I)),
    ("শার্লক হোমস সিরিজ", re.compile(r"শার্লক\s*হোমস|শেরলক\s*হোমস|Sherlock\s*Holmes", re.I)),
    ("টেনিদা সিরিজ", re.compile(r"টেনিদা|\bTenida\b", re.I)),
    ("ঘনাদা সিরিজ", re.compile(r"ঘনাদা|\bGhanada\b", re.I)),
    ("হ্যারি পটার সিরিজ", re.compile(r"হ্যারি\s*পটার|Harry\s*Potter", re.I)),
    ("মাসিক আত-তাহরীক", re.compile(r"at[\-_ ]?tahreek|\btahreek\b|আত-তাহরীক|আত[\s\-]তাহরিক", re.I)),
    ("আল-বিদায়া ওয়ান নিহায়া", re.compile(r"আল[\s\-]*বিদায়া|Al\s*Bidayah", re.I)),
    ("তাফসীর ইবনে কাসীর", re.compile(r"তাফসীর[ে]?র?\s*ইবনে\s*কাস[ীি]র|Tafsir\s*Ibn\s*Kathir", re.I)),
    ("তাফহীমুল কুরআন", re.compile(r"তাফহীমুল\s*কুরআন|তাফহিমুল\s*কোরআন|Tafhimul\s*Quran", re.I)),
    ("ফী যিলালিল কুরআন", re.compile(r"যিলালিল\s*কুরআন|zilalil\s*quran|feejilalilquran", re.I)),
    ("রচনাবলী ও রচনাসমগ্র", re.compile(r"রচনাবলী|রচনাবলি|রচনাসমগ্র|Rochonaboli|Rochonasomogro", re.I)),
]


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s or "").strip()


def canonicalize_author(raw: str, language: str) -> str:
    s = nfc(raw)
    # Strip trailing year bracket like "[2009]" or "(Unknown Author)"
    s = re.sub(r"\s*\[(?:19|20)\d{2}\]\s*$", "", s).strip()
    s = re.sub(r"\s*\((?:Unknown|লেখক অজানা)\)\s*$", "", s, flags=re.I).strip()
    low = s.lower()
    if (
        low in UNKNOWN_AUTHOR_TOKENS
        or re.fullmatch(r"[\W_0-9]+", low)
        or re.search(r"\b(?=[A-Za-z0-9_-]{18,}\b)(?=.*\d)(?=.*[a-z])(?=.*[A-Z])[A-Za-z0-9_-]{18,}\b", s)
        or re.search(r"(?:adobe|acrobat|pdf24|pdffactory|wkhtml|scanfix|hardcopy|sonic\s*pdf|microsoft\s*word|wpdf)", low)
    ):
        return "Unknown"
    if any(k in low for k in ("unknown author", "লেখক অজানা", "various / unknown", "various unknown")):
        return "Unknown"
    hit = AUTHOR_CANONICAL.get(low)
    if hit:
        return hit[0] if language == "Bangla" else hit[1]
    # Also try stripping dots/extra spaces
    low2 = re.sub(r"\s+", " ", low)
    hit = AUTHOR_CANONICAL.get(low2)
    if hit:
        return hit[0] if language == "Bangla" else hit[1]
    return s


BANGLA_ONLY_AUTHORS = {
    "হুমায়ূন আহমেদ", "humayun ahmed", "humajun ahmed",
    "বুদ্ধদেব গুহ", "buddhodeb guh", "buddhadeb guha",
    "বুদ্ধদেব বসু", "buddhodeb basu",
    "কাজী আনোয়ার হোসেন", "kazi anojar hossain", "kazi anwar hossain",
    "সত্যজিৎ রায়", "satyajit ray",
    "শীর্ষেন্দু মুখোপাধ্যায়", "shirshendu mukhopadhyay", "shirshendu mukhaepadhdhaj",
    "সুনীল গঙ্গোপাধ্যায়", "sunil gangopadhyay",
    "সমরেশ বসু", "somoresh basu", "সমরেশ মজুমদার", "somoresh mojumodar", "samaresh majumdar",
    "শরৎচন্দ্র চট্টোপাধ্যায়", "sarat chandra chattopadhyay",
    "বিভূতিভূষণ বন্দ্যোপাধ্যায়", "bibhutibhushan bandyopadhyay",
    "বঙ্কিমচন্দ্র চট্টোপাধ্যায়", "bankim chandra chattopadhyay",
    "তারাশঙ্কর বন্দ্যোপাধ্যায়", "tarashankar bandyopadhyay",
    "মুহম্মদ জাফর ইকবাল", "muhammed zafar iqbal",
    "আবুল আসাদ", "abul asad", "আশাপূর্ণা দেবী", "ashapurna devi",
    "আনিসুল হক", "anisul hok", "হুমায়ুন আজাদ", "humajun ajad",
    "তসলিমা নাসরিন", "tosolima nasorin", "রকিব হাসান", "rokib hasan",
    "শরদিন্দু বন্দ্যোপাধ্যায়", "shorodindu bandyopadhyay",
    "হেমেন্দ্রকুমার রায়", "hemendrokumar ray",
    "সৈয়দ মুজতবা আলী", "soijd mujotoba ali",
    "কাসেম বিন আবুবাকার", "kasem bin abubakar",
    "আহমদ ছফা", "ahmad chhopha",
}


def detect_language(
    title: str,
    author: str = "",
    publication: str = "",
    emb_lang: str = "",
    source_path: str = "",
) -> str:
    t = nfc(title)
    pub = nfc(publication).lower()
    el = nfc(emb_lang).lower()
    auth_low = nfc(author).lower()

    # Explicit NCTB English Version vs Bangla Version
    if re.search(r"\((?:EV|English Version)\)|English Version|English for Today", t, re.I):
        return "English"
    if re.search(r"\((?:BV|Bangla Version)\)", t, re.I) and (BN_RE.search(t) or ROMANIZED_BANGLA_RE.search(t)):
        return "Bangla"

    if BN_RE.search(t):
        if re.search(r"\b(?:dictionary|অভিধান)\b", t, re.I) and LATIN_RE.search(t) and ("english" in t.lower() or "ইংরেজি" in t or "arabic" in t.lower() or "আরবি" in t):
            return "Bilingual"
        return "Bangla"

    if AR_RE.search(t) and len(AR_RE.findall(t)) >= len(LATIN_RE.findall(t)):
        return "Arabic"

    if ROMANIZED_BANGLA_RE.search(t):
        return "Bangla"

    if auth_low in BANGLA_ONLY_AUTHORS and not re.match(
        r"^(?:The|A|An|Selected|Complete|Collected|History\s+of|Biography\s+of|Stories|Poems|Essays|Letters|Tales)\b",
        t, re.I
    ):
        return "Bangla"

    if el in ("bn", "ben", "bengali", "bangla"):
        return "Bangla"
    if el in ("ar", "ara", "arabic"):
        return "Arabic"
    if el in ("ur", "urd", "urdu"):
        return "Urdu"
    if el in ("sa", "san", "sanskrit"):
        return "Sanskrit"

    if any(p in pub for p in ("ebanglalibrary", "kindle bangla", "bdebooks", "বই বিতরন", "মৃণাল", "bongboi", "ইসলামী বই", "ইসলামীক বই")):
        # Check if author is distinctly Bangla or title has Bengali context
        if BN_RE.search(author) or any(w in t.lower() for w in ("bangla", "shishu", "sahitya", "golpo", "uponyas", "islam", "quran", "hadith", "tafsir", "namaz", "dua")):
            return "Bangla"

    if LATIN_RE.search(t):
        return "English"
    if BN_RE.search(author):
        return "Bangla"
    if el.startswith("en"):
        return "English"
    return "Other"


def detect_series(title: str, author: str = "", source_path: str = "", publication: str = "") -> str:
    blob = f"{nfc(title)} {nfc(source_path)}"
    if "nctb" in publication.lower() or "nctb" in blob.lower():
        m = re.search(r"(202[4-7])", blob)
        return f"NCTB Textbooks {m.group(1)}" if m else "NCTB Textbooks"
    for sname, rx in SERIES_PATTERNS:
        if rx.search(blob):
            if sname == "হিমু সিরিজ" and "হিমালয়" in blob and "হুমায়ূন" not in author:
                continue
            if sname == "শুভ্র সিরিজ" and "অভ্র" in blob:
                continue
            return sname
    return ""


def parse_education_target(title: str, orig_path: str, publication: str) -> str | None:
    """Return target subfolder under 03_Education_and_Textbooks/ or None if not an education book."""
    blob = f"{nfc(title)} {nfc(orig_path)} {nfc(publication)}"
    low = blob.lower()
    is_nctb = (
        "nctb" in low or "শ্রেণির" in blob or "shrenir" in low or "01_education" in low
        or "board book" in low
        or (bool(re.search(r"\bclass[\s_\-]*\d{1,2}\b", low)) and any(k in low for k in ("studies", "mathematics", "bangla", "english", "science", "grammar", "religion")))
    )

    # Admission & University & Professional Exams (check before School so HSC Question Banks split cleanly)
    if "01_education" in low and "admission_and_competitive_exams" in low:
        if re.search(r"\b(?:bcs|বিসিএস|bank\s*job|primary\s*assistant|ntrca|চাকরি)\b", low):
            return "03_Education_and_Textbooks/Professional_Exams"
        if re.search(r"\b(?:udvash|উদ্ভাস)\b.*\bhsc\b", low) and "admission" not in low and "মেডিকেল" not in blob and "medical" not in low:
            return "03_Education_and_Textbooks/HSC_Class_11-12"
        return "03_Education_and_Textbooks/Admission"

    if re.search(r"\b(?:bcs|বিসিএস|ntrca|bank\s*recruitment|চাকরির\s*প্রস্তুতি)\b", low):
        return "03_Education_and_Textbooks/Professional_Exams"
    if re.search(r"\b(?:admission|ভর্তি\s*পরীক্ষা|question\s*bank|প্রশ্নব্যাংক)\b", low) and "nctb" not in low:
        return "03_Education_and_Textbooks/Admission"

    # Determine class number (1..12) from Bangla or English/romanized text
    cls_num: int | None = None
    word_map = [
        (r"একাদশ|দ্বাদশ|\b11\b|\b12\b|class[\s_\-]*11|class[\s_\-]*12|\bhsc\b|higher[\s_]*secondary|alim|আলিম", 11),
        (r"দশম|\bdoshom\b|class[\s_\-]*10\b|\b10m\b", 10),
        (r"নবম|\bnobom\b|class[\s_\-]*0?9\b|\b9m\b", 9),
        (r"অষ্টম|৮ম|\boshtom\b|\b8m\b|class[\s_\-]*0?8\b", 8),
        (r"সপ্তম|৭ম|\bsoptom\b|\b7m\b|class[\s_\-]*0?7\b", 7),
        (r"ষষ্ঠ|৬ষ্ঠ|\bshoshth\b|\b6th\b|class[\s_\-]*0?6\b", 6),
        (r"পঞ্চম|৫ম|\bponchom\b|\b5m\b|class[\s_\-]*0?5\b", 5),
        (r"চতুর্থ|৪র্থ|\bchoturth\b|\b4th\b|class[\s_\-]*0?4\b", 4),
        (r"তৃতীয়|তৃতীয়|৩য়|৩য়|\btritij\b|\b3rd\b|class[\s_\-]*0?3\b", 3),
        (r"দ্বিতীয়|দ্বিতীয়|২য়|২য়|\bdwitij\b|\b2nd\b|class[\s_\-]*0?2\b", 2),
        (r"প্রথম|১ম|\bprothom\b|\b1st\b|class[\s_\-]*0?1\b", 1),
    ]
    if is_nctb or "madrasa" in low or "ibteda" in low or "dakhil" in low or "madhyamik" in low or "prathomik" in low:
        for pat, num in word_map:
            if re.search(pat, blob, re.I):
                cls_num = num
                break

        is_madrasa = bool(re.search(r"madrasa|ibotedaji|ibteda|ইবতেদায়ী|ইবতেদায়ী|দাখিল|dakhil|আলিম|alim", blob, re.I))
        if is_madrasa:
            if re.search(r"ibotedaji|ibteda|ইবতেদায়ী|ইবতেদায়ী", blob, re.I) or (cls_num and cls_num <= 5):
                return "03_Education_and_Textbooks/Madrasa/Ibtedayi"
            if re.search(r"alim|আলিম", blob, re.I) or (cls_num and cls_num >= 11):
                return "03_Education_and_Textbooks/Madrasa/Alim"
            if re.search(r"dakhil|দাখিল", blob, re.I) or (cls_num and 6 <= cls_num <= 10):
                return "03_Education_and_Textbooks/Madrasa/Dakhil"
            return "03_Education_and_Textbooks/Madrasa/General"

        if cls_num and 1 <= cls_num <= 10:
            return f"03_Education_and_Textbooks/School/Class_{cls_num:02d}"
        if cls_num == 11:
            return "03_Education_and_Textbooks/HSC_Class_11-12"
        if re.search(r"প্রাক[\s\-]*প্রাথমিক|prak[\s\-]*prathomik|pre[\s\-]*primary", blob, re.I):
            return "03_Education_and_Textbooks/School/Pre_Primary"
        if "কারিগরি" in blob or "vocational" in low or "karigori" in low:
            return "03_Education_and_Textbooks/Other_Textbooks"
        if "01_education" in low:
            return "03_Education_and_Textbooks/School/Other_School"

    if "01_education" in low:
        if "university" in low or "honours" in low or "অনার্স" in blob:
            return "03_Education_and_Textbooks/University"
        return "03_Education_and_Textbooks/Other_Textbooks"
    return None


def map_target_category(
    title: str,
    author: str,
    language: str,
    genres: list[str],
    orig_path: str,
    publication: str,
    series: str,
    clean_leaf_fn,
) -> tuple[str, str, str]:
    """Return (target_folder_path, category, subcategory) in the new architecture."""
    t_low = nfc(title).lower()
    p_low = nfc(orig_path).lower()

    # 1. Education & Textbooks first (fixes the 636 NCTB books in OTHER_EDUCATIONAL_BOOKS!)
    edu = parse_education_target(title, orig_path, publication)
    if edu:
        parts = edu.split("/", 1)
        return edu, parts[0], parts[1]

    # 2. Magazines & Reference (check before Religion so At-Tahreek periodicals go to Magazines)
    if series == "মাসিক আত-তাহরীক" or re.search(r"at[\-_ ]?tahreek|\btahreek\b|আত-তাহরীক|মাসিক\s+আল-আবরার|সাপ্তাহিক\s+আরাফাত", t_low + " " + p_low):
        return "07_Reference_and_Research/Magazines", "07_Reference_and_Research", "Magazines"
    if re.search(r"\b(?:dictionary|অভিধান|ডিকশনারি|lexicon|thesaurus)\b", t_low):
        return "07_Reference_and_Research/Dictionaries", "07_Reference_and_Research", "Dictionaries"
    if re.search(r"\b(?:encyclopedia|বিশ্বকোষ|বাংলাপিডিয়া|banglapedia)\b", t_low):
        return "07_Reference_and_Research/Encyclopedias", "07_Reference_and_Research", "Encyclopedias"
    if re.search(r"\b(?:journal|জার্নাল)\b", t_low):
        return "07_Reference_and_Research/Journals", "07_Reference_and_Research", "Journals"
    if re.search(r"\b(?:magazine|মাসিক|সাপ্তাহিক|পত্রিকা|বার্ষিকী)\b", t_low) or "magazines_and_periodicals" in p_low:
        return "07_Reference_and_Research/Magazines", "07_Reference_and_Research", "Magazines"
    if "general_reference" in p_low:
        return "07_Reference_and_Research/Encyclopedias", "07_Reference_and_Research", "Encyclopedias"

    # 3. Call repo's clean_classifier to infer semantic leaf
    leaf = clean_leaf_fn(
        title=title,
        author=author,
        genres=genres,
        existing_leaf="",
        publication=publication,
        source_path=orig_path,
    )

    # Guard against Islamic-only keywords misrouting secular biographies if clean_classifier matched existing_path
    # 4. Islamic Books
    if leaf.startswith("Religion/Islam/") or ("02_religion" in p_low and '"islam"' in p_low and leaf == "Others and Unclassified/Unclassified"):
        sub = leaf.split("/")[-1] if leaf.startswith("Religion/Islam/") else "Islamic Lifestyle"
        islam_map = {
            "Quran": "কুরআন ও তাফসির",
            "Tafsir": "কুরআন ও তাফসির",
            "Hadith": "হাদিস",
            "Fiqh": "ফিকহ",
            "Islamic Economics": "ফিকহ",
            "Aqeedah": "আকিদা",
            "Islamic Philosophy": "আকিদা",
            "Seerah": "সীরাত",
            "Prophets": "সীরাত",
            "Sahaba": "ইসলামিক ইতিহাস",
            "Islamic History": "ইসলামিক ইতিহাস",
            "Islamic Politics": "ইসলামিক ইতিহাস",
            "Islamic Literature": "ইসলামিক সাহিত্য",
            "Islamic Children Books": "ইসলামিক সাহিত্য",
            "Dua and Prayer": "অন্যান্য",
            "Islamic Lifestyle": "অন্যান্য",
        }
        bn_sub = islam_map.get(sub, "অন্যান্য")
        return f"04_Islamic_Books/{bn_sub}", "04_Islamic_Books", bn_sub

    # 5. English vs Bangla routing
    if language == "English":
        if leaf.startswith("Fiction/") or leaf in ("Literature/Novels", "Literature/Short Stories", "Literature/Poetry", "Literature/Drama", "Literature/Plays", "Literature/Collected Works", "Literature/Humorous Literature"):
            return "02_English_Books/Fiction", "02_English_Books", "Fiction"
        if leaf.startswith("Computer and Technology/") or leaf.startswith("Engineering/"):
            return "02_English_Books/Technology", "02_English_Books", "Technology"
        if leaf.startswith("Science/") or leaf.startswith("Medicine and Health/"):
            return "02_English_Books/Science", "02_English_Books", "Science"
        if leaf.startswith("History/"):
            return "02_English_Books/History", "02_English_Books", "History"
        if leaf.startswith("Philosophy/") or leaf.startswith("Religion/"):
            return "02_English_Books/Philosophy", "02_English_Books", "Philosophy"
        if leaf.startswith("Biography and Autobiography/") or leaf in ("Literature/Autobiography", "Literature/Memoirs"):
            return "02_English_Books/Biography", "02_English_Books", "Biography"
        if leaf != "Others and Unclassified/Unclassified":
            return "02_English_Books/Non_Fiction", "02_English_Books", "Non_Fiction"
        return "02_English_Books/Others", "02_English_Books", "Others"

    # Bangla / Bilingual / Arabic / Sanskrit / Other -> 01_Bangla_Books/ (or Islamic already handled)
    if leaf in ("Fiction/Detective", "Fiction/Thriller", "Fiction/Mystery", "Fiction/Horror", "Fiction/Ghost Stories", "Fiction/Adventure") or series in ("মাসুদ রানা সিরিজ", "তিন গোয়েন্দা সিরিজ", "ফেলুদা সিরিজ", "ব্যোমকেশ বক্সী সিরিজ", "কিরীটী রায় সিরিজ", "কাকাবাবু সিরিজ", "শার্লক হোমস সিরিজ", "কুয়াশা সিরিজ"):
        return "01_Bangla_Books/থ্রিলার, রহস্য ও গোয়েন্দা", "01_Bangla_Books", "থ্রিলার, রহস্য ও গোয়েন্দা"
    if "অনুবাদ" in " ".join(genres) or any(a in nfc(author) for a in ("জুল ভার্ন", "উইলিয়াম শেক্সপিয়ার", "আর্থার কোনান ডয়েল", "আগাথা ক্রিস্টি", "পাওলো কোয়েলহো", "জেমস হ্যাডলি চেজ", "জর্জ অরওয়েল")):
        return "01_Bangla_Books/অনুবাদ ও বিদেশী সাহিত্য", "01_Bangla_Books", "অনুবাদ ও বিদেশী সাহিত্য"
    if leaf in ("Literature/Novels",) or leaf.startswith("Fiction/"):
        return "01_Bangla_Books/উপন্যাস", "01_Bangla_Books", "উপন্যাস"
    if leaf in ("Literature/Short Stories", "Literature/Folk Literature", "Literature/Humorous Literature"):
        return "01_Bangla_Books/গল্প ও ছোটগল্প", "01_Bangla_Books", "গল্প ও ছোটগল্প"
    if leaf in ("Literature/Poetry", "Literature/Rhymes"):
        return "01_Bangla_Books/কবিতা", "01_Bangla_Books", "কবিতা"
    if leaf in ("Literature/Essays", "Literature/Literary Criticism", "Literature/Prose", "Literature/Letters", "Literature/Collected Works"):
        return "01_Bangla_Books/প্রবন্ধ", "01_Bangla_Books", "প্রবন্ধ"
    if leaf in ("Literature/Drama", "Literature/Plays"):
        return "01_Bangla_Books/নাটক", "01_Bangla_Books", "নাটক"
    if leaf.startswith("Biography and Autobiography/") or leaf in ("Literature/Autobiography", "Literature/Memoirs"):
        return "01_Bangla_Books/জীবনী ও আত্মজীবনী", "01_Bangla_Books", "জীবনী ও আত্মজীবনী"
    if leaf.startswith("History/"):
        return "01_Bangla_Books/ইতিহাস", "01_Bangla_Books", "ইতিহাস"
    if leaf.startswith("Science/") or leaf.startswith("Computer and Technology/") or leaf.startswith("Engineering/") or leaf.startswith("Medicine and Health/"):
        return "01_Bangla_Books/বিজ্ঞান ও প্রযুক্তি", "01_Bangla_Books", "বিজ্ঞান ও প্রযুক্তি"
    if leaf.startswith("Children and Young Adult/") or leaf == "Literature/Children's Literature":
        return "01_Bangla_Books/শিশু-কিশোর সাহিত্য", "01_Bangla_Books", "শিশু-কিশোর সাহিত্য"
    if leaf == "Literature/Travel Writing" or leaf.startswith("Travel and Geography/"):
        return "01_Bangla_Books/ভ্রমণ", "01_Bangla_Books", "ভ্রমণ"
    if leaf.startswith("Religion/") or leaf.startswith("Philosophy/"):
        return "01_Bangla_Books/ধর্ম ও দর্শন", "01_Bangla_Books", "ধর্ম ও দর্শন"
    if leaf.startswith("Language and Linguistics/"):
        return "01_Bangla_Books/ভাষা ও ব্যাকরণ", "01_Bangla_Books", "ভাষা ও ব্যাকরণ"

    # Fallbacks from existing Drive top/level-2 folders if clean_classifier couldn't tell
    if '"stories_and_fiction"' in p_low:
        return "01_Bangla_Books/উপন্যাস", "01_Bangla_Books", "উপন্যাস"
    if '"poetry"' in p_low:
        return "01_Bangla_Books/কবিতা", "01_Bangla_Books", "কবিতা"
    if '"essays_and_literature"' in p_low:
        return "01_Bangla_Books/প্রবন্ধ", "01_Bangla_Books", "প্রবন্ধ"
    if '"drama_and_plays"' in p_low:
        return "01_Bangla_Books/নাটক", "01_Bangla_Books", "নাটক"
    if '"biographies_and_autobiographies"' in p_low:
        return "01_Bangla_Books/জীবনী ও আত্মজীবনী", "01_Bangla_Books", "জীবনী ও আত্মজীবনী"
    if '"children_literature"' in p_low:
        return "01_Bangla_Books/শিশু-কিশোর সাহিত্য", "01_Bangla_Books", "শিশু-কিশোর সাহিত্য"
    if '"language_and_grammar"' in p_low:
        return "01_Bangla_Books/ভাষা ও ব্যাকরণ", "01_Bangla_Books", "ভাষা ও ব্যাকরণ"
    if '"other_religions"' in p_low:
        return "01_Bangla_Books/ধর্ম ও দর্শন", "01_Bangla_Books", "ধর্ম ও দর্শন"
    if "04_science_and_technology" in p_low:
        return "01_Bangla_Books/বিজ্ঞান ও প্রযুক্তি", "01_Bangla_Books", "বিজ্ঞান ও প্রযুক্তি"
    if "05_history_and_humanities" in p_low:
        return "01_Bangla_Books/ইতিহাস", "01_Bangla_Books", "ইতিহাস"

    return "01_Bangla_Books/অন্যান্য", "01_Bangla_Books", "অন্যান্য"
