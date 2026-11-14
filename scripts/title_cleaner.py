#!/usr/bin/env python3
"""
Shared Unicode/Bijoy/filename/title normalization utilities for Bangladesh-Biggest-eBook-Library.
"""
from __future__ import annotations

import re
import unicodedata

# ---------------------------------------------------------------------------
# Opaque / non-descriptive stem detection
# ---------------------------------------------------------------------------
OPAQUE_STEM_RE = re.compile(
    r"^(?:"
    r"[\s._\-\u09e6-\u09ef0-9]+"
    r"|(?:book|file|doc|document|scan|img|untitled|part|vol|volume|chapter|ch|pdf|epub|page|q|no|issue|copy)[\s._\-()]*[\d\u09e6-\u09ef+._\-()]*"
    r"|_?part[\s._\-+()0-9\u09e6-\u09ef]+"
    r"|\d+_\d{10,}"
    r"|new[\s._\-]*doc.*"
    r"|camscanner.*"
    r"|microsoft\s+word\s*[-–—].*"
    r"|ও"
    r")$",
    re.I,
)

# ---------------------------------------------------------------------------
# Bijoy ANSI (SutonnyMJ) -> Unicode Bengali converter
# ---------------------------------------------------------------------------
# Reference mapping based on Avro/SutonnyMJ Bijoy ANSI encoding table.
_BIJOY_CONSONANT_AND_SIGNS: dict[str, str] = {
    "K": "ক", "L": "খ", "M": "গ", "N": "ঘ", "O": "ঙ",
    "P": "চ", "Q": "ছ", "R": "জ", "S": "ঝ", "T": "ঞ",
    "U": "ট", "V": "ঠ", "W": "ড", "X": "ঢ", "Y": "ণ",
    "Z": "ত", "_": "থ", "`": "দ", "a": "ধ", "b": "ন",
    "c": "প", "d": "ফ", "e": "ব", "f": "ভ", "g": "ম",
    "h": "য", "i": "র", "j": "ল", "k": "শ", "l": "ষ",
    "m": "স", "n": "হ", "o": "ড়", "p": "ঢ়", "q": "য়",
    "r": "ৎ", "s": "ং", "t": "ঃ", "u": "ঁ",
    "A": "অ", "B": "ই", "C": "ঈ", "D": "উ", "E": "ঊ",
    "F": "ঋ", "G": "এ", "H": "ঐ", "I": "ও", "J": "ঔ",
    "0": "০", "1": "১", "2": "২", "3": "৩", "4": "৪",
    "5": "৫", "6": "৬", "7": "৭", "8": "৮", "9": "৯",
    "v": "া", "x": "ী", "y": "ু", "z": "ু", "~": "ূ",
    "ƒ": "ূ", "…": "ৃ", "„": "ৃ", "Š": "ৌ", "Œ": "ৌ",
    "|": "।", "||": "॥", "&": "্",
    # Common SutonnyMJ conjuncts & ligatures
    "ÿ": "ক্ষ", "¶": "ক্ষ", "Á": "জ্ঞ", "Â": "ঞ্ছ", "Ã": "ঞ্জ",
    "Ä": "ণ্ঠ", "Å": "ণ্ড", "Æ": "ত্ত", "Ç": "ত্ব", "È": "ত্থ",
    "É": "ত্র", "Ê": "দ্দ", "Ë": "দ্ধ", "Ì": "দ্ব", "Í": "দ্ম",
    "Î": "ন্ঠ", "Ï": "ন্ড", "Ð": "ন্ত", "Ñ": "ন্ত", "Ò": "ন্দ",
    "Ó": "ন্ধ", "Ô": "ন্ন", "Õ": "প্ট", "Ö": "প্ত", "×": "প্ল",
    "Ø": "প্স", "Ù": "ফ্ল", "Ú": "ব্জ", "Û": "ব্দ", "Ü": "ব্ধ",
    "Ý": "ব্ল", "Þ": "ভ্র", "ß": "ম্ন", "à": "ম্প", "á": "ম্ফ",
    "â": "ম্ব", "ã": "ম্ভ", "ä": "ম্ম", "å": "ম্ল", "æ": "ল্ক",
    "ç": "ল্গ", "è": "ল্ট", "é": "ল্ড", "ê": "ল্প", "ë": "ল্ম",
    "ì": "ল্ল", "í": "শ্চ", "î": "শ্ছ", "ï": "শ্ন", "ð": "শ্চ",
    "ñ": "শ্ল", "ò": "ষ্ক", "ó": "ষ্ট", "ô": "ষ্ঠ", "õ": "ষ্ণ",
    "ö": "ষ্প", "÷": "ষ্ফ", "ø": "ষ্ম", "ù": "স্ক", "ú": "স্ট",
    "û": "স্ত", "ü": "স্থ", "ý": "স্ন", "þ": "স্প",
    "¡": "্ব", "¢": "্ব", "£": "্ভ", "¤": "্ম", "¥": "্য",
    "¦": "্য", "§": "্র", "¨": "্র", "ª": "্র", "«": "্র",
    "¬": "্ল", "®": "্ন", "¯": "্ত", "°": "্ক", "±": "্খ",
    "²": "্গ", "³": "্ঘ", "´": "্ঙ", "µ": "্চ", "·": "্জ",
    "¸": "্ট", "¹": "্ড", "º": "্ণ", "»": "্ত", "¼": "্থ",
    "½": "্দ", "¾": "্ধ", "¿": "্ন", "À": "্প", "Ÿ": "্ব",
    "›": "্ল", "š": "্শ", "™": "্ষ", "˜": "্স", "–": "-", "—": "-",
}

