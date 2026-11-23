#!/usr/bin/env python3
"""Collect all books and cover thumbnails from:
  1. https://qawmimadrasa.com/
  2. https://banglakitab.weebly.com/
  3. https://iqrabari.com/কওমি-মাদ্রাসার-সকল-বই-pdf/ (+ Qawmi & Islamic posts)

Uploads everything to Google Drive under:
  Bangladesh-Biggest-eBook-Library / 03_Education_and_Textbooks / Qawmi_Madrasa
arranged by combined Qawmi Madrasa stages (General Education equivalents) and
website categories, preserving exact website book titles.

Also saves every book cover/thumbnail into:
  Qawmi_Madrasa / 00_Covers_&_Thumbnails (বইয়ের কভার ও থাম্বনেইল)
and generates + uploads a comprehensive Category Map & Book Catalog spreadsheet
(.xlsx & .csv) at the root of Qawmi_Madrasa.

Supports both:
- GitHub Actions / headless mode via GDRIVE_OAUTH_JSON (uses library_tools/drive_api.py)
- Local mode via `gdrive` CLI
"""
from __future__ import annotations

import argparse
import base64
import concurrent.futures
import csv
import hashlib
import html as html_lib
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
import pymupdf
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
REPORTS_DIR = ROOT / "reports"
TMP_DIR = ROOT / "tmp_qawmi"
TOOLS_DIR = ROOT / "library_tools"
sys.path.insert(0, str(TOOLS_DIR))

import drive_api as dapi  # noqa: E402

QAWMI_ROOT_ID = "1oACGk9Yf70kBJGRdsNMVPBkFLhZNJ02O"
BASE_URL = "https://qawmimadrasa.com"
BANGLAKITAB_URL = "https://banglakitab.weebly.com"
IQRABARI_URL = "https://iqrabari.com"
IQRABARI_MAIN_PAGE = (
    "https://iqrabari.com/%E0%A6%95%E0%A6%93%E0%A6%AE%E0%A6%BF-"
    "%E0%A6%AE%E0%A6%BE%E0%A6%A6%E0%A7%8D%E0%A6%B0%E0%A6%BE%E0%A6%B8%E0%A6%BE%E0%A6%B0-"
    "%E0%A6%B8%E0%A6%95%E0%A6%B2-%E0%A6%AC%E0%A6%87-pdf/"
)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
BOT_UA = (
    "BangladeshBiggesteBookLibraryBot/1.0 "
    "(+https://github.com/salman-anik/Bangladesh-Biggest-eBook-Library)"
)

FOLDERS_FILE = DATA_DIR / "qawmimadrasa_folders.json"
CATALOG_FILE = DATA_DIR / "qawmimadrasa_catalog.json"
PROGRESS_FILE = DATA_DIR / "qawmimadrasa_progress.json"
SUMMARY_FILE = REPORTS_DIR / "qawmimadrasa_summary.json"
XLSX_NAME = "00_Qawmi_Madrasa_Category_Map_and_Book_Catalog.xlsx"
CSV_NAME = "00_Qawmi_Madrasa_Category_Map_and_Book_Catalog.csv"
COVERS_FOLDER_PATH = "00_Covers_&_Thumbnails (বইয়ের কভার ও থাম্বনেইল)"
MGMT_COVERS_FOLDER_ID = "1QZtIEr8QjA8OSg0WsITp5kgeFOK4HiCj"

GDRIVE_CMD = shutil.which("gdrive") or "gdrive"
LOCK = threading.Lock()
LOCAL_SESSION = threading.local()


class PermanentNotFoundError(Exception):
    """Raised when an upstream file URL permanently returns HTTP 404/410 or is dead."""


# Combined folder hierarchy: Covers + General Education Equivalence Stages + Website Categories
FOLDER_PATHS: list[str] = [
    COVERS_FOLDER_PATH,
    "01_Ibtidaiyah_Primary (Class 1-5)",
    "01_Ibtidaiyah_Primary (Class 1-5)/Taisir_Jamat (তাইসীর জামাত)",
    "01_Ibtidaiyah_Primary (Class 1-5)/Maktab_&_Primary_Books (মকতব ও প্রাথমিক কিতাব)",
    "02_Mutawassitah_Junior_Secondary (Class 6-8)",
    "02_Mutawassitah_Junior_Secondary (Class 6-8)/Mizan_Jamat (মিজান জামাত)",
    "02_Mutawassitah_Junior_Secondary (Class 6-8)/Nahw_Meer_Jamat (নাহুমির জামাত)",
    "02_Mutawassitah_Junior_Secondary (Class 6-8)/Urdu_1st_Year_Al_Aula (درجہ اولی)",
    "02_Mutawassitah_Junior_Secondary (Class 6-8)/Urdu_2nd_Year_Sania (درجہ ثانیہ)",
    "02_Mutawassitah_Junior_Secondary (Class 6-8)/Urdu_3rd_Year_Salesa (درجہ ثالثہ)",
    "03_Sanabiyyah_Aam_SSC_Level (Class 9-10)",
    "03_Sanabiyyah_Aam_SSC_Level (Class 9-10)/Hidayatun_Nahw_Jamat (হেদায়াতুন নাহু জামাত)",
    "03_Sanabiyyah_Aam_SSC_Level (Class 9-10)/Kafia_Jamat (কাফিয়া জামাত)",
    "03_Sanabiyyah_Aam_SSC_Level (Class 9-10)/Urdu_4th_Year_Rabia (درجہ رابعہ)",
    "04_Sanabiyyah_Ulya_HSC_Level (Class 11-12)",
    "04_Sanabiyyah_Ulya_HSC_Level (Class 11-12)/Sharhe_Jami_Jamat (শরহে জামী জামাত)",
    "04_Sanabiyyah_Ulya_HSC_Level (Class 11-12)/Urdu_5th_Year_Khamesa (درجہ خامسہ)",
    "04_Sanabiyyah_Ulya_HSC_Level (Class 11-12)/Urdu_6th_Year_Sadesa (درجہ سادسہ)",
    "05_Fazilat_Bachelor_Level (Degree)",
    "05_Fazilat_Bachelor_Level (Degree)/Jalalain_Jamat (জালালাইন জামাত)",
    "05_Fazilat_Bachelor_Level (Degree)/Mishkat_Jamat (মিশকাত জামাত)",
    "05_Fazilat_Bachelor_Level (Degree)/Urdu_7th_Year_Sabia (درجہ سابعہ)",
    "06_Takmeel_Dawra-e-Hadith_Masters",
    "06_Takmeel_Dawra-e-Hadith_Masters/Dawra-e-Hadith_Bangla (দাওরায়ে হাদিস)",
    "06_Takmeel_Dawra-e-Hadith_Masters/Urdu_8th_Year_Dawra (دورہ حدیث)",
    "07_Madani_Nisab (মাদানী নেসাব)",
    "08_Mantiq_o_Falsafa (منطق و فلسفہ)",
    "09_Tafseer_o_Al-Quran (তাফসীর ও আল-কুরআন)",
    "10_Hadith_o_Sunnah (হাদীস)",
    "11_Fiqh_o_Madhhab (ফিকহ ও মাযহাব)",
    "12_Aqeedah_o_Beliefs (আকাঈদ ও আকিদা)",
    "13_Seerah_o_Biography (সীরাতে রাসূল ﷺ ও জীবনী)",
    "14_History_o_Heritage (ইতিহাস ঐতিহ্য)",
    "15_Dawah_Tabligh_o_Bayan (দাওয়াত, তাবলীগ ও বয়ান)",
    "16_Tasawwuf_Akhlaq_o_Dua (আত্মশুদ্ধি, আখলাক ও দোয়া)",
    "17_Islamic_Life_Literature_o_Misc (ইসলামী জীবন, সাহিত্য ও বিবিধ)",
    "18_Dictionaries_&_Lexicons (অভিধান সম্ভার)",
    "19_Arabic_Reference_Library (আরবী কিতাব সম্ভার)",
]

# Metadata for the Category Map spreadsheet
STAGE_METADATA: dict[str, tuple[str, str, str, str]] = {
    COVERS_FOLDER_PATH: ("00", "Assets", "Cover Thumbnails", "All Book Cover Images & Page-1 Previews"),
    "01_Ibtidaiyah_Primary (Class 1-5)": ("01", "Ibtidaiyah (ابتدائية)", "Primary (Class 1–5)", "ইবতিদায়িয়্যাহ / প্রাথমিক স্তর"),
    "01_Ibtidaiyah_Primary (Class 1-5)/Taisir_Jamat (তাইসীর জামাত)": ("01A", "Ibtidaiyah (ابتدائية)", "Primary (Class 1–5)", "তাইসীর জামাত"),
    "01_Ibtidaiyah_Primary (Class 1-5)/Maktab_&_Primary_Books (মকতব ও প্রাথমিক কিতাব)": ("01B", "Ibtidaiyah (ابتدائية)", "Primary (Class 1–5)", "মকতব, পহেলী, দোসরী, তেছরী, কায়দা"),
    "02_Mutawassitah_Junior_Secondary (Class 6-8)": ("02", "Mutawassitah (متوسطة)", "Junior Secondary (Class 6–8)", "মুতাওয়াসসিতাহ / নিম্ন মাধ্যমিক"),
    "02_Mutawassitah_Junior_Secondary (Class 6-8)/Mizan_Jamat (মিজান জামাত)": ("02A", "Mutawassitah (متوسطة)", "Junior Secondary (Class 6–8)", "মিজান জামাত"),
    "02_Mutawassitah_Junior_Secondary (Class 6-8)/Nahw_Meer_Jamat (নাহুমির জামাত)": ("02B", "Mutawassitah (متوسطة)", "Junior Secondary (Class 6–8)", "নাহবেমীর জামাত"),
    "02_Mutawassitah_Junior_Secondary (Class 6-8)/Urdu_1st_Year_Al_Aula (درجہ اولی)": ("02C", "Mutawassitah (متوسطة)", "Junior Secondary (Class 6–8)", "Al Aula (1st Year) درجہ اولی"),
    "02_Mutawassitah_Junior_Secondary (Class 6-8)/Urdu_2nd_Year_Sania (درجہ ثانیہ)": ("02D", "Mutawassitah (متوسطة)", "Junior Secondary (Class 6–8)", "Sania (2nd Year) درجہ ثانیہ"),
    "02_Mutawassitah_Junior_Secondary (Class 6-8)/Urdu_3rd_Year_Salesa (درجہ ثالثہ)": ("02E", "Mutawassitah (متوسطة)", "Junior Secondary (Class 6–8)", "Salesa (3rd Year) درجہ ثالثہ"),
    "03_Sanabiyyah_Aam_SSC_Level (Class 9-10)": ("03", "Sanabiyyah Aam (ثانوية عامة)", "SSC Level (Class 9–10)", "সানাবিয়্যাহ আম্মাহ / মাধ্যমিক"),
    "03_Sanabiyyah_Aam_SSC_Level (Class 9-10)/Hidayatun_Nahw_Jamat (হেদায়াতুন নাহু জামাত)": ("03A", "Sanabiyyah Aam (ثانوية عامة)", "SSC Level (Class 9–10)", "হেদায়াতুন নাহু জামাত"),
    "03_Sanabiyyah_Aam_SSC_Level (Class 9-10)/Kafia_Jamat (কাফিয়া জামাত)": ("03B", "Sanabiyyah Aam (ثانوية عامة)", "SSC Level (Class 9–10)", "কাফিয়া ও কুদুরী জামাত"),
    "03_Sanabiyyah_Aam_SSC_Level (Class 9-10)/Urdu_4th_Year_Rabia (درجہ رابعہ)": ("03C", "Sanabiyyah Aam (ثانوية عامة)", "SSC Level (Class 9–10)", "Rabia (4th Year) درجہ رابعہ"),
    "04_Sanabiyyah_Ulya_HSC_Level (Class 11-12)": ("04", "Sanabiyyah Ulya / Khasa", "HSC Level (Approx.)", "সানাবিয়্যাহ উলইয়া / উচ্চ মাধ্যমিক"),
    "04_Sanabiyyah_Ulya_HSC_Level (Class 11-12)/Sharhe_Jami_Jamat (শরহে জামী জামাত)": ("04A", "Sanabiyyah Ulya / Khasa", "HSC Level (Approx.)", "শরহে জামী ও শরহে বেকায়া জামাত"),
    "04_Sanabiyyah_Ulya_HSC_Level (Class 11-12)/Urdu_5th_Year_Khamesa (درجہ خامسہ)": ("04B", "Sanabiyyah Ulya / Khasa", "HSC Level (Approx.)", "Khamesa (5th Year) درجہ خامسہ"),
    "04_Sanabiyyah_Ulya_HSC_Level (Class 11-12)/Urdu_6th_Year_Sadesa (درجہ سادسہ)": ("04C", "Sanabiyyah Ulya / Khasa", "HSC Level (Approx.)", "Sadesa (6th Year) درجہ سادسہ"),
    "05_Fazilat_Bachelor_Level (Degree)": ("05", "Fazilat (فضيلة)", "Bachelor's Level (Approx.)", "ফযীলত / স্নাতক সমমান"),
    "05_Fazilat_Bachelor_Level (Degree)/Jalalain_Jamat (জালালাইন জামাত)": ("05A", "Fazilat (فضيلة)", "Bachelor's Level (Approx.)", "জালালাইন জামাত"),
    "05_Fazilat_Bachelor_Level (Degree)/Mishkat_Jamat (মিশকাত জামাত)": ("05B", "Fazilat (فضيلة)", "Bachelor's Level (Approx.)", "মিশকাত জামাত"),
    "05_Fazilat_Bachelor_Level (Degree)/Urdu_7th_Year_Sabia (درجہ سابعہ)": ("05C", "Fazilat (فضيلة)", "Bachelor's Level (Approx.)", "Sabia (7th Year) درجہ سابعہ"),
    "06_Takmeel_Dawra-e-Hadith_Masters": ("06", "Takmeel / Dawra-e-Hadith (تكميل)", "Master's Level (Approx.)", "তাকমীল / দাওরায়ে হাদীস"),
    "06_Takmeel_Dawra-e-Hadith_Masters/Dawra-e-Hadith_Bangla (দাওরায়ে হাদিস)": ("06A", "Takmeel / Dawra-e-Hadith (تكميل)", "Master's Level (Approx.)", "দাওরায়ে হাদিস (সিহাহ সিত্তাহ ও শরাহ)"),
    "06_Takmeel_Dawra-e-Hadith_Masters/Urdu_8th_Year_Dawra (دورہ حدیث)": ("06B", "Takmeel / Dawra-e-Hadith (تكميل)", "Master's Level (Approx.)", "Dora e Hadith (8th Year) دورہ حدیث"),
    "07_Madani_Nisab (মাদানী নেসাব)": ("07", "Special Curriculum", "Madani Nisab", "মাদানী নেসাবের কিতাবসমূহ"),
    "08_Mantiq_o_Falsafa (منطق و فلسفہ)": ("08", "Subject Category", "Logic & Philosophy", "Mantiq o Falsafa, ইসলামী দর্শন"),
    "09_Tafseer_o_Al-Quran (তাফসীর ও আল-কুরআন)": ("09", "Subject Category", "Quran & Tafseer", "তাফসীর, আল-কুরআন, তাজবীদ, কুরআন বিষয়ক"),
    "10_Hadith_o_Sunnah (হাদীস)": ("10", "Subject Category", "Hadith Studies", "হাদীস, হাদীসের ব্যাখ্যাগ্রন্থ, মুয়াত্তা, মুসনাদ"),
    "11_Fiqh_o_Madhhab (ফিকহ ও মাযহাব)": ("11", "Subject Category", "Islamic Jurisprudence", "ফিকহ, ফতোয়া, উসূলুল ফিকহ, মাযহাব"),
    "12_Aqeedah_o_Beliefs (আকাঈদ ও আকিদা)": ("12", "Subject Category", "Creed & Theology", "আকাঈদ, আকিদা ও সমালোচনা, তুলনামূলক ধর্মতত্ত্ব"),
    "13_Seerah_o_Biography (সীরাতে রাসূল ﷺ ও জীবনী)": ("13", "Subject Category", "Seerah & Biographies", "সীরাতে রাসূল (ﷺ), সাহাবা ও আকাবির জীবনী"),
    "14_History_o_Heritage (ইতিহাস ঐতিহ্য)": ("14", "Subject Category", "History & Travel", "ইতিহাস ঐতিহ্য, সফর কাহিনী"),
    "15_Dawah_Tabligh_o_Bayan (দাওয়াত, তাবলীগ ও বয়ান)": ("15", "Subject Category", "Dawah & Sermons", "দাওয়াত ও তাবলীগ, বয়ান ও খুতবা, ফাযায়েলে আমাল"),
    "16_Tasawwuf_Akhlaq_o_Dua (আত্মশুদ্ধি, আখলাক ও দোয়া)": ("16", "Subject Category", "Spirituality & Ethics", "আত্মশুদ্ধি, তাসাউফ, আখলাক, দোয়া ও যিকির"),
    "17_Islamic_Life_Literature_o_Misc (ইসলামী জীবন, সাহিত্য ও বিবিধ)": ("17", "Subject Category", "General & Literature", "ইসলামী জীবন, গল্প-উপন্যাস, গবেষণা, বিবিধ"),
    "18_Dictionaries_&_Lexicons (অভিধান সম্ভার)": ("18", "Reference", "Dictionaries", "অভিধান সম্ভার (বাংলা, আরবী, উর্দু, ইংরেজী)"),
    "19_Arabic_Reference_Library (আরবী কিতাব সম্ভার)": ("19", "Reference", "Arabic Classical Library", "২,৪৪৪ আরবী কিতাব সম্ভার (Wikisource)"),
}

CAT_PRIORITY_LIST: list[tuple[int, str]] = [
    (4626, "01_Ibtidaiyah_Primary (Class 1-5)/Taisir_Jamat (তাইসীর জামাত)"),
    (4632, "02_Mutawassitah_Junior_Secondary (Class 6-8)/Mizan_Jamat (মিজান জামাত)"),
    (4633, "02_Mutawassitah_Junior_Secondary (Class 6-8)/Nahw_Meer_Jamat (নাহুমির জামাত)"),
    (4677, "02_Mutawassitah_Junior_Secondary (Class 6-8)/Urdu_1st_Year_Al_Aula (درجہ اولی)"),
    (4678, "02_Mutawassitah_Junior_Secondary (Class 6-8)/Urdu_2nd_Year_Sania (درجہ ثانیہ)"),
    (4679, "02_Mutawassitah_Junior_Secondary (Class 6-8)/Urdu_3rd_Year_Salesa (درجہ ثالثہ)"),
    (4634, "03_Sanabiyyah_Aam_SSC_Level (Class 9-10)/Hidayatun_Nahw_Jamat (হেদায়াতুন নাহু জামাত)"),
    (4635, "03_Sanabiyyah_Aam_SSC_Level (Class 9-10)/Kafia_Jamat (কাফিয়া জামাত)"),
    (4680, "03_Sanabiyyah_Aam_SSC_Level (Class 9-10)/Urdu_4th_Year_Rabia (درجہ رابعہ)"),
    (4636, "04_Sanabiyyah_Ulya_HSC_Level (Class 11-12)/Sharhe_Jami_Jamat (শরহে জামী জামাত)"),
    (4681, "04_Sanabiyyah_Ulya_HSC_Level (Class 11-12)/Urdu_5th_Year_Khamesa (درجہ خامسہ)"),
    (4682, "04_Sanabiyyah_Ulya_HSC_Level (Class 11-12)/Urdu_6th_Year_Sadesa (درجہ سادسہ)"),
    (4637, "05_Fazilat_Bachelor_Level (Degree)/Jalalain_Jamat (জালালাইন জামাত)"),
    (4639, "05_Fazilat_Bachelor_Level (Degree)/Mishkat_Jamat (মিশকাত জামাত)"),
    (4683, "05_Fazilat_Bachelor_Level (Degree)/Urdu_7th_Year_Sabia (درجہ سابعہ)"),
    (4641, "06_Takmeel_Dawra-e-Hadith_Masters/Dawra-e-Hadith_Bangla (দাওরায়ে হাদিস)"),
    (4684, "06_Takmeel_Dawra-e-Hadith_Masters/Urdu_8th_Year_Dawra (دورہ حدیث)"),
    (4659, "07_Madani_Nisab (মাদানী নেসাব)"),
    (4676, "08_Mantiq_o_Falsafa (منطق و فلسفہ)"),
    (4645, "08_Mantiq_o_Falsafa (منطق و فلسفہ)"),
    (4638, "09_Tafseer_o_Al-Quran (তাফসীর ও আল-কুরআন)"),
    (4631, "09_Tafseer_o_Al-Quran (তাফসীর ও আল-কুরআন)"),
    (4661, "09_Tafseer_o_Al-Quran (তাফসীর ও আল-কুরআন)"),
    (4642, "10_Hadith_o_Sunnah (হাদীস)"),
    (4630, "11_Fiqh_o_Madhhab (ফিকহ ও মাযহাব)"),
    (4664, "11_Fiqh_o_Madhhab (ফিকহ ও মাযহাব)"),
    (4640, "12_Aqeedah_o_Beliefs (আকাঈদ ও আকিদা)"),
    (4663, "12_Aqeedah_o_Beliefs (আকাঈদ ও আকিদা)"),
    (4650, "12_Aqeedah_o_Beliefs (আকাঈদ ও আকিদা)"),
    (4669, "12_Aqeedah_o_Beliefs (আকাঈদ ও আকিদা)"),
    (4628, "13_Seerah_o_Biography (সীরাতে রাসূল ﷺ ও জীবনী)"),
    (4643, "13_Seerah_o_Biography (সীরাতে রাসূল ﷺ ও জীবনী)"),
    (4644, "14_History_o_Heritage (ইতিহাস ঐতিহ্য)"),
    (4654, "14_History_o_Heritage (ইতিহাস ঐতিহ্য)"),
    (4648, "15_Dawah_Tabligh_o_Bayan (দাওয়াত, তাবলীগ ও বয়ান)"),
    (4666, "15_Dawah_Tabligh_o_Bayan (দাওয়াত, তাবলীগ ও বয়ান)"),
    (4649, "15_Dawah_Tabligh_o_Bayan (দাওয়াত, তাবলীগ ও বয়ান)"),
    (4665, "16_Tasawwuf_Akhlaq_o_Dua (আত্মশুদ্ধি, আখলাক ও দোয়া)"),
    (4667, "16_Tasawwuf_Akhlaq_o_Dua (আত্মশুদ্ধি, আখলাক ও দোয়া)"),
    (4670, "16_Tasawwuf_Akhlaq_o_Dua (আত্মশুদ্ধি, আখলাক ও দোয়া)"),
    (4647, "16_Tasawwuf_Akhlaq_o_Dua (আত্মশুদ্ধি, আখলাক ও দোয়া)"),
    (4629, "16_Tasawwuf_Akhlaq_o_Dua (আত্মশুদ্ধি, আখলাক ও দোয়া)"),
    (4646, "16_Tasawwuf_Akhlaq_o_Dua (আত্মশুদ্ধি, আখলাক ও দোয়া)"),
    (4653, "18_Dictionaries_&_Lexicons (অভিধান সম্ভার)"),
    (805, "01_Ibtidaiyah_Primary (Class 1-5)/Maktab_&_Primary_Books (মকতব ও প্রাথমিক কিতাব)"),
    (4656, "17_Islamic_Life_Literature_o_Misc (ইসলামী জীবন, সাহিত্য ও বিবিধ)"),
    (4658, "17_Islamic_Life_Literature_o_Misc (ইসলামী জীবন, সাহিত্য ও বিবিধ)"),
    (4655, "17_Islamic_Life_Literature_o_Misc (ইসলামী জীবন, সাহিত্য ও বিবিধ)"),
    (4652, "17_Islamic_Life_Literature_o_Misc (ইসলামী জীবন, সাহিত্য ও বিবিধ)"),
    (4662, "17_Islamic_Life_Literature_o_Misc (ইসলামী জীবন, সাহিত্য ও বিবিধ)"),
    (4660, "17_Islamic_Life_Literature_o_Misc (ইসলামী জীবন, সাহিত্য ও বিবিধ)"),
    (4657, "17_Islamic_Life_Literature_o_Misc (ইসলামী জীবন, সাহিত্য ও বিবিধ)"),
    (4668, "17_Islamic_Life_Literature_o_Misc (ইসলামী জীবন, সাহিত্য ও বিবিধ)"),
    (4651, "17_Islamic_Life_Literature_o_Misc (ইসলামী জীবন, সাহিত্য ও বিবিধ)"),
    (4675, "17_Islamic_Life_Literature_o_Misc (ইসলামী জীবন, সাহিত্য ও বিবিধ)"),
    (4627, "17_Islamic_Life_Literature_o_Misc (ইসলামী জীবন, সাহিত্য ও বিবিধ)"),
    (4674, "17_Islamic_Life_Literature_o_Misc (ইসলামী জীবন, সাহিত্য ও বিবিধ)"),
]
CAT_PRIORITY_DICT = dict(CAT_PRIORITY_LIST)
CAT_PRIORITY_RANK = {cid: idx for idx, (cid, _) in enumerate(CAT_PRIORITY_LIST)}