# Pre-base / Multi-key Bijoy combinations processed before single chars
_BIJOY_MULTI: tuple[tuple[str, str], ...] = (
    ("Av", "আ"),
    ("G¨", "এ্যা"),
    ("A¨", "অ্যা"),
    ("ª¨", "্র্যা"),
    ("&¨", "্যা"),
    ("iv", "রা"),
    ("wi", "রি"),
    ("ex", "বী"),
    ("K¬", "ক্ল"),
    ("M¬", "গ্ল"),
    ("e¬", "ব্ল"),
    ("k¬", "শ্ল"),
    ("m¬", "স্ল"),
    ("iƒ", "রূ"),
    ("iæ", "রু"),
    ("kª", "শ্র"),
    ("Z¡", "ত্ব"),
    ("Z¨", "ত্য"),
    ("`¡", "দ্ব"),
    ("eŸ", "ব্ব"),
    ("mŸ", "স্ব"),
    ("bœ", "ন্ন"),
    ("gœ", "ম্ন"),
    ("j¥", "ল্য"),
    ("K¡", "ক্ব"),
    ("k¦", "শ্ব"),
    ("cÖ", "প্র"),
    ("eª", "ব্র"),
    ("Mª", "গ্র"),
    ("Kª", "ক্র"),
    ("Zª", "ত্র"),
    ("`ª", "দ্র"),
    ("fª", "ভ্র"),
    ("gª", "ম্র"),
    ("bœ", "ন্ন"),
)

_BIJOY_PRE_E = {"‡", "†"}
_BIJOY_PRE_OI = {"‰", "ˆ"}
_BIJOY_PRE_I = {"w"}
_BIJOY_REPH = {"©"}

_BIJOY_MARKER_RE = re.compile(r"[‡†‰ˆ©ª¡ŸðÿÁÂÃÄÅÇÉËÐÑÒÓÔØÚÜÞß]|(?:Av|vw|Kvi|gvw|wb)")


def is_likely_bijoy(text: str) -> bool:
    if not text:
        return False
    # If already contains Unicode Bengali letters, don't blindly Bijoy-decode the whole string
    if re.search(r"[\u0980-\u09FF]", text):
        return False
    markers = len(_BIJOY_MARKER_RE.findall(text))
    return markers >= 1