PAGE12812_HEADING_MAP: list[tuple[str, str]] = [
    ("তাইসীর", "01_Ibtidaiyah_Primary (Class 1-5)/Taisir_Jamat (তাইসীর জামাত)"),
    ("মীযান", "02_Mutawassitah_Junior_Secondary (Class 6-8)/Mizan_Jamat (মিজান জামাত)"),
    ("নাহবেমীর", "02_Mutawassitah_Junior_Secondary (Class 6-8)/Nahw_Meer_Jamat (নাহুমির জামাত)"),
    ("হেদায়াতুন নাহু", "03_Sanabiyyah_Aam_SSC_Level (Class 9-10)/Hidayatun_Nahw_Jamat (হেদায়াতুন নাহু জামাত)"),
    ("কাফিয়া", "03_Sanabiyyah_Aam_SSC_Level (Class 9-10)/Kafia_Jamat (কাফিয়া জামাত)"),
    ("শরহে জামী", "04_Sanabiyyah_Ulya_HSC_Level (Class 11-12)/Sharhe_Jami_Jamat (শরহে জামী জামাত)"),
    ("জালালাইন", "05_Fazilat_Bachelor_Level (Degree)/Jalalain_Jamat (জালালাইন জামাত)"),
    ("মেশকাত", "05_Fazilat_Bachelor_Level (Degree)/Mishkat_Jamat (মিশকাত জামাত)"),
    ("দাওরায়ে", "06_Takmeel_Dawra-e-Hadith_Masters/Dawra-e-Hadith_Bangla (দাওরায়ে হাদিস)"),
]


def get_session() -> requests.Session:
    s = getattr(LOCAL_SESSION, "session", None)
    if s is None:
        s = requests.Session()
        s.headers.update({"User-Agent": UA})
        LOCAL_SESSION.session = s
    return s


def has_oauth_env() -> bool:
    return bool(os.environ.get("GDRIVE_OAUTH_JSON", "").strip())


def _resolve_gdrive_prefix() -> list[str]:
    cmd_path = shutil.which("gdrive") or "gdrive"
    if os.name == "nt" and cmd_path.lower().endswith((".cmd", ".bat")) and Path(cmd_path).exists():
        try:
            txt = Path(cmd_path).read_text(encoding="utf-8", errors="replace").strip()
            m = re.match(r'^@"([^"]+)"\s+(.*?)\s+%\*\s*$', txt)
            if m:
                return [m.group(1), *m.group(2).split()]
        except Exception:
            pass
    return [cmd_path]


GDRIVE_PREFIX = _resolve_gdrive_prefix()