def bijoy_to_unicode(text: str) -> str:
    """Convert SutonnyMJ / Bijoy ANSI encoded Bengali string into NFC Unicode."""
    if not text or not is_likely_bijoy(text):
        return fix_unicode_nfc(text)

    out: list[str] = []
    i = 0
    n = len(text)
    pending_pre_i = False
    pending_pre_e = False
    pending_pre_oi = False

    def _flush_vowel(buf: list[str]) -> None:
        nonlocal pending_pre_i, pending_pre_e, pending_pre_oi
        if pending_pre_i:
            buf.append("ি")
            pending_pre_i = False
        elif pending_pre_e:
            buf.append("ে")
            pending_pre_e = False
        elif pending_pre_oi:
            buf.append("ৈ")
            pending_pre_oi = False

    while i < n:
        ch = text[i]
        # Spaces/punctuation break any dangling pre-vowel
        if ch in " \t\r\n-_()[]:;,!?/":
            _flush_vowel(out)
            out.append(ch)
            i += 1
            continue

        # Multi-character sequences
        matched_multi = False
        for pat, rep in _BIJOY_MULTI:
            if text.startswith(pat, i):
                # Special case: pre_e + C + v (া) -> ো
                out.append(rep)
                i += len(pat)
                matched_multi = True
                break
        if matched_multi:
            # Flush pending_pre_i immediately if no trailing conjunct/medial follows
            if (pending_pre_i or pending_pre_e or pending_pre_oi) and (
                i >= n or text[i] not in {"&", "¨", "¥", "¦", "ª", "«", "©", "v", "Š", "Œ"}
            ):
                if pending_pre_e and i < n and text[i] == "v":
                    out.append("ো")
                    pending_pre_e = False
                    i += 1
                elif pending_pre_e and i < n and text[i] in {"Š", "Œ"}:
                    out.append("ৌ")
                    pending_pre_e = False
                    i += 1
                else:
                    _flush_vowel(out)
            continue

        if ch in _BIJOY_PRE_I:
            pending_pre_i = True
            i += 1
            continue
        if ch in _BIJOY_PRE_E:
            pending_pre_e = True
            i += 1
            continue
        if ch in _BIJOY_PRE_OI:
            pending_pre_oi = True
            i += 1
            continue

        if ch in _BIJOY_REPH:
            # Reph attaches before the previous consonant cluster
            if out:
                last = out.pop()
                out.extend(["র্", last])
            else:
                out.append("র্")
            i += 1
            continue

        # Vowel combination after consonant with pending_pre_e
        if pending_pre_e and ch == "v":
            out.append("ো")
            pending_pre_e = False
            i += 1
            continue
        if pending_pre_e and ch in {"Š", "Œ"}:
            out.append("ৌ")
            pending_pre_e = False
            i += 1
            continue

        mapped = _BIJOY_CONSONANT_AND_SIGNS.get(ch, ch)
        out.append(mapped)
        i += 1

        # Wait to flush pre-base vowel if next token is hasanta/medial/vowel-right-half
        next_ch = text[i] if i < n else ""
        if next_ch not in {"&", "¨", "¥", "¦", "ª", "«", "v", "Š", "Œ", "¡", "¢", "¤", "Ÿ"}:
            # Handle ো and ৌ right halves if next_ch wasn't consumed above
            if pending_pre_e and next_ch == "v":
                continue
            if pending_pre_e and next_ch in {"Š", "Œ"}:
                continue
            _flush_vowel(out)

    _flush_vowel(out)
    res = "".join(out)
    # Clean up common Bijoy conversion artifacts
    res = res.replace("্‌", "্").replace("্র্", "র্")
    return fix_unicode_nfc(res)


# ---------------------------------------------------------------------------
# Unicode, extension, watermark & author cleanup
# ---------------------------------------------------------------------------
_CTRL_OR_BIDI_RE = re.compile(r"[\ufeff\u200e\u200f\u202a-\u202e\x00-\x1f\x7f]")