def run_gdrive_cli(args: list[str], timeout: int = 120) -> str:
    res = subprocess.run(
        [*GDRIVE_PREFIX, *args],
        shell=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if res.returncode != 0:
        raise RuntimeError(f"gdrive {' '.join(args)} failed: {res.stderr or res.stdout}")
    return res.stdout


def drive_list_children(folder_id: str) -> list[dict[str, Any]]:
    if has_oauth_env():
        q = f"'{folder_id}' in parents and trashed = false"
        return list(dapi.list_all(q=q, fields="id,name,mimeType,size"))
    out = run_gdrive_cli(["readonly", "ls", folder_id, "--max", "0", "--json"], timeout=120)
    return json.loads(out or "[]")


def drive_mkdir(name: str, parent_id: str) -> str:
    if has_oauth_env():
        res = dapi.mkdir(name, parent_id)
        return res["id"]
    out = run_gdrive_cli(["mutate", "mkdir", name, "--parent", parent_id], timeout=60)
    m = re.search(r"\(ID:\s*([A-Za-z0-9_-]+)\)", out)
    if not m:
        raise RuntimeError(f"Could not parse mkdir output: {out}")
    return m.group(1)


def drive_upload(local_path: Path, name: str, parent_id: str, mime_type: str = "application/pdf") -> str:
    if has_oauth_env():
        res = dapi.upload_resumable(local_path, name, parent_id, mime_type=mime_type)
        return res["id"]
    upload_path = local_path
    if local_path.name != name:
        renamed = local_path.parent / name
        local_path.rename(renamed)
        upload_path = renamed
    out = run_gdrive_cli(["mutate", "upload", str(upload_path), "--parent", parent_id], timeout=600)
    m = re.search(r"\(ID:\s*([A-Za-z0-9_-]+)\)", out)
    if not m:
        raise RuntimeError(f"Could not parse upload output: {out}")
    return m.group(1)


def drive_update_or_upload(local_path: Path, name: str, parent_id: str, mime_type: str) -> str:
    children = drive_list_children(parent_id)
    for ch in children:
        if ch.get("name") == name and ch.get("mimeType") != "application/vnd.google-apps.folder":
            fid = ch["id"]
            if has_oauth_env():
                dapi.update_media(fid, local_path, mime_type=mime_type)
            else:
                run_gdrive_cli(["mutate", "update", fid, str(local_path)], timeout=300)
            return fid
    return drive_upload(local_path, name, parent_id, mime_type=mime_type)


def drive_copy(src_id: str, name: str, parent_id: str) -> str:
    if has_oauth_env():
        try:
            res = dapi.request(
                "POST",
                f"/files/{src_id}/copy",
                {"supportsAllDrives": "true", "fields": "id,name"},
                body={"name": name, "parents": [parent_id]},
            )
            return res["id"]
        except RuntimeError as e:
            msg = str(e)
            if "404" in msg or "File not found" in msg:
                raise PermanentNotFoundError(f"Drive file not found: {src_id}") from None
            tmp_path = TMP_DIR / f"copy_{src_id}.pdf"
            TMP_DIR.mkdir(parents=True, exist_ok=True)
            try:
                raw = dapi.download_full(src_id)
                tmp_path.write_bytes(raw)
                return drive_upload(tmp_path, name, parent_id)
            except RuntimeError as e2:
                if "404" in str(e2) or "403" in str(e2):
                    raise PermanentNotFoundError(f"Drive file inaccessible: {src_id} ({e2})") from None
                raise
            finally:
                tmp_path.unlink(missing_ok=True)
    tmp_path = TMP_DIR / f"copy_{src_id}.pdf"
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    try:
        try:
            run_gdrive_cli(["readonly", "download", src_id, "--output", str(tmp_path)], timeout=300)
        except RuntimeError as e:
            if "404" in str(e) or "not found" in str(e).lower() or "403" in str(e):
                raise PermanentNotFoundError(f"Drive file inaccessible: {src_id} ({e})") from None
            raise
        return drive_upload(tmp_path, name, parent_id)
    finally:
        tmp_path.unlink(missing_ok=True)


def sanitize_filename(raw: str, max_len: int = 160) -> str:
    s = html_lib.unescape(raw or "").strip()
    s = re.sub(r'[<>:"/\\|?*\r\n\t\x00-\x1f\u200b]+', " ", s)
    s = re.sub(r"\s+", " ", s).strip().rstrip(".")
    if len(s) > max_len:
        s = s[:max_len].strip()
    return s or "Untitled_Book"


def clean_iqrabari_title(raw: str) -> str:
    s = html_lib.unescape(raw or "").strip()
    s = re.sub(r"^[↪️🔽►•\-\s]+", "", s)
    s = re.sub(r"^(?:ডাউনলোড\s*করুন\s*[ঃ:]?\s*|ডাউনলোড\s*[ঃ:]\s*)", "", s)
    s = re.sub(r"\s+pdf\s*download\s*$", "", s, flags=re.I)
    s = re.sub(r"\s+download\s*$", "", s, flags=re.I)
    s = re.sub(r"\s+pdf\s*$", "", s, flags=re.I)
    return sanitize_filename(s)


def clean_volume_label(raw: str) -> str:
    s = html_lib.unescape(raw or "").strip()
    s = re.sub(r"^\d+\.\s*", "", s)
    s = re.sub(r"\.pdf$", "", s, flags=re.I)
    s = re.sub(r"-[a-z0-9]{5,7}$", "", s, flags=re.I)
    s = s.replace("_", " ").strip(" -.")
    return sanitize_filename(s, max_len=80)


def ensure_folders() -> dict[str, str]:
    """Create or reconcile the complete folder tree under QAWMI_ROOT_ID."""
    folders: dict[str, str] = {}
    if FOLDERS_FILE.exists():
        folders = json.loads(FOLDERS_FILE.read_text(encoding="utf-8"))

    children_cache: dict[str, dict[str, str]] = {}

    def get_children_map(pid: str) -> dict[str, str]:
        if pid not in children_cache:
            kids = drive_list_children(pid)
            children_cache[pid] = {
                k["name"]: k["id"]
                for k in kids
                if k.get("mimeType") == "application/vnd.google-apps.folder"
            }
        return children_cache[pid]

    folders[COVERS_FOLDER_PATH] = MGMT_COVERS_FOLDER_ID

    for rel_path in FOLDER_PATHS:
        if rel_path == COVERS_FOLDER_PATH:
            folders[rel_path] = MGMT_COVERS_FOLDER_ID
            continue
        parts = rel_path.split("/")
        cur_parent = QAWMI_ROOT_ID
        acc_parts: list[str] = []
        for part in parts:
            acc_parts.append(part)
            acc_path = "/".join(acc_parts)
            if acc_path in folders and folders[acc_path]:
                cur_parent = folders[acc_path]
                continue
            cmap = get_children_map(cur_parent)
            if part in cmap:
                fid = cmap[part]
            else:
                fid = drive_mkdir(part, cur_parent)
                cmap[part] = fid
            folders[acc_path] = fid
            cur_parent = fid

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    FOLDERS_FILE.write_text(json.dumps(folders, ensure_ascii=False, indent=2), encoding="utf-8")
    return folders


def map_keywords_to_folder(title: str, context_hint: str = "") -> str:
    text = f"{title} {context_hint}".lower()
    if any(k in text for k in ("তাইসীর", "taisir", "পহেলী", "দোসরী", "তেছরী", "কায়দা", "নূরানী", "নুজহাতুল", "বেহেশতী গাওহার", "তালীমুল ইসলাম", "তালিমুল ইসলাম")):
        if any(k in text for k in ("তাইসীর", "taisir")):
            return "01_Ibtidaiyah_Primary (Class 1-5)/Taisir_Jamat (তাইসীর জামাত)"
        return "01_Ibtidaiyah_Primary (Class 1-5)/Maktab_&_Primary_Books (মকতব ও প্রাথমিক কিতাব)"
    if any(k in text for k in ("মিজান", "মীযান", "mizan", "জামালুল কুরআন", "পান্দে নামা", "করীমা", "কারীমা", "বাকুরাতুল", "মুনশায়িব", "ছফওয়াতুল")):
        return "02_Mutawassitah_Junior_Secondary (Class 6-8)/Mizan_Jamat (মিজান জামাত)"
    if any(k in text for k in ("নাহবেমীর", "নাহুমির", "nahw", "রওজাতুল আদব", "ইলমুস সরফ", "এসো সরফ", "সরফ")):
        return "02_Mutawassitah_Junior_Secondary (Class 6-8)/Nahw_Meer_Jamat (নাহুমির জামাত)"
    if any(k in text for k in ("হেদায়াতুন্নাহু", "হেদায়াতুন নাহু", "হেদায়াতুন নাহু", "hidayatun", "কালয়ূবী", "কুদুরী", "মুখতাসারুল কুদুরী", "দুরুসুল বালাগাত")):
        if any(k in text for k in ("কুদুরী", "কাফিয়া", "কাফিয়া", "দুরুসুল বালাগাত", "মিরকাত", "উসুলুশ শাশী", "kafia")):
            return "03_Sanabiyyah_Aam_SSC_Level (Class 9-10)/Kafia_Jamat (কাফিয়া জামাত)"
        return "03_Sanabiyyah_Aam_SSC_Level (Class 9-10)/Hidayatun_Nahw_Jamat (হেদায়াতুন নাহু জামাত)"
    if any(k in text for k in ("কাফিয়া", "কাফিয়া", "kafia")):
        return "03_Sanabiyyah_Aam_SSC_Level (Class 9-10)/Kafia_Jamat (কাফিয়া জামাত)"
    if any(k in text for k in ("শরহে জামী", "শরহে বেকায়া", "শরহে বেকায়া", "sharhe", "নুরুল আনওয়ার")):
        return "04_Sanabiyyah_Ulya_HSC_Level (Class 11-12)/Sharhe_Jami_Jamat (শরহে জামী জামাত)"
    if any(k in text for k in ("জালালাইন", "jalalain")):
        return "05_Fazilat_Bachelor_Level (Degree)/Jalalain_Jamat (জালালাইন জামাত)"
    if any(k in text for k in ("মিশকাত", "মেশকাত", "mishkat", "হিদায়া", "হেদায়া", "hidaya")):
        return "05_Fazilat_Bachelor_Level (Degree)/Mishkat_Jamat (মিশকাত জামাত)"
    if any(k in text for k in ("দাওরা", "dawra", "বুখারী", "বুখারি", "bukhari", "মুসলিম শরীফ", "তিরমিযী", "তিরমিজি", "tirmizi", "আবু দাউদ", "আবী দাঊদ", "নাসাঈ", "ইবনে মাজাহ", "তাহাভী", "মুয়াত্তা", "মুয়াত্তা", "মুসনাদে আহমাদ")):
        return "06_Takmeel_Dawra-e-Hadith_Masters/Dawra-e-Hadith_Bangla (দাওরায়ে হাদিস)"
    if any(k in text for k in ("মাদানী নেসাব", "এসো কোরআন শিখি", "এসো কুরআন শিখি", "এসো আরবী শিখি", "কাসাসুন নাবিয়্যিন", "আত-তারিকু ইলাল ইনশা")):
        return "07_Madani_Nisab (মাদানী নেসাব)"
    if any(k in text for k in ("অভিধান", "লুগাত", "শব্দভাণ্ডার", "ovidan", "dictionary", "vocabulary", "শব্দার্থে আল কোরআন")):
        return "18_Dictionaries_&_Lexicons (অভিধান সম্ভার)"
    if any(k in text for k in ("তাফসীর", "tafsir", "কোরআন", "কুরআন", "quran", "তাজবীদ", "tajweed", "মারেফুল", "ইবনে কাসীর", "ইবনে কাছীর", "শানে নুযূল")):
        return "09_Tafseer_o_Al-Quran (তাফসীর ও আল-কুরআন)"
    if any(k in text for k in ("হাদীস", "হাদিস", "hadith", "রিয়াযুস সালেহীন", "আদাবুল মুফরাদ", "হাদিসে কুদসি")):
        return "10_Hadith_o_Sunnah (হাদীস)"
    if any(k in text for k in ("ফিকহ", "fiqah", "fiqh", "ফতোয়া", "ইফতা", "বেহেশতী জেওর", "মাসআলা", "মাসায়েল", "নামায", "পর্দা")):
        return "11_Fiqh_o_Madhhab (ফিকহ ও মাযহাব)"
    if any(k in text for k in ("আকিদা", "আকীদা", "আকাঈদ", "akida", "তাহাবী")):
        return "12_Aqeedah_o_Beliefs (আকাঈদ ও আকিদা)"
    if any(k in text for k in ("সীরাত", "জীবনী", "সাহাবা", "কাসাসুল", "biography", "নবী", "ওমর")):
        return "13_Seerah_o_Biography (সীরাতে রাসূল ﷺ ও জীবনী)"
    if any(k in text for k in ("ইতিহাস", "তারিখুল", "সফর")):
        return "14_History_o_Heritage (ইতিহাস ঐতিহ্য)"
    if any(k in text for k in ("দাওয়াত", "তাবলীগ", "ফাযায়েলে", "মুন্তাখাব", "বয়ান", "ওয়াজ", "খুতবা", "বক্তৃতা", "dawat", "fazael", "montakhab")):
        return "15_Dawah_Tabligh_o_Bayan (দাওয়াত, তাবলীগ ও বয়ান)"
    if any(k in text for k in ("দোয়া", "যিকির", "তাসাউফ", "আত্মশুদ্ধি", "আখলাক", "duaa", "spirituality")):
        return "16_Tasawwuf_Akhlaq_o_Dua (আত্মশুদ্ধি, আখলাক ও দোয়া)"
    return "17_Islamic_Life_Literature_o_Misc (ইসলামী জীবন, সাহিত্য ও বিবিধ)"


def map_product_to_folder(title: str, cat_ids: list[int]) -> str:
    best_cid = None
    best_rank = 10**9
    for cid in cat_ids:
        rank = CAT_PRIORITY_RANK.get(cid)
        if rank is not None and rank < best_rank:
            best_rank = rank
            best_cid = cid
    if best_cid is not None:
        return CAT_PRIORITY_DICT[best_cid]
    return map_keywords_to_folder(title)


def map_prefix_to_folder(filename_or_title: str) -> str:
    low = filename_or_title.lower()
    if re.match(r"^t[-_]", low):
        return "01_Ibtidaiyah_Primary (Class 1-5)/Taisir_Jamat (তাইসীর জামাত)"
    if re.match(r"^m[-_]", low):
        return "02_Mutawassitah_Junior_Secondary (Class 6-8)/Mizan_Jamat (মিজান জামাত)"
    if re.match(r"^n[-_]", low):
        return "02_Mutawassitah_Junior_Secondary (Class 6-8)/Nahw_Meer_Jamat (নাহুমির জামাত)"
    if re.match(r"^h[-_]", low):
        return "03_Sanabiyyah_Aam_SSC_Level (Class 9-10)/Hidayatun_Nahw_Jamat (হেদায়াতুন নাহু জামাত)"
    if re.match(r"^k[-_]", low):
        return "03_Sanabiyyah_Aam_SSC_Level (Class 9-10)/Kafia_Jamat (কাফিয়া জামাত)"
    if re.match(r"^s[-_]", low):
        return "04_Sanabiyyah_Ulya_HSC_Level (Class 11-12)/Sharhe_Jami_Jamat (শরহে জামী জামাত)"
    if re.match(r"^j[-_]", low):
        return "05_Fazilat_Bachelor_Level (Degree)/Jalalain_Jamat (জালালাইন জামাত)"
    if re.match(r"^mk[-_]", low):
        return "05_Fazilat_Bachelor_Level (Degree)/Mishkat_Jamat (মিশকাত জামাত)"
    if re.match(r"^d[-_]", low):
        return "06_Takmeel_Dawra-e-Hadith_Masters/Dawra-e-Hadith_Bangla (দাওরায়ে হাদিস)"
    return map_keywords_to_folder(filename_or_title)


def fetch_wp_paginated(base_site: str, endpoint: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    sess = get_session()
    items: list[dict[str, Any]] = []
    page = 1
    while True:
        q = {**params, "per_page": 100, "page": page}
        url = f"{base_site}/wp-json/wp/v2/{endpoint}?{urllib.parse.urlencode(q)}"
        for attempt in range(4):
            try:
                r = sess.get(url, timeout=40)
                if r.status_code == 400 and "rest_post_invalid_page_number" in r.text:
                    return items
                r.raise_for_status()
                batch = r.json()
                total_pages = int(r.headers.get("X-WP-TotalPages", "1"))
                items.extend(batch)
                if page >= total_pages or not batch:
                    return items
                page += 1
                break
            except Exception:
                if attempt == 3:
                    raise
                time.sleep(2 * (attempt + 1))
    return items


def norm_bn_key(s: str) -> str:
    return re.sub(r"[\s\u200b\u200c\u200d’'`\".,_()\[\]-]+", "", (s or "").lower())


def crawl_banglakitab(seen_urls: set[str]) -> list[dict[str, Any]]:
    print("Crawling banglakitab.weebly.com (sitemap + Archive.org collection)...", flush=True)
    sess = get_session()
    out: list[dict[str, Any]] = []
    try:
        r_sm = sess.get(f"{BANGLAKITAB_URL}/sitemap.xml", timeout=20)
        root = ET.fromstring(r_sm.content)
        locs = [el.text.replace("http://", "https://") for el in root.iter() if el.tag.endswith("loc")]
    except Exception as e:
        print(f"  Warning reading banglakitab sitemap: {e}", flush=True)
        return out

    skip_domains = ("facebook.com", "twitter.com", "youtube.com", "archive.org/details/")

    def scan_page(page_url: str) -> list[dict[str, Any]]:
        res_items: list[dict[str, Any]] = []
        try:
            r = sess.get(page_url, timeout=20)
            soup = BeautifulSoup(r.text, "html.parser")
            content = soup.find(id="wsite-content") or soup.body or soup
            slug = page_url.split("weebly.com")[-1]
            # First scan leaf multicol blocks to keep title + cover paired accurately
            blocks = [
                td for td in content.find_all("td", class_="wsite-multicol-col")
                if not td.find("td", class_="wsite-multicol-col")
            ]
            processed_hrefs: set[str] = set()

            def extract_block(container: Any, is_leaf_col: bool) -> None:
                block_text = container.get_text("\n", strip=True) if is_leaf_col else ""
                m_name = re.search(r"(?:নাম|বই)\s*[ঃ:]\s*([^\n\r]+)", block_text)
                block_book_name = ""
                if m_name:
                    block_book_name = re.split(r"(?:বিষয়|বিষয়|লেখক|অনুবাদক|প্রকাশনী|সাইজ|পৃষ্ঠা)\s*[ঃ:]", m_name.group(1))[0].strip()
                elif is_leaf_col and block_text:
                    first_line = block_text.split("\n")[0].strip()
                    if 3 < len(first_line) < 90 and not any(k in first_line for k in ("ডাউনলোড", "Download")):
                        block_book_name = first_line

                imgs = [img.get("src") for img in container.find_all("img") if img.get("src")]
                col_cover = ""
                for im in imgs:
                    if "/uploads/" in im:
                        col_cover = urllib.parse.urljoin(BANGLAKITAB_URL, im)
                        break

                for a in container.find_all("a", href=True):
                    href = a["href"].strip()
                    if not href or href in processed_hrefs or href.startswith("#") or href.startswith("javascript:"):
                        continue
                    if any(sd in href.lower() for sd in skip_domains):
                        continue
                    is_internal = href.startswith("/") or "banglakitab.weebly.com" in href
                    if is_internal and not href.lower().endswith((".pdf", ".zip", ".rar")):
                        continue
                    if not any(k in href.lower() for k in ("dropbox.com", "archive.org", "drive.google", "bit.ly", "goo.gl", ".pdf", ".zip")):
                        continue

                    processed_hrefs.add(href)
                    if href in seen_urls:
                        continue
                    seen_urls.add(href)

                    a_text = a.get_text(" ", strip=True)
                    img_inside = a.find("img")
                    cover_url = col_cover
                    if img_inside and img_inside.get("src"):
                        cover_url = urllib.parse.urljoin(BANGLAKITAB_URL, img_inside["src"])

                    # Derive clean title
                    generic = {"ডাউনলোড", "ডাউনলোড করুন", "download", "download from dropbox server", "pdf download", "অনলাইনে পড়ুন ডাউনলোড করুন", "সরাসরি সার্ভার থেকে ডাউনলোড করুন", "ফাইল আকারে সবগুলো বই একসাথে ডাউনলোড করুন", ""}
                    low_t = re.sub(r"\s+", " ", a_text).strip().lower()
                    if block_book_name:
                        if low_t in generic or low_t in block_book_name.lower():
                            title = block_book_name
                        elif any(v in a_text for v in ("খন্ড", "খণ্ড", "part", "vol")) and len(a_text) < 35:
                            title = f"{block_book_name} — {a_text}"
                        else:
                            title = a_text if len(a_text) > len(block_book_name) else f"{block_book_name} ({a_text})"
                    elif low_t not in generic:
                        title = a_text
                    else:
                        # Fallback to filename from URL or slug
                        fname = Path(urllib.parse.unquote(urllib.parse.urlparse(href).path)).stem
                        title = fname.replace("-", " ").replace("_", " ") if len(fname) > 4 else f"banglakitab_{slug.strip('/')}"

                    folder = map_keywords_to_folder(title, slug)
                    uhash = hashlib.md5(href.encode("utf-8")).hexdigest()[:12]
                    res_items.append({
                        "key": f"bk_{uhash}",
                        "kind": "external_url",
                        "source_site": "banglakitab.weebly.com",
                        "title": sanitize_filename(title),
                        "url": href,
                        "page_url": page_url,
                        "cover_url": cover_url,
                        "folder": folder,
                    })

            for col in blocks:
                extract_block(col, is_leaf_col=True)
            extract_block(content, is_leaf_col=False)
        except Exception:
            pass
        return res_items

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for batch in ex.map(scan_page, locs):
            out.extend(batch)

    # Also check owner's Archive.org item (138 PDFs) for any missing PDFs
    try:
        meta_url = "https://archive.org/metadata/skype-id-azharmea-website-www.eelm.weebly.com"
        rm = sess.get(meta_url, timeout=45).json()
        ia_added = 0
        for f in rm.get("files", []):
            name = f.get("name") or ""
            if not name.lower().endswith(".pdf"):
                continue
            dl_url = f"https://archive.org/download/skype-id-azharmea-website-www.eelm.weebly.com/{urllib.parse.quote(name)}"
            if dl_url in seen_urls:
                continue
            seen_urls.add(dl_url)
            stem = Path(name).stem.replace("_", " ").replace("-", " ").strip()
            uhash = hashlib.md5(dl_url.encode("utf-8")).hexdigest()[:12]
            out.append({
                "key": f"bk_ia_{uhash}",
                "kind": "direct_pdf",
                "source_site": "banglakitab.weebly.com",
                "title": sanitize_filename(stem),
                "url": dl_url,
                "referer": "https://banglakitab.weebly.com/qaumi-kitab.html",
                "cover_url": "",
                "folder": map_keywords_to_folder(stem, "qaumi-kitab"),
            })
            ia_added += 1
        print(f"  banglakitab.weebly.com: {len(out) - ia_added} page links + {ia_added} Archive.org PDFs.", flush=True)
    except Exception as e:
        print(f"  Warning Archive.org metadata: {e}", flush=True)

    return out


def crawl_iqrabari(seen_urls: set[str]) -> list[dict[str, Any]]:
    print("Crawling iqrabari.com (Qawmi Madrasa + Islamic categories)...", flush=True)
    sess = get_session()
    out: list[dict[str, Any]] = []
    seen_drive_ids: set[str] = {u for u in seen_urls if not u.startswith("http")}

    pages_to_scan: list[tuple[str, str, str, str]] = []  # (url, title_hint, cover_url, context_hint)
    try:
        posts = fetch_wp_paginated(IQRABARI_URL, "posts", {"categories": "73,1071"})
        for p in posts:
            og = (p.get("yoast_head_json") or {}).get("og_image") or []
            cover = og[0].get("url", "") if og else ""
            t = html_lib.unescape((p.get("title") or {}).get("rendered") or "")
            pages_to_scan.append((p["link"], t, cover, t))
    except Exception as e:
        print(f"  Warning fetching iqrabari WP API: {e}", flush=True)

    # Also ensure main page and any subpages linked from it are included
    known_urls = {u for u, _, _, _ in pages_to_scan}
    if IQRABARI_MAIN_PAGE not in known_urls:
        pages_to_scan.insert(0, (IQRABARI_MAIN_PAGE, "কওমি মাদ্রাসার সকল বই", "", "কওমি মাদ্রাসা"))
        known_urls.add(IQRABARI_MAIN_PAGE)

    try:
        rm = sess.get(IQRABARI_MAIN_PAGE, timeout=20)
        sm = BeautifulSoup(rm.text, "html.parser")
        em = sm.find(class_="entry-content") or sm
        for a in em.find_all("a", href=True):
            h = a["href"].split("#")[0]
            if "iqrabari.com/" in h and h not in known_urls and "/category/" not in h and "/author/" not in h:
                t = a.get_text(" ", strip=True)
                known_urls.add(h)
                pages_to_scan.append((h, t, "", t))
    except Exception:
        pass

    for purl, ptitle, pcover, ctx in pages_to_scan:
        try:
            rp = sess.get(purl, timeout=20)
            sp = BeautifulSoup(rp.text, "html.parser")
            ec = sp.find(class_="entry-content") or sp
            if not pcover:
                img = ec.find("img")
                if img and img.get("src") and not img["src"].startswith("data:"):
                    pcover = img["src"]
            for a in ec.find_all("a", href=True):
                h = a["href"].strip()
                lt = clean_iqrabari_title(a.get_text(" ", strip=True))
                if "drive.google.com" in h:
                    m_f = re.search(r"(?:id=|/file/d/)([A-Za-z0-9_-]{20,})", h)
                    m_dir = re.search(r"/folders/([A-Za-z0-9_-]{20,})", h)
                    if m_f:
                        fid = m_f.group(1)
                        if fid in seen_drive_ids:
                            continue
                        seen_drive_ids.add(fid)
                        title = lt if lt and lt != "Untitled_Book" else clean_iqrabari_title(ptitle)
                        out.append({
                            "key": f"iqra_gf_{fid}",
                            "kind": "gdrive_file",
                            "source_site": "iqrabari.com",
                            "drive_id": fid,
                            "title": title,
                            "url": h,
                            "page_url": purl,
                            "cover_url": pcover,
                            "folder": map_keywords_to_folder(title, ctx),
                        })
                    elif m_dir:
                        fid = m_dir.group(1)
                        if fid in seen_drive_ids:
                            continue
                        seen_drive_ids.add(fid)
                        title = lt if lt and lt != "Untitled_Book" else clean_iqrabari_title(ptitle)
                        out.append({
                            "key": f"iqra_gd_{fid}",
                            "kind": "gdrive_folder",
                            "source_site": "iqrabari.com",
                            "drive_id": fid,
                            "title": title,
                            "url": h,
                            "page_url": purl,
                            "cover_url": pcover,
                            "folder": map_keywords_to_folder(title, ctx),
                        })
                elif ".pdf" in h.lower() and h not in seen_urls:
                    seen_urls.add(h)
                    title = lt if lt and lt != "Untitled_Book" else clean_iqrabari_title(ptitle)
                    uhash = hashlib.md5(h.encode("utf-8")).hexdigest()[:12]
                    out.append({
                        "key": f"iqra_pdf_{uhash}",
                        "kind": "direct_pdf",
                        "source_site": "iqrabari.com",
                        "title": title,
                        "url": h,
                        "referer": purl,
                        "page_url": purl,
                        "cover_url": pcover,
                        "folder": map_keywords_to_folder(title, ctx),
                    })
        except Exception:
            pass

    print(f"  iqrabari.com: {len(out)} book entries found.", flush=True)
    return out


def build_catalog(include_arabic: bool = True, refresh: bool = False) -> list[dict[str, Any]]:
    if CATALOG_FILE.exists() and not refresh:
        data = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
        if data:
            return data

    print("Building unified multi-site catalog...", flush=True)
    sess = get_session()

    # 1. qawmimadrasa.com WooCommerce products + WP Media PDF index
    products = fetch_wp_paginated(BASE_URL, "product", {})
    print(f"  qawmimadrasa.com: {len(products)} WooCommerce products.", flush=True)

    media_pdfs = fetch_wp_paginated(BASE_URL, "media", {"mime_type": "application/pdf"})
    print(f"  qawmimadrasa.com: {len(media_pdfs)} WP Media PDF records.", flush=True)

    media_by_post: dict[int, list[dict[str, Any]]] = {}
    for m in media_pdfs:
        pid = m.get("post")
        if isinstance(pid, int) and pid > 0:
            media_by_post.setdefault(pid, []).append(m)

    catalog: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for p in products:
        title = html_lib.unescape((p.get("title") or {}).get("rendered") or "").strip()
        if not title or "Donations" in title:
            continue
        pid = int(p["id"])
        link = p["link"]
        cat_ids = [int(c) for c in (p.get("product_cat") or [])]
        folder = map_product_to_folder(title, cat_ids)
        og = (p.get("yoast_head_json") or {}).get("og_image") or []
        cover_url = og[0].get("url", "") if og else ""
        attached_media = [
            {"id": m["id"], "title": html_lib.unescape((m.get("title") or {}).get("rendered") or ""), "url": m["source_url"]}
            for m in media_by_post.get(pid, [])
            if m.get("source_url")
        ]
        for am in attached_media:
            seen_urls.add(am["url"])
        catalog.append({
            "key": f"prod_{pid}",
            "kind": "product",
            "source_site": "qawmimadrasa.com",
            "product_id": pid,
            "title": title,
            "url": link,
            "page_url": link,
            "cover_url": cover_url,
            "folder": folder,
            "cat_ids": cat_ids,
            "attached_media": attached_media,
        })

    # 2. Page 12812 viewer PDFs
    prod_norm_titles_by_folder: dict[str, set[str]] = {}
    for it in catalog:
        prod_norm_titles_by_folder.setdefault(it["folder"], set()).add(norm_bn_key(it["title"]))

    try:
        r12812 = sess.get(f"{BASE_URL}/wp-json/wp/v2/pages/12812", timeout=30).json()
        html_12812 = (r12812.get("content") or {}).get("rendered") or ""
        pattern = re.compile(
            r'<h3[^>]*>(.*?)</h3>|<a[^>]+href=["\']([^"\']*tnc_pvfw=[^"\']+)["\'][^>]*>(.*?)</a>',
            re.S,
        )
        cur_h3 = ""
        p12812_added = 0
        for m in pattern.finditer(html_12812):
            if m.group(1):
                cur_h3 = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            else:
                href = m.group(2)
                raw_t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(3))).strip()
                qs = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                b64 = qs.get("tnc_pvfw", [""])[0]
                b64 += "=" * (-len(b64) % 4)
                dec = base64.b64decode(b64).decode("utf-8", "ignore")
                m_file = re.search(r"file=([^&]+)", dec)
                pdf_url = urllib.parse.unquote(m_file.group(1)) if m_file else ""
                if not pdf_url or pdf_url in seen_urls:
                    continue
                seen_urls.add(pdf_url)
                fname_stem = Path(urllib.parse.urlparse(pdf_url).path).name
                title = html_lib.unescape(raw_t) if raw_t else fname_stem.replace(".pdf", "")
                folder = "17_Islamic_Life_Literature_o_Misc (ইসলামী জীবন, সাহিত্য ও বিবিধ)"
                for kw, fpath in PAGE12812_HEADING_MAP:
                    if kw in cur_h3:
                        folder = fpath
                        break
                if norm_bn_key(title) in prod_norm_titles_by_folder.get(folder, set()):
                    continue
                url_hash = hashlib.md5(pdf_url.encode("utf-8")).hexdigest()[:12]
                catalog.append({
                    "key": f"p12812_{url_hash}",
                    "kind": "direct_pdf",
                    "source_site": "qawmimadrasa.com",
                    "title": title,
                    "url": pdf_url,
                    "referer": f"{BASE_URL}/darse-nizami-bangla-books-pdf-download/",
                    "page_url": f"{BASE_URL}/darse-nizami-bangla-books-pdf-download/",
                    "cover_url": "",
                    "folder": folder,
                })
                p12812_added += 1
        print(f"  qawmimadrasa.com Page 12812: +{p12812_added} PDFs.", flush=True)
    except Exception as e:
        print(f"  Warning parsing Page 12812: {e}", flush=True)

    # 3. Dictionaries page Google Drive links
    try:
        dict_url = f"{BASE_URL}/%e0%a6%85%e0%a6%ad%e0%a6%bf%e0%a6%a7%e0%a6%be%e0%a6%a8-%e0%a6%b8%e0%a6%ae%e0%a7%8d%e0%a6%ad%e0%a6%be%e0%a6%b0-%e0%a6%ac%e0%a6%be%e0%a6%82%e0%a6%b2%e0%a6%be-%e0%a6%86%e0%a6%b0%e0%a6%ac%e0%a7%80/"
        rd = sess.get(dict_url, timeout=30)
        soupd = BeautifulSoup(rd.text, "html.parser")
        cd = soupd.find(class_="entry-content")
        dict_added = 0
        if cd:
            for a in cd.find_all("a", href=True):
                href = a["href"]
                if "drive.google.com" not in href:
                    continue
                t = a.get_text(" ", strip=True)
                if not t:
                    continue
                m_f = re.search(r"(?:id=|/file/d/)([A-Za-z0-9_-]{20,})", href)
                m_dir = re.search(r"/folders/([A-Za-z0-9_-]{20,})", href)
                if m_dir:
                    fid = m_dir.group(1)
                    if fid in seen_urls:
                        continue
                    seen_urls.add(fid)
                    catalog.append({
                        "key": f"gdrive_dir_{fid}",
                        "kind": "gdrive_folder",
                        "source_site": "qawmimadrasa.com",
                        "drive_id": fid,
                        "title": t,
                        "url": href,
                        "page_url": dict_url,
                        "cover_url": "",
                        "folder": "18_Dictionaries_&_Lexicons (অভিধান সম্ভার)",
                    })
                    dict_added += 1
                elif m_f:
                    fid = m_f.group(1)
                    if fid in seen_urls:
                        continue
                    seen_urls.add(fid)
                    catalog.append({
                        "key": f"gdrive_file_{fid}",
                        "kind": "gdrive_file",
                        "source_site": "qawmimadrasa.com",
                        "drive_id": fid,
                        "title": t,
                        "url": href,
                        "page_url": dict_url,
                        "cover_url": "",
                        "folder": "18_Dictionaries_&_Lexicons (অভিধান সম্ভার)",
                    })
                    dict_added += 1
        print(f"  qawmimadrasa.com Dictionaries: +{dict_added} entries.", flush=True)
    except Exception as e:
        print(f"  Warning parsing Dictionaries page: {e}", flush=True)

    # 4. Unattached WP Media PDFs
    unattached_added = 0
    for m in media_pdfs:
        src = m.get("source_url") or ""
        if not src or src in seen_urls or (isinstance(m.get("post"), int) and m["post"] > 0):
            continue
        seen_urls.add(src)
        raw_title = html_lib.unescape((m.get("title") or {}).get("rendered") or "").strip()
        fname = Path(urllib.parse.urlparse(src).path).name
        title = raw_title or fname.replace(".pdf", "")
        catalog.append({
            "key": f"media_{m['id']}",
            "kind": "direct_pdf",
            "source_site": "qawmimadrasa.com",
            "title": title,
            "url": src,
            "referer": BASE_URL,
            "page_url": BASE_URL,
            "cover_url": "",
            "folder": map_prefix_to_folder(fname),
        })
        unattached_added += 1
    print(f"  qawmimadrasa.com Unattached Media: +{unattached_added} PDFs.", flush=True)

    # 5. banglakitab.weebly.com
    catalog.extend(crawl_banglakitab(seen_urls))

    # 6. iqrabari.com
    catalog.extend(crawl_iqrabari(seen_urls))

    # 7. qawmimadrasa.com Arabic Reference Library (2,444 Wikisource Arabic books)
    if include_arabic:
        try:
            ar_url = f"{BASE_URL}/%e0%a6%86%e0%a6%b0%e0%a6%ac%e0%a7%80-%e0%a6%95%e0%a6%bf%e0%a6%a4%e0%a6%be%e0%a6%ac%e0%a7%87%e0%a6%b0-%e0%a6%a1%e0%a6%be%e0%a6%89%e0%a6%a8%e0%a6%b2%e0%a7%8b%e0%a6%a1-%e0%a6%b2%e0%a6%bf%e0%a6%82/"
            rar = sess.get(ar_url, timeout=60)
            soupar = BeautifulSoup(rar.text, "html.parser")
            ol = soupar.find("ol", class_="wp-block-list")
            ar_added = 0
            if ol:
                for idx, li in enumerate(ol.find_all("li"), start=1):
                    pdfs = [
                        a["href"]
                        for a in li.find_all("a", href=True)
                        if ".pdf" in a["href"].lower() and "upload.wikimedia.org" in a["href"]
                    ]
                    if not pdfs:
                        continue
                    pdf_url = pdfs[0]
                    if pdf_url in seen_urls:
                        continue
                    seen_urls.add(pdf_url)
                    txt = li.get_text(" ", strip=True)
                    title = re.split(r"\s+[–-]\s+", txt)[0].strip()
                    catalog.append({
                        "key": f"ar_{idx}",
                        "kind": "direct_pdf",
                        "source_site": "qawmimadrasa.com",
                        "title": title,
                        "url": pdf_url,
                        "referer": ar_url,
                        "page_url": ar_url,
                        "cover_url": "",
                        "folder": "19_Arabic_Reference_Library (আরবী কিতাব সম্ভার)",
                    })
                    ar_added += 1
            print(f"  qawmimadrasa.com Arabic Reference Library: +{ar_added} PDFs.", flush=True)
        except Exception as e:
            print(f"  Warning parsing Arabic books page: {e}", flush=True)

    # Assign deterministic target_stem per folder so colliding titles never overwrite/skip each other
    used_stems: dict[str, set[str]] = {}
    for it in catalog:
        folder = it["folder"]
        fset = used_stems.setdefault(folder, set())
        stem = sanitize_filename(it["title"])
        cand = stem
        n = 2
        while cand in fset:
            cand = f"{stem} ({n})"
            n += 1
        fset.add(cand)
        it["target_stem"] = cand

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CATALOG_FILE.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Total unified catalog items: {len(catalog)}", flush=True)
    return catalog