_WATERMARK_BRACKET_RE = re.compile(
    r"(?:"
    r"\[\[.*?\]\]"
    r"|\(\(XxX\)\)"
    r"|_+WriTeR_+"
    r"|[\[(]\s*Password[^)\]]*[\])]"
    r"|[\[(]\s*(?:www\.)?(?:amarboi|boighar|boimate|allbdbooks|allbanglaboi|islamibpoipdf|almodina|porageducation|pdfhorse|subahesadiq|purepdfbook|ebanglalibrary|bdebooks|banglapdf|priyoboi|banglainternet|yanabi|pathagar|archive|i-onlinemedia)[^)\]]*[\])]"
    r"|[\[(]\s*\d+\s*Pages?\s*,\s*[\d.]+\s*[KMG]B\s*,\s*[^\])]+[\])]"
    r"|[\[(]\s*www\.[^)\]]+[\])]"
    r"|[\[(]\s*Mockingbird@[^)\]]+[\])]"
    r"|@[a-z0-9.-]+\.[a-z]{2,}"
    r"|(?:https?://|www\.)\S+"
    r"|i-onlinemedia\.net\s*[-–—]*"
    r"|\s*[-–—]\s*(?:amarboi|boighar|almodina|banglapdf|bdebooks|ebanglalibrary|archive)\.(?:com|org|net|in|bd)\b"
    r"|\s*\[Akash\]"
    r")",
    re.I,
)

_EN_BN_AUTHOR_EQUIV: list[tuple[str, str]] = [
    ("william shakespeare", "উইলিয়াম শেক্সপিয়ার"),
    ("arthur conan doyle", "আর্থার কোনান ডয়েল"),
    ("leo tolstoy", "লিও তলস্তয়"),
    ("fyodor dostoevsky", "ফিওদোর দস্তয়েভস্কি"),
    ("charles dickens", "চার্লস ডিকেন্স"),
    ("mark twain", "মার্ক টোয়েন"),
    ("edgar allan poe", "এডগার অ্যালান পো"),
    ("george orwell", "জর্জ অরওয়েল"),
    ("franz kafka", "ফ্রানৎস কাফকা"),
    ("gabriel garcia marquez", "গাব্রিয়েল গার্সিয়া মার্কেস"),
    ("ernest hemingway", "আর্নেস্ট হেমিংওয়ে"),
    ("agatha christie", "আগাথা ক্রিস্টি"),
    ("jules verne", "জুল ভার্ন"),
    ("alexandre dumas", "আলেকজান্ডার দ্যুমা"),
    ("victor hugo", "ভিক্টর হুগো"),
    ("oscar wilde", "অস্কার ওয়াইল্ড"),
    ("jane austen", "জেন অস্টেন"),
    ("robert louis stevenson", "রবার্ট লুই স্টিভেনসন"),
    ("herman melville", "হারমান মেলভিল"),
    ("stephen hawking", "স্টিফেন হকিং"),
    ("albert einstein", "আলবার্ট আইনস্টাইন"),
    ("bertrand russell", "বার্ট্রান্ড রাসেল"),
    ("sigmund freud", "সিগমুন্ড ফ্রয়েড"),
    ("anton chekhov", "আন্তন চেখভ"),
    ("rabindranath tagore", "রবীন্দ্রনাথ ঠাকুর"),
    ("kazi nazrul islam", "কাজী নজরুল ইসলাম"),
    ("swami vivekananda", "স্বামী বিবেকানন্দ"),
    ("a c bhaktivedanta swami prabhupada", "স্বামী প্রভুপাদ"),
    ("bhaktivedanta swami prabhupada", "স্বামী প্রভুপাদ"),
    ("marcel proust", "মার্সেল প্রুস্ত"),
    ("randall garrett", "র্যান্ডাল গ্যারেট"),
    ("h p lovecraft", "এইচ পি লাভক্র্যাফট"),
    ("j r r tolkien", "জে আর আর টলকিন"),
    ("j k rowling", "জে কে রাউলিং"),
    ("stephen king", "স্টিফেন কিং"),
    ("dan brown", "ড্যান ব্রাউন"),
    ("paulo coelho", "পাওলো কোয়েলহো"),
    ("haruki murakami", "হারুকি মুরাকামি"),
    ("george r r martin", "জর্জ আর আর মার্টিন"),
    ("neil gaiman", "নিল গেইম্যান"),
]


def fix_unicode_nfc(text: str) -> str:
    if not text:
        return ""
    s = unicodedata.normalize("NFC", text)
    s = _CTRL_OR_BIDI_RE.sub("", s)
    s = re.sub(r"[ \t\r\n]+", " ", s).strip()
    return s


def fold_bengali_key(text: str) -> str:
    """Fold Bengali vowel length / nukta variants + whitespace for robust equality/dedupe checks."""
    s = fix_unicode_nfc(text).lower()
    # Fold long/short vowel marks and common spelling variants
    trans = str.maketrans({
        "ী": "ি",
        "ূ": "ু",
        "য়": "য়",
        "ড়": "ড়",
        "ঢ়": "ঢ়",
        "ং": "ঙ",
        "ঁ": "",
        "ঃ": "",
        "্": "",  # note: helpful when comparing transliterations like র‍্যান্ডাল vs র্যান্ডাল
        "\u200d": "",
        "\u200c": "",
    })
    s = s.translate(trans)
    # Strip punctuation for fuzzy author/title comparison
    s = re.sub(r"[\s\-–—_.,:;!?'\"`()\[\]{}|/\\]+", "", s)
    return s


def _authors_equivalent(a: str, b: str) -> bool:
    ka, kb = fold_bengali_key(a), fold_bengali_key(b)
    if not ka or not kb:
        return False
    if ka == kb:
        return True
    # Substring check when shorter author is at least 4 chars (e.g., "বেগম রোকেয়া" in "বেগম রোকেয়া সাখাওয়াত হোসেন")
    if len(ka) >= 4 and len(kb) >= 4 and (ka in kb or kb in ka):
        return True
    na = re.sub(r"[^a-z0-9\u0980-\u09ff ]+", " ", fix_unicode_nfc(a).lower()).strip()
    nb = re.sub(r"[^a-z0-9\u0980-\u09ff ]+", " ", fix_unicode_nfc(b).lower()).strip()
    for en, bn in _EN_BN_AUTHOR_EQUIV:
        eb_k = fold_bengali_key(bn)
        if (en in na or fold_bengali_key(en) == ka) and (eb_k in kb or kb in eb_k):
            return True
        if (en in nb or fold_bengali_key(en) == kb) and (eb_k in ka or ka in eb_k):
            return True
    return False


def split_clean_name_and_ext(filename: str, mime_type: str = "") -> tuple[str, str]:
    """Repair mangled extensions (. pdf, .pdf', ...) and return (stem, lower_ext)."""
    s = fix_unicode_nfc(filename)
    # Remove stray trailing quotes/spaces before parsing suffix
    s = re.sub(r"['\"\s]+$", "", s)
    # Handle '. pdf', ' .PDF', '(১)pdf'
    m = re.match(
        r"^(.*?)[\s.]+\s*(pdf|epub|json|docx?|txt|mobi|azw3?|kfx|opf|html?|xml|jpg|jpeg|png|webp|gif|bmp|svg|tiff|mp3|m4a|mp4|avi|mkv|mov|zip|rar|7z|apk|ini)$",
        s,
        re.I,
    )
    if m:
        stem, ext = m.group(1), "." + m.group(2).lower()
    else:
        m2 = re.match(r"^(.*\S)(pdf|epub|json)$", s, re.I)
        if m2 and not re.search(r"\.(pdf|epub|json)$", s, re.I):
            stem, ext = m2.group(1), "." + m2.group(2).lower()
        else:
            stem, ext = s, ""
    if not ext and mime_type == "application/pdf":
        ext = ".pdf"
    elif not ext and mime_type == "application/epub+zip":
        ext = ".epub"
    elif not ext and mime_type == "application/json":
        ext = ".json"
    return stem.strip(), ext