def stream_download_to_file(resp: requests.Response, dest: Path) -> int:
    ctype = (resp.headers.get("Content-Type") or "").lower()
    if "text/html" in ctype:
        raise ValueError(f"Expected binary file, got {ctype}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    first_bytes = b""
    with open(dest, "wb") as fh:
        for chunk in resp.iter_content(chunk_size=1024 * 256):
            if not chunk:
                continue
            if not first_bytes:
                first_bytes = chunk[:16]
            fh.write(chunk)
            total += len(chunk)
    if total < 512:
        raise ValueError(f"Downloaded file too small ({total} bytes)")
    if "pdf" in ctype and not first_bytes.startswith(b"%PDF"):
        raise ValueError(f"Invalid PDF header: {first_bytes[:8]!r}")
    return total


def normalize_dropbox_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)
    qs["dl"] = ["1"]
    new_q = urllib.parse.urlencode(qs, doseq=True)
    return urllib.parse.urlunparse(parsed._replace(query=new_q))


def download_url_direct(url: str, dest: Path, referer: str) -> int:
    sess = get_session()
    target_url = normalize_dropbox_url(url) if "dropbox.com" in url else url
    headers = {"Referer": referer}
    if "wikimedia.org" in target_url:
        headers["User-Agent"] = BOT_UA
    for attempt in range(3):
        try:
            with sess.get(target_url, headers=headers, stream=True, allow_redirects=True, timeout=240) as r:
                if r.status_code in (404, 410):
                    raise PermanentNotFoundError(f"HTTP {r.status_code} for {target_url}")
                r.raise_for_status()
                return stream_download_to_file(r, dest)
        except PermanentNotFoundError:
            dest.unlink(missing_ok=True)
            raise
        except Exception:
            dest.unlink(missing_ok=True)
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("Unreachable")