def strip_watermarks_and_noise(stem: str) -> str:
    s = fix_unicode_nfc(stem)
    if is_likely_bijoy(s):
        s = bijoy_to_unicode(s)
    # Strip Microsoft Word prefix in metadata titles
    s = re.sub(r"^Microsoft\s+Word\s*[-–—]\s*", "", s, flags=re.I)
    # Replace _WriTeR_ separator between title and author before general stripping
    s = re.sub(r"\s*_+WriTeR_+\s*", " - ", s, flags=re.I)
    s = _WATERMARK_BRACKET_RE.sub(" ", s)
    # Clean underscores used between words when mostly underscores around Bengali/Latin
    if s.count("_") >= 3 and " " not in s:
        s = s.replace("_", " ")
    else:
        s = re.sub(r"(?:\s+_+|\s*_+\s+)", " ", s)
    s = re.sub(r"[\s\-–—]+$", "", s)
    s = re.sub(r"^[\s\-–—]+", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def dedupe_trailing_authors(stem: str, known_author: str = "") -> str:
    """Collapse 'Title - Author - Author' or 'Title - EN Author - BN Author' cleanly."""
    s = fix_unicode_nfc(stem)
    parts = [p.strip() for p in re.split(r"\s+[-–—]\s+", s) if p.strip()]
    while len(parts) >= 3 and _authors_equivalent(parts[-2], parts[-1]):
        # Prefer the Bengali author segment if one is English and the other is Bengali
        prev, last = parts[-2], parts[-1]
        if re.search(r"[\u0980-\u09ff]", last):
            parts.pop(-2)
        else:
            parts.pop(-1)
    # Also check if final two parts are repeated via single hyphen without spaces on one side
    out = " - ".join(parts)
    if known_author:
        ka = fix_unicode_nfc(known_author)
        if parts and _authors_equivalent(parts[-1], ka):
            if fold_bengali_key(parts[-1]) == fold_bengali_key(ka) and len(ka) >= len(parts[-1]):
                parts[-1] = ka
                out = " - ".join(parts)
        elif ka and "Various" not in ka:
            if not any(_authors_equivalent(p, ka) for p in parts[1:]):
                out = f"{out} - {ka}" if out else ka
    return out


def sanitize_filename(stem: str, max_len: int = 160) -> str:
    s = fix_unicode_nfc(stem)
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', " ", s)
    s = re.sub(r"\s+", " ", s).strip(" ._-")
    if len(s) > max_len:
        s = s[:max_len].rstrip(" ._-")
    return s


def clean_book_stem(raw_stem: str, author: str = "", known_title: str = "") -> str:
    """Produce canonical clean book stem '<Title>' or '<Title - Author>'."""
    s = known_title.strip() if known_title.strip() else raw_stem
    s = strip_watermarks_and_noise(s)
    s = dedupe_trailing_authors(s, known_author=author)
    return sanitize_filename(s)


def clean_book_filename(raw_name: str, author: str = "", known_title: str = "", mime_type: str = "") -> str:
    stem, ext = split_clean_name_and_ext(raw_name, mime_type=mime_type)
    clean_stem = clean_book_stem(stem, author=author, known_title=known_title)
    if not clean_stem:
        clean_stem = sanitize_filename(stem) or "Untitled"
    return f"{clean_stem}{ext or '.pdf'}"


def is_opaque_stem(stem: str) -> bool:
    s = fix_unicode_nfc(stem)
    if not s or len(s) <= 2:
        return True
    if OPAQUE_STEM_RE.match(s):
        return True
    # Only underscores, punctuation, digits
    alnum_no_under = re.sub(r"[\s._\-\d\u09e6-\u09ef()+]+", "", s)
    if not alnum_no_under:
        return True
    return False


def match_keys(stem: str, author: str = "") -> tuple[str, str]:
    """Return canonical (title_key, author_key) for matching PDF + Text + Cover into one book folder."""
    s = strip_watermarks_and_noise(stem)
    s = dedupe_trailing_authors(s, known_author=author)
    parts = [p.strip() for p in re.split(r"\s+[-–—]\s+", s) if p.strip()]
    if len(parts) >= 2 and (author and _authors_equivalent(parts[-1], author) or len(parts) == 2):
        title_part = " - ".join(parts[:-1])
        author_part = author or parts[-1]
    elif author and fold_bengali_key(author) in fold_bengali_key(s):
        title_part = s
        author_part = author
    else:
        title_part = s
        author_part = author or ""
    return fold_bengali_key(title_part), fold_bengali_key(author_part)