def download_somdn(
    product_url: str,
    product_id: int,
    action: str,
    dest: Path,
    productfile: str | None = None,
) -> int:
    sess = get_session()
    for attempt in range(3):
        try:
            key = base64.b64encode(str(int(time.time())).encode()).decode()
            payload: dict[str, str] = {
                "somdn_download_key": key,
                "action": action,
                "somdn_product": str(product_id),
            }
            if productfile is not None:
                payload["somdn_productfile"] = productfile
            headers = {
                "Origin": BASE_URL,
                "Referer": product_url,
            }
            with sess.post(product_url, data=payload, headers=headers, stream=True, timeout=240) as r:
                r.raise_for_status()
                return stream_download_to_file(r, dest)
        except Exception:
            dest.unlink(missing_ok=True)
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("Unreachable")


def reserve_unique_filename(folder_id: str, desired_name: str, existing_names: dict[str, set[str]]) -> tuple[str, bool]:
    with LOCK:
        fset = existing_names.setdefault(folder_id, set())
        if desired_name in fset:
            return desired_name, True
        fset.add(desired_name)
        return desired_name, False


def upload_or_extract_cover(
    book_stem: str,
    cover_url: str,
    local_pdf: Path | None,
    folders: dict[str, str],
    existing_names: dict[str, set[str]],
    tag: str,
) -> str:
    """Download remote cover image or render Page 1 of local_pdf, and upload to 00_Covers_&_Thumbnails."""
    covers_folder_id = folders[COVERS_FOLDER_PATH]
    sess = get_session()
    tmp_cover = TMP_DIR / f"cov_{tag}_{int(time.time() * 1000)}"
    try:
        # 1. Try downloading remote cover_url first
        if cover_url:
            try:
                rc = sess.get(cover_url, timeout=30)
                if rc.status_code == 200 and len(rc.content) > 500:
                    ct = (rc.headers.get("Content-Type") or "").lower()
                    if "webp" in ct or cover_url.lower().endswith(".webp"):
                        ext, mime = ".webp", "image/webp"
                    elif "png" in ct or cover_url.lower().endswith(".png"):
                        ext, mime = ".png", "image/png"
                    else:
                        ext, mime = ".jpg", "image/jpeg"
                    cov_name = f"{book_stem}{ext}"
                    final_name, exists = reserve_unique_filename(covers_folder_id, cov_name, existing_names)
                    if exists:
                        return ""
                    img_path = tmp_cover.with_suffix(ext)
                    img_path.write_bytes(rc.content)
                    try:
                        return drive_upload(img_path, final_name, covers_folder_id, mime_type=mime)
                    finally:
                        img_path.unlink(missing_ok=True)
            except Exception:
                pass

        # 2. Fallback: render Page 1 of local_pdf via PyMuPDF
        if local_pdf and local_pdf.exists():
            cov_name = f"{book_stem}.jpg"
            final_name, exists = reserve_unique_filename(covers_folder_id, cov_name, existing_names)
            if exists:
                return ""
            img_path = tmp_cover.with_suffix(".jpg")
            try:
                with pymupdf.open(local_pdf) as doc:
                    if len(doc) > 0:
                        pix = doc[0].get_pixmap(dpi=130)
                        if pix.alpha:
                            pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
                        img_path.write_bytes(pix.tobytes("jpeg", jpg_quality=85))
                        return drive_upload(img_path, final_name, covers_folder_id, mime_type="image/jpeg")
            except Exception:
                pass
            finally:
                img_path.unlink(missing_ok=True)
    finally:
        tmp_cover.unlink(missing_ok=True)
    return ""


def process_external_url(
    item: dict[str, Any],
    folders: dict[str, str],
    existing_names: dict[str, set[str]],
) -> tuple[str, dict[str, Any]]:
    key = item["key"]
    folder_path = item["folder"]
    folder_id = folders[folder_path]
    base_title = item.get("target_stem") or sanitize_filename(item["title"])
    raw_url = item["url"]
    sess = get_session()

    # Resolve shortlinks (bit.ly / goo.gl)
    resolved_url = raw_url
    if any(d in raw_url for d in ("bit.ly", "goo.gl")):
        try:
            rh = sess.head(raw_url, allow_redirects=True, timeout=20)
            resolved_url = rh.url
            if rh.status_code in (404, 410):
                return "not_found_404", {"key": key, "url": raw_url, "error": f"Resolved HTTP {rh.status_code}"}
        except Exception as e:
            return "error", {"key": key, "title": base_title, "errors": [f"Shortlink error: {e}"]}

    if "drive.google.com" in resolved_url:
        m_f = re.search(r"(?:id=|/file/d/)([A-Za-z0-9_-]{20,})", resolved_url)
        m_dir = re.search(r"/folders/([A-Za-z0-9_-]{20,})", resolved_url)
        if m_dir:
            try:
                children = drive_list_children(m_dir.group(1))
                uploaded_files = []
                for ch in children:
                    if ch.get("mimeType") == "application/vnd.google-apps.folder":
                        continue
                    cname = sanitize_filename(ch["name"])
                    if not cname.lower().endswith(".pdf"):
                        cname += ".pdf"
                    final_name, exists = reserve_unique_filename(folder_id, cname, existing_names)
                    if exists:
                        continue
                    fid = drive_copy(ch["id"], final_name, folder_id)
                    cov_id = upload_or_extract_cover(Path(final_name).stem, item.get("cover_url", ""), None, folders, existing_names, key)
                    uploaded_files.append({"id": fid, "name": final_name, "size": int(ch.get("size") or 0), "cover_id": cov_id})
                return "added", {"key": key, "folder": folder_path, "folder_id": folder_id, "files": uploaded_files}
            except (PermanentNotFoundError, RuntimeError) as nf:
                if "404" in str(nf) or "not found" in str(nf).lower():
                    return "not_found_404", {"key": key, "url": resolved_url, "error": str(nf)}
                raise
        if m_f:
            target_name = f"{base_title}.pdf"
            final_name, exists = reserve_unique_filename(folder_id, target_name, existing_names)
            if exists:
                return "skipped_existing", {"key": key, "name": final_name, "folder": folder_path}
            try:
                fid = drive_copy(m_f.group(1), final_name, folder_id)
                cov_id = upload_or_extract_cover(base_title, item.get("cover_url", ""), None, folders, existing_names, key)
                return "added", {
                    "key": key,
                    "folder": folder_path,
                    "folder_id": folder_id,
                    "files": [{"id": fid, "name": final_name, "size": 0, "cover_id": cov_id}],
                }
            except PermanentNotFoundError as nf:
                return "not_found_404", {"key": key, "url": resolved_url, "error": str(nf)}

    # Check if resolved_url is a Dropbox folder (/scl/fo/) or ZIP archive
    is_zip_source = ("dropbox.com/scl/fo/" in resolved_url) or resolved_url.lower().endswith(".zip")
    if is_zip_source:
        dl_zip_url = normalize_dropbox_url(resolved_url) if "dropbox.com" in resolved_url else resolved_url
        tmp_zip = TMP_DIR / f"{key}_{int(time.time() * 1000)}.zip"
        ext_dir = TMP_DIR / f"ext_{key}_{int(time.time() * 1000)}"
        try:
            download_url_direct(dl_zip_url, tmp_zip, item.get("page_url") or BANGLAKITAB_URL)
            uploaded_files = []
            with zipfile.ZipFile(tmp_zip, "r") as zf:
                zf.extractall(ext_dir)
            for pdf_path in sorted(ext_dir.rglob("*.pdf")):
                cname = sanitize_filename(pdf_path.name)
                if not cname.lower().endswith(".pdf"):
                    cname += ".pdf"
                sub_folder_path = map_keywords_to_folder(pdf_path.stem, folder_path)
                sub_folder_id = folders[sub_folder_path]
                final_name, exists = reserve_unique_filename(sub_folder_id, cname, existing_names)
                if exists:
                    continue
                size = pdf_path.stat().st_size
                if size < 1024:
                    continue
                fid = drive_upload(pdf_path, final_name, sub_folder_id)
                cov_id = upload_or_extract_cover(Path(final_name).stem, "", pdf_path, folders, existing_names, f"{key}_{len(uploaded_files)}")
                uploaded_files.append({
                    "id": fid,
                    "name": final_name,
                    "size": size,
                    "cover_id": cov_id,
                    "folder": sub_folder_path,
                    "folder_id": sub_folder_id,
                })
            return "added", {"key": key, "folder": folder_path, "folder_id": folder_id, "files": uploaded_files}
        except PermanentNotFoundError as nf:
            return "not_found_404", {"key": key, "url": resolved_url, "error": str(nf)}
        finally:
            tmp_zip.unlink(missing_ok=True)
            shutil.rmtree(ext_dir, ignore_errors=True)

    # Otherwise single PDF download (Dropbox file / Archive.org)
    # If title came from a generic fallback, refine stem from resolved Dropbox filename
    if base_title.startswith("banglakitab_") and "dropbox.com" in resolved_url:
        parsed_stem = Path(urllib.parse.unquote(urllib.parse.urlparse(resolved_url).path)).stem
        if parsed_stem:
            base_title = sanitize_filename(parsed_stem.replace("-", " ").replace("_", " "))

    target_name = f"{base_title}.pdf"
    final_name, exists = reserve_unique_filename(folder_id, target_name, existing_names)
    if exists:
        return "skipped_existing", {"key": key, "name": final_name, "folder": folder_path}

    tmp_file = TMP_DIR / f"{key}_{int(time.time() * 1000)}.pdf"
    try:
        size = download_url_direct(resolved_url, tmp_file, item.get("page_url") or BANGLAKITAB_URL)
        fid = drive_upload(tmp_file, final_name, folder_id)
        cov_id = upload_or_extract_cover(Path(final_name).stem, item.get("cover_url", ""), tmp_file, folders, existing_names, key)
        return "added", {
            "key": key,
            "folder": folder_path,
            "folder_id": folder_id,
            "files": [{"id": fid, "name": final_name, "size": size, "cover_id": cov_id}],
        }
    except PermanentNotFoundError as nf:
        return "not_found_404", {"key": key, "url": resolved_url, "error": str(nf)}
    finally:
        tmp_file.unlink(missing_ok=True)


def process_item(
    item: dict[str, Any],
    folders: dict[str, str],
    existing_names: dict[str, set[str]],
    deadline: float | None,
) -> tuple[str, dict[str, Any]]:
    if deadline and time.time() > deadline:
        return "time_limit", {"key": item["key"]}

    key = item["key"]
    folder_path = item["folder"]
    folder_id = folders[folder_path]
    base_title = item.get("target_stem") or sanitize_filename(item["title"])
    cover_url = item.get("cover_url", "")

    if item["kind"] == "external_url":
        return process_external_url(item, folders, existing_names)

    if item["kind"] == "direct_pdf":
        target_name = f"{base_title}.pdf"
        final_name, exists = reserve_unique_filename(folder_id, target_name, existing_names)
        if exists:
            return "skipped_existing", {"key": key, "name": final_name, "folder": folder_path}

        tmp_file = TMP_DIR / f"{key}_{int(time.time() * 1000)}.pdf"
        try:
            size = download_url_direct(item["url"], tmp_file, item.get("referer") or BASE_URL)
            fid = drive_upload(tmp_file, final_name, folder_id)
            cov_id = upload_or_extract_cover(base_title, cover_url, tmp_file, folders, existing_names, key)
            return "added", {
                "key": key,
                "folder": folder_path,
                "folder_id": folder_id,
                "files": [{"id": fid, "name": final_name, "size": size, "cover_id": cov_id}],
            }
        except PermanentNotFoundError as nf:
            return "not_found_404", {"key": key, "url": item["url"], "error": str(nf)}
        finally:
            tmp_file.unlink(missing_ok=True)

    if item["kind"] == "gdrive_file":
        target_name = f"{base_title}.pdf"
        final_name, exists = reserve_unique_filename(folder_id, target_name, existing_names)
        if exists:
            return "skipped_existing", {"key": key, "name": final_name, "folder": folder_path}
        try:
            fid = drive_copy(item["drive_id"], final_name, folder_id)
            cov_id = upload_or_extract_cover(base_title, cover_url, None, folders, existing_names, key)
            return "added", {
                "key": key,
                "folder": folder_path,
                "folder_id": folder_id,
                "files": [{"id": fid, "name": final_name, "size": 0, "cover_id": cov_id}],
            }
        except PermanentNotFoundError as nf:
            return "not_found_404", {"key": key, "url": item["url"], "error": str(nf)}

    if item["kind"] == "gdrive_folder":
        try:
            children = drive_list_children(item["drive_id"])
            uploaded_files = []
            for ch in children:
                if ch.get("mimeType") == "application/vnd.google-apps.folder":
                    continue
                cname = f"{base_title} — {sanitize_filename(ch['name'])}"
                if not cname.lower().endswith(".pdf"):
                    cname += ".pdf"
                final_name, exists = reserve_unique_filename(folder_id, cname, existing_names)
                if exists:
                    continue
                fid = drive_copy(ch["id"], final_name, folder_id)
                cov_id = upload_or_extract_cover(Path(final_name).stem, cover_url, None, folders, existing_names, key)
                uploaded_files.append({"id": fid, "name": final_name, "size": int(ch.get("size") or 0), "cover_id": cov_id})
            return "added", {
                "key": key,
                "folder": folder_path,
                "folder_id": folder_id,
                "files": uploaded_files,
            }
        except (PermanentNotFoundError, RuntimeError) as nf:
            if "404" in str(nf) or "not found" in str(nf).lower():
                return "not_found_404", {"key": key, "url": item["url"], "error": str(nf)}
            raise

    # WooCommerce product (single or multi-volume)
    sess = get_session()
    prod_url = item["url"]
    prod_id = int(item["product_id"])
    r = sess.get(prod_url, timeout=45)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    forms = soup.find_all("form", class_=lambda c: c and "somdn-download-form" in c)

    download_tasks: list[dict[str, Any]] = []
    if len(forms) == 1:
        action_inp = forms[0].find("input", attrs={"name": "action"})
        pfile_inp = forms[0].find("input", attrs={"name": "somdn_productfile"})
        action = action_inp["value"] if action_inp else "somdn_download_single"
        pfile = pfile_inp["value"] if pfile_inp else None
        download_tasks.append({
            "target_name": f"{base_title}.pdf",
            "mode": "somdn",
            "action": action,
            "productfile": pfile,
        })
    elif len(forms) > 1:
        for idx, form in enumerate(forms, start=1):
            action_inp = form.find("input", attrs={"name": "action"})
            pfile_inp = form.find("input", attrs={"name": "somdn_productfile"})
            a_link = form.find("a", class_="somdn-download-link")
            vol_raw = a_link.get_text(" ", strip=True) if a_link else f"Part {idx}"
            vol_clean = clean_volume_label(vol_raw)
            download_tasks.append({
                "target_name": f"{base_title} — {vol_clean}.pdf",
                "mode": "somdn",
                "action": action_inp["value"] if action_inp else "somdn_download_multi_single",
                "productfile": pfile_inp["value"] if pfile_inp else str(idx),
            })
    else:
        attached = item.get("attached_media") or []
        if len(attached) == 1:
            download_tasks.append({"target_name": f"{base_title}.pdf", "mode": "direct", "url": attached[0]["url"]})
        elif len(attached) > 1:
            for idx, am in enumerate(attached, start=1):
                vol_clean = clean_volume_label(am.get("title") or f"Part {idx}")
                download_tasks.append({"target_name": f"{base_title} — {vol_clean}.pdf", "mode": "direct", "url": am["url"]})
        else:
            for a in soup.find_all("a", href=True):
                h = a["href"]
                if ".pdf" in h.lower() and "qawmimadrasa.com" in h:
                    download_tasks.append({"target_name": f"{base_title}.pdf", "mode": "direct", "url": h})
                    break
                if "drive.google.com" in h:
                    m_f = re.search(r"(?:id=|/file/d/)([A-Za-z0-9_-]{20,})", h)
                    if m_f:
                        download_tasks.append({"target_name": f"{base_title}.pdf", "mode": "gdrive", "drive_id": m_f.group(1)})
                        break

    if not download_tasks:
        return "no_file_found", {"key": key, "title": base_title, "url": prod_url}

    uploaded_files: list[dict[str, Any]] = []
    errors: list[str] = []
    shared_cover_id = ""
    for idx, dt in enumerate(download_tasks, start=1):
        tname = dt["target_name"]
        final_name, exists = reserve_unique_filename(folder_id, tname, existing_names)
        if exists:
            continue

        tmp_file = TMP_DIR / f"{key}_{idx}_{int(time.time() * 1000)}.pdf"
        try:
            if dt["mode"] == "somdn":
                try:
                    size = download_somdn(prod_url, prod_id, dt["action"], tmp_file, dt.get("productfile"))
                except Exception as somdn_err:
                    attached = item.get("attached_media") or []
                    if idx - 1 < len(attached):
                        size = download_url_direct(attached[idx - 1]["url"], tmp_file, prod_url)
                    else:
                        raise somdn_err
                fid = drive_upload(tmp_file, final_name, folder_id)
                if not shared_cover_id:
                    shared_cover_id = upload_or_extract_cover(base_title, cover_url, tmp_file, folders, existing_names, key)
                uploaded_files.append({"id": fid, "name": final_name, "size": size, "cover_id": shared_cover_id})
            elif dt["mode"] == "direct":
                size = download_url_direct(dt["url"], tmp_file, prod_url)
                fid = drive_upload(tmp_file, final_name, folder_id)
                if not shared_cover_id:
                    shared_cover_id = upload_or_extract_cover(base_title, cover_url, tmp_file, folders, existing_names, key)
                uploaded_files.append({"id": fid, "name": final_name, "size": size, "cover_id": shared_cover_id})
            elif dt["mode"] == "gdrive":
                fid = drive_copy(dt["drive_id"], final_name, folder_id)
                if not shared_cover_id:
                    shared_cover_id = upload_or_extract_cover(base_title, cover_url, None, folders, existing_names, key)
                uploaded_files.append({"id": fid, "name": final_name, "size": 0, "cover_id": shared_cover_id})
        except Exception as exc:
            errors.append(f"{tname}: {exc}")
        finally:
            tmp_file.unlink(missing_ok=True)

    if errors and not uploaded_files:
        return "error", {"key": key, "title": base_title, "errors": errors}

    return "added", {
        "key": key,
        "status": "partial" if errors else "added",
        "folder": folder_path,
        "folder_id": folder_id,
        "files": uploaded_files,
        "errors": errors,
    }


def save_progress(progress: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8")


def write_summary(catalog: list[dict[str, Any]], progress: dict[str, Any], stats: dict[str, int]) -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    total_files = sum(len(v.get("files") or []) for v in progress.values() if isinstance(v, dict))
    total_bytes = sum(
        int(f.get("size") or 0)
        for v in progress.values()
        if isinstance(v, dict)
        for f in (v.get("files") or [])
    )
    summary = {
        "total_catalog_items": len(catalog),
        "processed_items": len(progress),
        "remaining_items": sum(1 for it in catalog if it["key"] not in progress),
        "total_uploaded_files": total_files,
        "total_uploaded_mb": round(total_bytes / (1024 * 1024), 2),
        "last_run_stats": stats,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    SUMMARY_FILE.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def build_and_upload_spreadsheet(
    catalog: list[dict[str, Any]],
    progress: dict[str, Any],
    folders: dict[str, str],
    upload_drive: bool = True,
) -> None:
    """Build Category Map + Book Catalog spreadsheets (.xlsx & .csv) and upload to Drive root."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    xlsx_path = REPORTS_DIR / XLSX_NAME
    csv_path = REPORTS_DIR / CSV_NAME

    cat_counts: dict[str, int] = {}
    for it in catalog:
        cat_counts[it["folder"]] = cat_counts.get(it["folder"], 0) + 1

    up_counts: dict[str, int] = {}
    book_rows: list[list[Any]] = []
    cat_by_key = {it["key"]: it for it in catalog}

    for it in catalog:
        key = it["key"]
        rec = progress.get(key)
        fpath = it["folder"]
        meta = STAGE_METADATA.get(fpath, ("", "", "", ""))
        if isinstance(rec, dict) and rec.get("files"):
            for f in rec["files"]:
                actual_folder = f.get("folder") or fpath
                actual_fid = f.get("folder_id") or folders.get(actual_folder, "")
                actual_meta = STAGE_METADATA.get(actual_folder, meta)
                up_counts[actual_folder] = up_counts.get(actual_folder, 0) + 1
                pdf_id = f.get("id", "")
                cov_id = f.get("cover_id", "")
                size_mb = round(int(f.get("size") or 0) / (1024 * 1024), 2) if f.get("size") else ""
                book_rows.append([
                    f.get("name") or it["title"],
                    actual_meta[1],
                    actual_meta[2],
                    actual_folder,
                    it.get("source_site", "qawmimadrasa.com"),
                    size_mb,
                    f"https://drive.google.com/file/d/{pdf_id}/view" if pdf_id else "",
                    f"https://drive.google.com/drive/folders/{actual_fid}" if actual_fid else "",
                    f"https://drive.google.com/file/d/{cov_id}/view" if cov_id else "",
                    f"https://drive.google.com/thumbnail?id={cov_id}&sz=w600" if cov_id else "",
                    it.get("cover_url", ""),
                    it.get("page_url") or it.get("url", ""),
                ])
        else:
            status_str = rec.get("status", "pending") if isinstance(rec, dict) else "pending"
            fid = folders.get(fpath, "")
            book_rows.append([
                it["title"],
                meta[1],
                meta[2],
                fpath,
                it.get("source_site", "qawmimadrasa.com"),
                "",
                f"[{status_str}]",
                f"https://drive.google.com/drive/folders/{fid}" if fid else "",
                "",
                "",
                it.get("cover_url", ""),
                it.get("page_url") or it.get("url", ""),
            ])

    # Build Excel workbook
    wb = openpyxl.Workbook()
    ws_map = wb.active
    ws_map.title = "Category_Map"
    header_fill = PatternFill(start_color="1B5E20", end_color="1B5E20", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True, size=11)

    map_headers = [
        "Code",
        "Qawmi Madrasa Stage (কওমী মাদ্রাসা স্তর)",
        "General Education Equivalent (সাধারণ শিক্ষা সমমান)",
        "Drive Folder Path (ফোল্ডার পাথ)",
        "Mapped Website Categories (ওয়েবসাইট ক্যাটাগরি)",
        "Catalog Books Count",
        "Uploaded Files Count",
        "Google Drive Folder Link",
    ]
    ws_map.append(map_headers)
    for col_idx in range(1, len(map_headers) + 1):
        c = ws_map.cell(row=1, column=col_idx)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for fpath in FOLDER_PATHS:
        code, stage, gen_eq, mapped = STAGE_METADATA.get(fpath, ("", "", "", ""))
        fid = folders.get(fpath, "")
        dlink = f"https://drive.google.com/drive/folders/{fid}" if fid else ""
        ws_map.append([
            code,
            stage,
            gen_eq,
            fpath,
            mapped,
            cat_counts.get(fpath, 0),
            up_counts.get(fpath, 0),
            dlink,
        ])
    ws_map.freeze_panes = "A2"
    ws_map.auto_filter.ref = f"A1:H{len(FOLDER_PATHS) + 1}"
    for col, w in zip("ABCDEFGH", [8, 30, 28, 56, 46, 18, 20, 56]):
        ws_map.column_dimensions[col].width = w

    ws_books = wb.create_sheet("Books_Catalog")
    book_headers = [
        "Book Title (কিতাবের নাম)",
        "Qawmi Stage",
        "General Education Equivalent",
        "Folder Path",
        "Source Website",
        "Size (MB)",
        "PDF Google Drive Link",
        "Folder Google Drive Link",
        "Cover Image Drive Link",
        "Embeddable Thumbnail URL",
        "Original Source Cover URL",
        "Source Page URL",
    ]
    ws_books.append(book_headers)
    for col_idx in range(1, len(book_headers) + 1):
        c = ws_books.cell(row=1, column=col_idx)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for row in book_rows:
        ws_books.append(row)
    ws_books.freeze_panes = "A2"
    ws_books.auto_filter.ref = f"A1:L{len(book_rows) + 1}"
    for col, w in zip("ABCDEFGHIJKL", [48, 26, 24, 48, 22, 10, 48, 48, 48, 52, 52, 52]):
        ws_books.column_dimensions[col].width = w

    wb.save(xlsx_path)

    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(book_headers)
        writer.writerows(book_rows)

    print(f"Generated spreadsheet ({len(book_rows)} rows): {xlsx_path}", flush=True)
    if upload_drive:
        drive_update_or_upload(
            xlsx_path,
            XLSX_NAME,
            QAWMI_ROOT_ID,
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        drive_update_or_upload(csv_path, CSV_NAME, QAWMI_ROOT_ID, "text/csv")
        print(f"Uploaded {XLSX_NAME} and {CSV_NAME} to Google Drive Qawmi_Madrasa root.", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Max items per run (0 = all)")
    parser.add_argument("--workers", type=int, default=8, help="Concurrent download/upload workers")
    parser.add_argument("--max-minutes", type=int, default=0, help="Graceful stop after N minutes (0 = no limit)")
    parser.add_argument("--refresh-catalog", action="store_true", help="Force re-crawl all websites")
    parser.add_argument("--no-arabic", action="store_true", help="Skip 2,444 Arabic Wikisource books")
    parser.add_argument("--spreadsheet-only", action="store_true", help="Only rebuild and upload spreadsheet")
    args = parser.parse_args()

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    folders = ensure_folders()
    catalog = build_catalog(include_arabic=not args.no_arabic, refresh=args.refresh_catalog)
    progress: dict[str, Any] = (
        json.loads(PROGRESS_FILE.read_text(encoding="utf-8")) if PROGRESS_FILE.exists() else {}
    )

    if args.spreadsheet_only:
        build_and_upload_spreadsheet(catalog, progress, folders, upload_drive=True)
        return

    todo = [it for it in catalog if it["key"] not in progress]
    if args.limit > 0:
        todo = todo[: args.limit]

    print(f"Unified Catalog: {len(catalog)} | Processed: {len(progress)} | Todo this run: {len(todo)}", flush=True)
    if not todo:
        write_summary(catalog, progress, {"added": 0, "skipped_existing": 0, "no_file_found": 0, "error": 0, "time_limit": 0})
        build_and_upload_spreadsheet(catalog, progress, folders, upload_drive=True)
        return

    # Index existing filenames in target folders + covers folder
    needed_folder_ids = {folders[it["folder"]] for it in todo} | {folders[COVERS_FOLDER_PATH]}
    # Also include all folders if any external_url zip might route into any subject folder
    if any(it["kind"] == "external_url" for it in todo):
        needed_folder_ids |= set(folders.values())

    existing_names: dict[str, set[str]] = {}
    print(f"Indexing existing files across {len(needed_folder_ids)} Drive folders...", flush=True)
    for fid in needed_folder_ids:
        kids = drive_list_children(fid)
        existing_names[fid] = {k["name"] for k in kids if k.get("mimeType") != "application/vnd.google-apps.folder"}

    deadline = (time.time() + args.max_minutes * 60) if args.max_minutes > 0 else None
    stats = {"added": 0, "skipped_existing": 0, "no_file_found": 0, "not_found_404": 0, "error": 0, "time_limit": 0}
    done = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(process_item, it, folders, existing_names, deadline): it for it in todo}
        for f in concurrent.futures.as_completed(futs):
            it = futs[f]
            done += 1
            try:
                status, info = f.result()
                stats[status] = stats.get(status, 0) + 1
                if status in ("added", "skipped_existing", "no_file_found", "not_found_404"):
                    with LOCK:
                        progress[it["key"]] = {**info, "status": status}
                elif status == "error":
                    print(f"[{done}/{len(todo)}] ERROR {it['key']} ({it['title']}): {info.get('errors')}", flush=True)
            except Exception as exc:
                stats["error"] += 1
                print(f"[{done}/{len(todo)}] EXCEPTION {it['key']} ({it['title']}): {exc}", flush=True)

            if done % 10 == 0 or done == len(todo):
                with LOCK:
                    save_progress(progress)
                print(
                    f"Progress [{done}/{len(todo)}] added={stats['added']} skipped={stats['skipped_existing']} no_file={stats['no_file_found']} nf404={stats['not_found_404']} err={stats['error']} tlimit={stats['time_limit']}",
                    flush=True,
                )

    with LOCK:
        save_progress(progress)
    write_summary(catalog, progress, stats)
    build_and_upload_spreadsheet(catalog, progress, folders, upload_drive=True)
    shutil.rmtree(TMP_DIR, ignore_errors=True)
    print(f"Run complete! Stats: {stats}", flush=True)


if __name__ == "__main__":
    main()
