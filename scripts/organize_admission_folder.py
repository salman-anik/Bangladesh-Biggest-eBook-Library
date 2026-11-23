#!/usr/bin/env python3
"""Organize Admission & Entrance Preparation (12bPXR_IlHukYrfJgC6wxSyzqq20H7pQd)
into a clean Level/Category -> Subcategory hierarchy with publisher & cross-category shortcuts.
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
sys.path.insert(0, str(ROOT / "scripts"))
from reorg_lib import (  # noqa: E402
    create_shortcut,
    flush_log,
    gdrive_ls,
    mkdir_item,
    move_item,
    rename_item,
)

ADMISSION_ROOT_ID = "12bPXR_IlHukYrfJgC6wxSyzqq20H7pQd"
UDVASH_EXISTING_FOLDER_ID = "1SZanPVyKs0dpwjQX4LdCmXalKeF-HnHa"
VITAMIN_EXISTING_FOLDER_ID = "1BF08M39InSxmqe_Vxx_q-C9vNYQozyhG"

# Complete deterministic mapping for all 122 physical PDFs:
# file_id: (primary_dest_path, [shortcut_dest_paths])
PDF_MAP: dict[str, tuple[str, list[str]]] = {
    # === 1. Medical & Dental Admission (29 PDFs) ===
    "1jU8AiOEj2tGXUGMdv-qp4heIGGORnZMA": (
        "Medical & Dental Admission/Medical Admission",
        [
            "Medical & Dental Admission/Dental Admission",
            "Publisher & Coaching Collections/Unmesh/Medical",
            "Publisher & Coaching Collections/Unmesh/Dental",
        ],
    ),
    "1iVBuHB0dMVhkTD9CLs6M2NU2KD_4EY7m": (
        "Medical & Dental Admission/Medical Admission",
        ["Publisher & Coaching Collections/Unmesh/Medical"],
    ),
    "1NQ76IaftP-RQiGdIOyzxUCOcT6Dx5jaN": (
        "Medical & Dental Admission/Previous Year Questions",
        [],
    ),
    "1cXgdS5TIqJikXaU0dGAn0flbrKXyDliB": (
        "Medical & Dental Admission/Question Banks",
        [
            "Medical & Dental Admission/Dental Admission",
            "Publisher & Coaching Collections/Other Publishers/Medico",
        ],
    ),
    "12bqTD5E2sdnrGgae_oxyqsprP7ciA0_j": (
        "Medical & Dental Admission/Model Tests",
        ["Publisher & Coaching Collections/Other Publishers/Joykoli"],
    ),
    "1Q0xTrOIVuTox1pJ7_hdmr-Yuq51a_sc8": (
        "Medical & Dental Admission/Solutions & Explanations",
        ["Publisher & Coaching Collections/Other Publishers/Retina"],
    ),
    "1lW7TbTi5Fp2qQ3IMgk1LSZO0JcWnxZTp": (
        "Medical & Dental Admission/Solutions & Explanations",
        ["Publisher & Coaching Collections/Unmesh/Model Tests"],
    ),
    "1ThniFEfMZb8Wl9brYCalU2-Lzom0dlEC": (
        "Medical & Dental Admission/Solutions & Explanations",
        ["Publisher & Coaching Collections/Unmesh/Model Tests"],
    ),
    "1V4eTrxkOHmvNwpFaX-XlM-93jtw8O2AF": (
        "Medical & Dental Admission/Solutions & Explanations",
        ["Publisher & Coaching Collections/Unmesh/Model Tests"],
    ),
    # Biology (8 PDFs)
    "1kt-CxXYbENNSUaioFVhUhE14x428qQ0V": (
        "Medical & Dental Admission/Subject-wise Preparation/Biology",
        ["Publisher & Coaching Collections/Other Publishers/Medico"],
    ),
    "1mnp4lnzqoAEAjJt5oxtgB7kaNf4-1OWE": (
        "Medical & Dental Admission/Subject-wise Preparation/Biology",
        ["Publisher & Coaching Collections/Other Publishers/Medico"],
    ),
    "18li0_s98r9BiJvv5EzJWs0ExwQqRMu6n": (
        "Medical & Dental Admission/Subject-wise Preparation/Biology",
        ["Publisher & Coaching Collections/Other Publishers/Medico"],
    ),
    "1X8qer3HXRWJekR0Bgq5-qoeKfsI0o_S4": (
        "Medical & Dental Admission/Subject-wise Preparation/Biology",
        ["Publisher & Coaching Collections/Other Publishers/Medico"],
    ),
    "1J9UL_30h38q8x2oYz6GhV_OA4JcdzG9y": (
        "Medical & Dental Admission/Subject-wise Preparation/Biology",
        ["Publisher & Coaching Collections/Unmesh/Medical"],
    ),
    "1yRxJeYH3pSl8DNeVz0QVdTpm_OOeEc3s": (
        "Medical & Dental Admission/Subject-wise Preparation/Biology",
        ["Publisher & Coaching Collections/Unmesh/Medical"],
    ),
    "1RP_7_t6y2V4VD62LliPcqQfjnXlJzcrt": (
        "Medical & Dental Admission/Subject-wise Preparation/Biology",
        ["Publisher & Coaching Collections/Unmesh/Medical"],
    ),
    "1kly2EpsGvqoX9TB-PCJC5FnF41Lpz5GR": (
        "Medical & Dental Admission/Subject-wise Preparation/Biology",
        ["Publisher & Coaching Collections/Unmesh/Medical"],
    ),
    # Chemistry (2 PDFs)
    "1ll6sD81pQSIgVLcAFI9FPCkuy1d2DHKB": (
        "Medical & Dental Admission/Subject-wise Preparation/Chemistry",
        ["Publisher & Coaching Collections/Other Publishers/Medico"],
    ),
    "1UlC7m2fxJLs8dO3sqz36yxndl8KbR06q": (
        "Medical & Dental Admission/Subject-wise Preparation/Chemistry",
        ["Publisher & Coaching Collections/Other Publishers/Medico"],
    ),
    # Physics (3 PDFs)
    "1ladwnQum5XcPAAdf5irWL5mfImOH__9h": (
        "Medical & Dental Admission/Subject-wise Preparation/Physics",
        ["Publisher & Coaching Collections/Other Publishers/Medico"],
    ),
    "1QmFKMOJXOF2idDIBD_1UctmfiR0pNxk_": (
        "Medical & Dental Admission/Subject-wise Preparation/Physics",
        ["Publisher & Coaching Collections/Other Publishers/Retina"],
    ),
    "1VVQV4eh1lbq8HFT5nAqpHsmMvIdaUdSl": (
        "Medical & Dental Admission/Subject-wise Preparation/Physics",
        ["Publisher & Coaching Collections/Other Publishers/Retina"],
    ),
    # English (2 PDFs)
    "1_Go-mzd15pf9boYbNI20nJZSrl2iRR_O": (
        "Medical & Dental Admission/Subject-wise Preparation/English",
        ["Publisher & Coaching Collections/Other Publishers/Medico"],
    ),
    "1jkQkIdjepppEEAhCATlahQ4rca4EU73X": (
        "Medical & Dental Admission/Subject-wise Preparation/English",
        ["Publisher & Coaching Collections/Unmesh/Medical"],
    ),
    # General Knowledge (5 PDFs)
    "1Grx9Lh5gZTXOcXfGC_a9u1LPMmtlNJkA": (
        "Medical & Dental Admission/Subject-wise Preparation/General Knowledge",
        ["Publisher & Coaching Collections/Other Publishers/Retina"],
    ),
    "1uvPdFIeWrp9p88reyFC_KuaroQkEZ5Fi": (
        "Medical & Dental Admission/Subject-wise Preparation/General Knowledge",
        ["Publisher & Coaching Collections/Other Publishers/Medico"],
    ),
    "1bZEhsJo_5xF9zjnXwEmMN_a4p0isOHjx": (
        "Medical & Dental Admission/Subject-wise Preparation/General Knowledge",
        ["Publisher & Coaching Collections/Other Publishers/Medico"],
    ),
    "1sWpE5ZAdLVlHtYnderQq94-Fp1aa9xol": (
        "Medical & Dental Admission/Subject-wise Preparation/General Knowledge",
        ["Publisher & Coaching Collections/Unmesh/Medical"],
    ),
    "1ANVzO9dEW6Y9-FINF7ktD31zUZntQAFc": (
        "Medical & Dental Admission/Subject-wise Preparation/General Knowledge",
        ["Publisher & Coaching Collections/Unmesh/Medical"],
    ),

    # === 2. University Admission (31 PDFs) ===
    # DU (3 PDFs)
    "1bt4pQ7U1DDRq7OmyySXw9ZxBvpH4SqNU": (
        "University Admission/Public Universities/University of Dhaka (DU)",
        ["Publisher & Coaching Collections/Other Publishers/ACS"],
    ),
    "1BC41rT1eMI8V3BvkR7hUX6kZOsPUaSxc": (
        "University Admission/Public Universities/University of Dhaka (DU)",
        ["Publisher & Coaching Collections/Other Publishers/ACS"],
    ),
    "1bqS7qzhpETJiTry5XdPDuBEMeHEjs_al": (
        "University Admission/Public Universities/University of Dhaka (DU)",
        ["Publisher & Coaching Collections/Other Publishers/Paragon & Panacea"],
    ),
    # RU (2 PDFs)
    "1MtbApxekbQE39cI2vkPQcazwkJ-uAnYN": (
        "University Admission/Public Universities/University of Rajshahi (RU)",
        ["Publisher & Coaching Collections/Other Publishers/Pankouri"],
    ),
    "1l0hfklv4-sF-kPSgTpMfZg4Xg1mLA5O3": (
        "University Admission/Public Universities/University of Rajshahi (RU)",
        [
            "Publisher & Coaching Collections/Xenon/University Admission",
            "Publisher & Coaching Collections/Xenon/Question Banks",
        ],
    ),
    # CU (2 PDFs)
    "1ds8JaVTX4cpLMFpB5ywJYR3zv4DQZqzu": (
        "University Admission/Public Universities/University of Chittagong (CU)",
        ["Publisher & Coaching Collections/Other Publishers/Joykoli"],
    ),
    "1ISr2If4n-Ycc4aWSLVqV8Ugvr46gfAsk": (
        "University Admission/Public Universities/University of Chittagong (CU)",
        ["Publisher & Coaching Collections/Other Publishers/Pankouri"],
    ),
    # JU (4 PDFs)
    "1S4veby1zEWZpJpK9T_A_yiBUW1e8r667": (
        "University Admission/Public Universities/Jahangirnagar University (JU)",
        ["Publisher & Coaching Collections/Other Publishers/Pankouri"],
    ),
    "10qgqqUHKVyyvETecHnV_HyGqbO0OnSqi": (
        "University Admission/Public Universities/Jahangirnagar University (JU)",
        ["Publisher & Coaching Collections/Other Publishers/Pankouri"],
    ),
    "1r0-vkznEDX9ie157Zh1YU4S58_74MRr3": (
        "University Admission/Public Universities/Jahangirnagar University (JU)",
        ["Publisher & Coaching Collections/Other Publishers/Pankouri"],
    ),
    "1pNwnxo-wqW87Z1X0TzH4HAvHEsKZEbCp": (
        "University Admission/Public Universities/Jahangirnagar University (JU)",
        ["Publisher & Coaching Collections/Other Publishers/Pankouri"],
    ),
    # Other Universities (9 PDFs)
    "18jVJ2Tf_mEfPmB8cQWtdUkkGe3tG18mN": (
        "University Admission/Public Universities/Other Universities",
        ["Publisher & Coaching Collections/Other Publishers/Expert"],
    ),
    "15JgBxrsi3YX7YrumpXECMGfjG4hKfZ6a": (
        "University Admission/Public Universities/Other Universities",
        ["Publisher & Coaching Collections/Other Publishers/Joykoli"],
    ),
    "12mVWIbDOSL3Kg-ukqJ9lc4w-2PXccupu": (
        "University Admission/Public Universities/Other Universities",
        ["Publisher & Coaching Collections/Other Publishers/Joykoli"],
    ),
    "1TDcZyWmhBkcNLSvoLCh-Tso8vwvZeHuf": (
        "University Admission/Public Universities/Other Universities",
        [
            "Publisher & Coaching Collections/Udvash/University",
            "Publisher & Coaching Collections/Udvash/Question Banks",
        ],
    ),
    "1FqctUevg3TpzS-hFP6PQ2vemdmb731CB": (
        "University Admission/Public Universities/Other Universities",
        [
            "Publisher & Coaching Collections/Udvash/University",
            "Publisher & Coaching Collections/Udvash/Question Banks",
        ],
    ),
    "1scDxYKS7_LjKqgw7vlLmg766CaLE27q1": (
        "University Admission/Public Universities/Other Universities",
        [
            "Publisher & Coaching Collections/Udvash/University",
            "Publisher & Coaching Collections/Udvash/Question Banks",
        ],
    ),
    "1hq86ooo2SXL23jcyq6kefNpEQKnLjKyK": (
        "University Admission/Public Universities/Other Universities",
        [
            "Publisher & Coaching Collections/Udvash/University",
            "Publisher & Coaching Collections/Udvash/Question Banks",
        ],
    ),
    "1rmx1zzsZC86MTDHTPVNrAbDcRCWp5zJB": (
        "University Admission/Public Universities/Other Universities",
        ["Publisher & Coaching Collections/Udvash/University"],
    ),
    "1EBLCsJEOz72Xpm0TVeqv1Nu3PyG5fAGN": (
        "University Admission/Public Universities/Other Universities",
        ["Publisher & Coaching Collections/Udvash/University"],
    ),
    # GST Admission/A Unit (4 PDFs)
    "1deK-aMMXDnik_MPJeed-bH2FUuSVFW6F": (
        "University Admission/GST Admission/A Unit",
        ["Publisher & Coaching Collections/Other Publishers/GST Network"],
    ),
    "1e0gaFrUXEuS1HX4VLKsYutzO2aPZsRCq": (
        "University Admission/GST Admission/A Unit",
        ["Publisher & Coaching Collections/Other Publishers/GST Network"],
    ),
    "1FjyI8taiCl_ZNuHYNyYG1kCJjMiqIPEb": (
        "University Admission/GST Admission/A Unit",
        ["Publisher & Coaching Collections/Other Publishers/Joykoli"],
    ),
    "11PF3x2gy4tjs8VWqOe8CJSgX8U-XHpvs": (
        "University Admission/GST Admission/A Unit",
        [
            "Publisher & Coaching Collections/Xenon/University Admission",
            "Publisher & Coaching Collections/Xenon/Question Banks",
        ],
    ),
    # Private Universities (1 PDF)
    "1MW7O054CykJjfSgUAlmPAXMTXE-nWaus": (
        "University Admission/Private Universities",
        ["Publisher & Coaching Collections/Other Publishers/Mentors"],
    ),
    # Model Tests & Solutions (6 PDFs)
    "189XPPxI1kvGbTDD88iUZZAgf61lOO8N8": (
        "University Admission/Model Tests & Solutions",
        ["Publisher & Coaching Collections/Other Publishers/Focus"],
    ),
    "1rW1oeX-jh6I1xpM-V3KnVLGfncWBJWFm": (
        "University Admission/Model Tests & Solutions",
        ["Publisher & Coaching Collections/Other Publishers/Focus"],
    ),
    "11IZEfqSUQEC3VfO0d5nyZI7pddg4Xt1V": (
        "University Admission/Model Tests & Solutions",
        ["Publisher & Coaching Collections/Other Publishers/Focus"],
    ),
    "1-v7qNY-kH0MU4vI3fa3C_zsAKzCiakQj": (
        "University Admission/Model Tests & Solutions",
        ["Publisher & Coaching Collections/Other Publishers/Focus"],
    ),
    "1OvjQr8NGMA3pXQFz6qCOSf1j9dPv-fJw": (
        "University Admission/Model Tests & Solutions",
        ["Publisher & Coaching Collections/Other Publishers/Focus"],
    ),
    "1XnMAdaYlMQBcI2kWW69gtHaAKqfi4bh4": (
        "University Admission/Model Tests & Solutions",
        ["Publisher & Coaching Collections/Other Publishers/Paragon & Panacea"],
    ),

    # === 3. Engineering & Technology Admission (5 PDFs) ===
    "16JP4V61uXYdGBaGxlNvaioG8sMeYI9rI": (
        "Engineering & Technology Admission/CUET",
        [
            "Engineering & Technology Admission/Question Banks",
            "Publisher & Coaching Collections/Udvash/Engineering",
            "Publisher & Coaching Collections/Udvash/Question Banks",
        ],
    ),
    "1UcAk7KFcAZoHBjpw5-G-j_4B_kmVBkIk": (
        "Engineering & Technology Admission/KUET",
        [
            "Engineering & Technology Admission/Question Banks",
            "Publisher & Coaching Collections/Udvash/Engineering",
            "Publisher & Coaching Collections/Udvash/Question Banks",
        ],
    ),
    "1iFdEeJlsBsmIqMCC0bAoV_jHycGYKmcn": (
        "Engineering & Technology Admission/RUET",
        [
            "Engineering & Technology Admission/Question Banks",
            "Publisher & Coaching Collections/Udvash/Engineering",
            "Publisher & Coaching Collections/Udvash/Question Banks",
        ],
    ),
    "1nax7daEAIWCoGB5QACizOREW-yg0P9Hw": (
        "Engineering & Technology Admission/Other Engineering Universities",
        ["Publisher & Coaching Collections/Other Publishers/Joykoli"],
    ),
    "1xflRwbb1oqfTMyasAtN0qMWj3B106YPK": (
        "Engineering & Technology Admission/Model Tests & Solutions",
        ["Publisher & Coaching Collections/Udvash/Engineering"],
    ),

    # === 4. Agriculture Admission (7 PDFs) ===
    "1BeyUNqiHyEXlsQronLwiNisSikUKNMwM": (
        "Agriculture Admission/Agricultural Universities",
        ["Publisher & Coaching Collections/Other Publishers/Address Academy"],
    ),
    "11SXU2pJJoLOuhVMZnQtUILWeqWhqGGLm": (
        "Agriculture Admission/Combined Agriculture Admission",
        ["Publisher & Coaching Collections/Other Publishers/Address Academy"],
    ),
    "1dOkZiG7wLsm_gBQL3U__aNDfUdVB6Px1": (
        "Agriculture Admission/Combined Agriculture Admission",
        ["Publisher & Coaching Collections/Other Publishers/Joykoli"],
    ),
    "17JjEoRspd_szYx3VTL5GfkbZwXKUYE03": (
        "Agriculture Admission/Combined Agriculture Admission",
        [],  # existing shortcut 123aEekAUI95dkK2j8qorPbwBL8kiTs4y moved to Vitamin Admission Series/Question Banks
    ),
    "1gVXHioAuXJu3nsun6SRqxk6OtDhvYg-W": (
        "Agriculture Admission/Combined Agriculture Admission",
        [],  # existing shortcut 1WGnhkEbGl98vBNpICmn-BVon2oLzBEFC moved to Vitamin Admission Series/Question Banks
    ),
    "1DwXWhlQAQ-yFwqKTrVU5Swtq4SyB2q61": (
        "Agriculture Admission/Combined Agriculture Admission",
        [],  # existing shortcut 15zTouCrQ4FcPIzTLZFVIHaCuMqL6O-59 moved to Vitamin Admission Series/Question Banks
    ),
    "1dOeYe9cDWgSoa8IR8XdgTQj6A9F0ag1h": (
        "Agriculture Admission/Model Tests & Solutions",
        [],  # existing shortcut 1zpT1bDGCqUiSDooDSnkL7cqWDnLSFAlM moved to Udvash/University
    ),

    # === 5. HSC & Academic Preparation (44 PDFs) ===
    # Science/Physics (5 PDFs)
    "1tqj7W2FcdyhOzUNbluJbMFuY2UoJvjqb": (
        "HSC & Academic Preparation/Science/Physics",
        ["Publisher & Coaching Collections/Udvash/Question Banks"],  # existing shortcut -> Udvash/Academic
    ),
    "1P8temAOG31fh29FGxI90sm6hz7MlEHOT": (
        "HSC & Academic Preparation/Science/Physics",
        [
            "Publisher & Coaching Collections/Udvash/Academic",
            "Publisher & Coaching Collections/Udvash/Question Banks",
        ],
    ),
    "17FNfGTd7oMUTflmRVL_HPIe_yqfjEaxx": (
        "HSC & Academic Preparation/Science/Physics",
        [
            "Publisher & Coaching Collections/Udvash/Academic",
            "Publisher & Coaching Collections/Udvash/Question Banks",
        ],
    ),
    "1kwV1HLmKsd7SEKvX_zdkWEsZt34ToINE": (
        "HSC & Academic Preparation/Science/Physics",
        [
            "Publisher & Coaching Collections/Udvash/Academic",
            "Publisher & Coaching Collections/Udvash/Question Banks",
        ],
    ),
    "1fBBOFwptyY25m3sdzFlJJMJyrawJfz8J": (
        "HSC & Academic Preparation/Science/Physics",
        ["Publisher & Coaching Collections/Other Publishers/Panjeree"],
    ),
    # Science/Chemistry (5 PDFs)
    "1QZdJPMd1Y7exoInfuU9Jkma8xOyXD0tL": (
        "HSC & Academic Preparation/Science/Chemistry",
        [
            "Publisher & Coaching Collections/Udvash/Academic",
            "Publisher & Coaching Collections/Udvash/Question Banks",
        ],
    ),
    "12Wah2Ti7HmLSGFr57vGrYoBF0QOJRxP7": (
        "HSC & Academic Preparation/Science/Chemistry",
        [
            "Publisher & Coaching Collections/Udvash/Academic",
            "Publisher & Coaching Collections/Udvash/Question Banks",
        ],
    ),
    "1CxxcCeAyVvCBeBIAJl5nBH66ofKk4GNF": (
        "HSC & Academic Preparation/Science/Chemistry",
        [
            "Publisher & Coaching Collections/Udvash/Academic",
            "Publisher & Coaching Collections/Udvash/Question Banks",
        ],
    ),
    "1ImskHKv4wvc7NC2jdVsOFgOXJZZ2zVHw": (
        "HSC & Academic Preparation/Science/Chemistry",
        [
            "Publisher & Coaching Collections/Udvash/Academic",
            "Publisher & Coaching Collections/Udvash/Question Banks",
        ],
    ),
    "14_E90X8pMCCFMdFJNzfS4C07qoRvi8oj": (
        "HSC & Academic Preparation/Science/Chemistry",
        ["Publisher & Coaching Collections/Other Publishers/Panjeree"],
    ),
    # Science/Higher Mathematics (6 PDFs)
    "1ddutBnQRl8P7qkle4K3roqS-wvI90Oxu": (
        "HSC & Academic Preparation/Science/Higher Mathematics",
        ["Publisher & Coaching Collections/Udvash/Question Banks"],  # existing shortcut -> Udvash/Academic
    ),
    "160qGrWFX38MtSOar8d9VhCjtxPyj2ceJ": (
        "HSC & Academic Preparation/Science/Higher Mathematics",
        ["Publisher & Coaching Collections/Udvash/Question Banks"],  # existing shortcut -> Udvash/Academic
    ),
    "1NJToV0sU8KVE3xmxOckzIO8vQOwqFqM4": (
        "HSC & Academic Preparation/Science/Higher Mathematics",
        [
            "Publisher & Coaching Collections/Udvash/Academic",
            "Publisher & Coaching Collections/Udvash/Question Banks",
        ],
    ),
    "1EjuMDb-2MHvbyYmAnUWotV41aRcnYGDU": (
        "HSC & Academic Preparation/Science/Higher Mathematics",
        [
            "Publisher & Coaching Collections/Udvash/Academic",
            "Publisher & Coaching Collections/Udvash/Question Banks",
        ],
    ),
    "1drflt6TAiwP980rsfiH1ryHb3Sp5PqTk": (
        "HSC & Academic Preparation/Science/Higher Mathematics",
        ["Publisher & Coaching Collections/Other Publishers/Panjeree"],
    ),
    "1kxLY_b9GP-DZe4yxwqE2MlriF5YE5dfg": (
        "HSC & Academic Preparation/Science/Higher Mathematics",
        ["Publisher & Coaching Collections/Other Publishers/Panjeree"],
    ),
    # Science/Biology (4 PDFs)
    "13cZDx7F_Jh_kbcfV7kXAfLOo6hXuKjPq": (
        "HSC & Academic Preparation/Science/Biology",
        ["Publisher & Coaching Collections/Udvash/Question Banks"],  # existing shortcut -> Udvash/Academic
    ),
    "1usLfTzaEDz7t_YiuhicZ9ZcIfT9-Oeiq": (
        "HSC & Academic Preparation/Science/Biology",
        [
            "Publisher & Coaching Collections/Udvash/Academic",
            "Publisher & Coaching Collections/Udvash/Question Banks",
        ],
    ),
    "1y-EPNExP1NwuxeX_b_IT86lL_5Gd9vxE": (
        "HSC & Academic Preparation/Science/Biology",
        [
            "Publisher & Coaching Collections/Udvash/Academic",
            "Publisher & Coaching Collections/Udvash/Question Banks",
        ],
    ),
    "1ZJC-aeJatx0fgHxJEeJeG6zQDPW25uh4": (
        "HSC & Academic Preparation/Science/Biology",
        ["Publisher & Coaching Collections/Other Publishers/Panjeree"],
    ),
    # Humanities (5 PDFs)
    "1tB5jdhaP2oE6TkO5NkwKa7ervbDumHdf": (
        "HSC & Academic Preparation/Humanities",
        ["Publisher & Coaching Collections/Other Publishers/Panjeree"],
    ),
    "1aOBMWUB2ZzuxCD5zb29FGf2MFgbo1zCH": (
        "HSC & Academic Preparation/Humanities",
        ["Publisher & Coaching Collections/Other Publishers/Panjeree"],
    ),
    "15ZlKyB0zPaHGVLE3fMb7ERS3Kg-gjJWK": (
        "HSC & Academic Preparation/Humanities",
        ["Publisher & Coaching Collections/Other Publishers/Panjeree"],
    ),
    "1BYJrKA0Fl3Utfho1wXVBQTKTap10Vlgg": (
        "HSC & Academic Preparation/Humanities",
        ["Publisher & Coaching Collections/Other Publishers/Panjeree"],
    ),
    "1lhG7Zp5OJAawQB2Sc3XcKByVwKC7ZPPw": (
        "HSC & Academic Preparation/Humanities",
        ["Publisher & Coaching Collections/Other Publishers/Panjeree"],
    ),
    # Business Studies (2 PDFs)
    "1Emsmaw85YsFWn9BhncLqIMtvj2AAECA_": (
        "HSC & Academic Preparation/Business Studies",
        ["Publisher & Coaching Collections/Other Publishers/Panjeree"],
    ),
    "1ZKW5CW5I8HZUEBO43j3d7wJ7PJH-H-yG": (
        "HSC & Academic Preparation/Business Studies",
        ["Publisher & Coaching Collections/Other Publishers/Panjeree"],
    ),
    # Board Questions (17 PDFs)
    "1eSNFlFFJ4ch078_c2wWwMSvqbHMU63pn": (
        "HSC & Academic Preparation/Board Questions",
        [
            "Publisher & Coaching Collections/Udvash/Academic",
            "Publisher & Coaching Collections/Udvash/Question Banks",
        ],
    ),
    "13HUpwz0CUsw3mCFPUZL3_ZeJd1riuOIY": (
        "HSC & Academic Preparation/Board Questions",
        ["Publisher & Coaching Collections/Udvash/Question Banks"],  # existing shortcut -> Udvash/Academic
    ),
    "18DWmNtMzS1HoHcXnialduxjI7VWbk5Sq": (
        "HSC & Academic Preparation/Board Questions",
        ["Publisher & Coaching Collections/Udvash/Question Banks"],  # existing shortcut -> Udvash/Academic
    ),
    "1jFMNfl5yhLvsiyEhkfhd-AikvNC-dwO8": (
        "HSC & Academic Preparation/Board Questions",
        [
            "Publisher & Coaching Collections/Udvash/Academic",
            "Publisher & Coaching Collections/Udvash/Question Banks",
        ],
    ),
    "1vIHw_NdWAAw4bQ9vFJb1fQWjvG223vXs": (
        "HSC & Academic Preparation/Board Questions",
        ["Publisher & Coaching Collections/Udvash/Question Banks"],  # existing shortcut -> Udvash/Academic
    ),
    "1N3x2BXmzkuIlcq7m47JTWTrn8X4D6Gt-": (
        "HSC & Academic Preparation/Board Questions",
        [
            "Publisher & Coaching Collections/Udvash/Academic",
            "Publisher & Coaching Collections/Udvash/Question Banks",
        ],
    ),
    "1Pd7_20tasKDNOXoDNtHp7g9GMzP0cNd6": (
        "HSC & Academic Preparation/Board Questions",
        [
            "Publisher & Coaching Collections/Udvash/Academic",
            "Publisher & Coaching Collections/Udvash/Question Banks",
        ],
    ),
    "11i1oTAq7MIUsgulP0UAzotjxXiPi_Qnk": (
        "HSC & Academic Preparation/Board Questions",
        [
            "Publisher & Coaching Collections/Udvash/Academic",
            "Publisher & Coaching Collections/Udvash/Question Banks",
        ],
    ),
    "1BI8Pi0lRzm-wF7fVUymuUreAGzXsaWTf": (
        "HSC & Academic Preparation/Board Questions",
        [
            "Publisher & Coaching Collections/Udvash/Academic",
            "Publisher & Coaching Collections/Udvash/Question Banks",
        ],
    ),
    "1OWL4RGnoO9Kxybydnb2_aBIAzM2pIoW6": (
        "HSC & Academic Preparation/Board Questions",
        ["Publisher & Coaching Collections/Other Publishers/Panjeree"],
    ),
    "1b3aNcwV7NCTvBfWqgjfi07hI0Z8NF553": (
        "HSC & Academic Preparation/Board Questions",
        ["Publisher & Coaching Collections/Other Publishers/Panjeree"],
    ),
    "1rt3c0_ZvcQLwF33t89v6ntXqP-xA67uF": (
        "HSC & Academic Preparation/Board Questions",
        ["Publisher & Coaching Collections/Other Publishers/Panjeree"],
    ),
    "1eAYyyHDRjGfPJzWmHo11570o2kJhNh2r": (
        "HSC & Academic Preparation/Board Questions",
        ["Publisher & Coaching Collections/Other Publishers/Panjeree"],
    ),
    "1rTGvamESfKYP0jOLD9DjkRTKhNqs2epd": (
        "HSC & Academic Preparation/Board Questions",
        ["Publisher & Coaching Collections/Other Publishers/Panjeree"],
    ),
    "1wcnyCOF-VxeCzCIwTxbqxJzwWv_hsLod": (
        "HSC & Academic Preparation/Board Questions",
        ["Publisher & Coaching Collections/Other Publishers/Panjeree"],
    ),
    "1Gt68rMjArla3qHz2CshBYbCKvpwIeA99": (
        "HSC & Academic Preparation/Board Questions",
        ["Publisher & Coaching Collections/Other Publishers/Panjeree"],
    ),
    "19CMHezRoCPVUZiDkHwR7iUEjEmozRrws": (
        "HSC & Academic Preparation/Board Questions",
        ["Publisher & Coaching Collections/Other Publishers/Panjeree"],
    ),

    # === 6. General Competitive Exams (6 PDFs) ===
    "1O0KWwO6xn1qjnSS1oD4J8fW2oGWZgvq4": (
        "General Competitive Exams/Government Jobs",
        ["University Admission/Model Tests & Solutions"],
    ),
    "1k4gag5MtpX8pc_mvSxsezIK70QKjRLyb": (
        "General Competitive Exams/Nursing",
        ["Publisher & Coaching Collections/Other Publishers/Neuron"],
    ),
    "1FaS5HIginpFbhU7SoYgFMbcaXIMEEwek": (
        "General Competitive Exams/English Proficiency",
        [],
    ),
    "1qT9-0_wuiHOJg_G02Ivdn5_SS57AnrtL": (
        "General Competitive Exams/English Proficiency",
        [],
    ),
    "1rLt4JbStOysUVLjCx4bMhG32YAHt0adq": (
        "General Competitive Exams/English Proficiency",
        [],
    ),
    "1g4ZI0RkR66XuFiWsVJF5wcXQXnGvEgcv": (
        "General Competitive Exams/IQ & Analytical Reasoning",
        ["University Admission/Model Tests & Solutions"],
    ),
}

# Existing shortcuts inside Udvash (1SZanPVyKs0dpwjQX4LdCmXalKeF-HnHa) and Vitamin (1BF08M39InSxmqe_Vxx_q-C9vNYQozyhG)
EXISTING_SHORTCUT_MOVES: dict[str, tuple[str, str]] = {
    "1zpT1bDGCqUiSDooDSnkL7cqWDnLSFAlM": (UDVASH_EXISTING_FOLDER_ID, "Publisher & Coaching Collections/Udvash/University"),
    "1A3rtAL_-4gEW4PJnmOYdQ4JmHdzMgy5i": (UDVASH_EXISTING_FOLDER_ID, "Publisher & Coaching Collections/Udvash/Academic"),
    "1s5e0bdtH8mUxl6o1MmAEkUXOZqMIos60": (UDVASH_EXISTING_FOLDER_ID, "Publisher & Coaching Collections/Udvash/Academic"),
    "1PGeWbCbPkTjXadQ_os71e3xph-4ofJu7": (UDVASH_EXISTING_FOLDER_ID, "Publisher & Coaching Collections/Udvash/Academic"),
    "18T_tA5nuai1Wa7wKv4_E6zYEPLBC_u7O": (UDVASH_EXISTING_FOLDER_ID, "Publisher & Coaching Collections/Udvash/Academic"),
    "1Z_qcvl6_0Gm63EwZl9hvdZzJpRQIgpAy": (UDVASH_EXISTING_FOLDER_ID, "Publisher & Coaching Collections/Udvash/Academic"),
    "1cKUHHawhitHz_71y0wd13brZO0Nt182c": (UDVASH_EXISTING_FOLDER_ID, "Publisher & Coaching Collections/Udvash/Academic"),
    "1-uFN4HSxyf9qIklbQes07S4GjIHiP4V9": (UDVASH_EXISTING_FOLDER_ID, "Publisher & Coaching Collections/Udvash/Academic"),
    "123aEekAUI95dkK2j8qorPbwBL8kiTs4y": (VITAMIN_EXISTING_FOLDER_ID, "Publisher & Coaching Collections/Vitamin Admission Series/Question Banks"),
    "1WGnhkEbGl98vBNpICmn-BVon2oLzBEFC": (VITAMIN_EXISTING_FOLDER_ID, "Publisher & Coaching Collections/Vitamin Admission Series/Question Banks"),
    "15zTouCrQ4FcPIzTLZFVIHaCuMqL6O-59": (VITAMIN_EXISTING_FOLDER_ID, "Publisher & Coaching Collections/Vitamin Admission Series/Question Banks"),
}


def collect_live_items() -> tuple[dict[str, dict], dict[str, dict], dict[str, dict]]:
    pdfs: dict[str, dict] = {}
    shortcuts: dict[str, dict] = {}
    folders: dict[str, dict] = {"": {"id": ADMISSION_ROOT_ID, "name": "Admission & Entrance Preparation"}}

    def walk(fid: str, rel: str = "") -> None:
        for it in gdrive_ls(fid):
            mt = it.get("mimeType")
            if mt == "application/vnd.google-apps.folder":
                p = f"{rel}/{it['name']}" if rel else it["name"]
                folders[p] = {**it, "parent_id": fid}
                walk(it["id"], p)
            elif mt == "application/vnd.google-apps.shortcut":
                shortcuts[it["id"]] = {**it, "parent_id": fid, "folder": rel}
            else:
                pdfs[it["id"]] = {**it, "parent_id": fid, "folder": rel}

    walk(ADMISSION_ROOT_ID)
    return pdfs, shortcuts, folders


def main() -> None:
    print("Scanning live items inside Admission & Entrance Preparation...", flush=True)
    live_pdfs, live_shortcuts, live_folders = collect_live_items()
    print(f"Live audit: {len(live_pdfs)} PDFs, {len(live_shortcuts)} shortcuts, {len(live_folders)-1} subfolders", flush=True)

    missing_from_map = set(live_pdfs) - set(PDF_MAP)
    extra_in_map = set(PDF_MAP) - set(live_pdfs)
    assert not missing_from_map, f"Unmapped PDFs found in folder: {missing_from_map}"
    assert not extra_in_map, f"Expected PDFs missing from folder: {extra_in_map}"
    assert len(live_pdfs) == 122, f"Expected 122 PDFs, found {len(live_pdfs)}"

    # 1. Create folder hierarchy (only folders that will receive content)
    needed_paths: set[str] = set()
    for dest, sc_dests in PDF_MAP.values():
        needed_paths.add(dest)
        needed_paths.update(sc_dests)
    for _, sc_dest in EXISTING_SHORTCUT_MOVES.values():
        needed_paths.add(sc_dest)

    all_folder_prefixes: set[str] = set()
    for p in needed_paths:
        parts = p.split("/")
        for i in range(1, len(parts) + 1):
            all_folder_prefixes.add("/".join(parts[:i]))

    folder_ids: dict[str, str] = {"": ADMISSION_ROOT_ID}
    for p, finfo in live_folders.items():
        if p:
            folder_ids[p] = finfo["id"]

    # Create top-level & intermediate folders first
    pub_parent_path = "Publisher & Coaching Collections"
    if pub_parent_path not in folder_ids:
        folder_ids[pub_parent_path] = mkdir_item(pub_parent_path, ADMISSION_ROOT_ID)
    pub_parent_id = folder_ids[pub_parent_path]

    # Preserve existing Udvash & Vitamin folders by moving them under Publisher & Coaching Collections
    udvash_path = f"{pub_parent_path}/Udvash"
    if udvash_path not in folder_ids:
        udvash_info = next((v for v in live_folders.values() if v.get("id") == UDVASH_EXISTING_FOLDER_ID), None)
        assert udvash_info, "Existing Udvash folder not found!"
        if udvash_info["parent_id"] != pub_parent_id:
            move_item(UDVASH_EXISTING_FOLDER_ID, pub_parent_id, old_parent_id=udvash_info["parent_id"], name=udvash_info["name"])
        if udvash_info["name"] != "Udvash":
            rename_item(UDVASH_EXISTING_FOLDER_ID, "Udvash", old_name=udvash_info["name"])
        folder_ids[udvash_path] = UDVASH_EXISTING_FOLDER_ID

    vitamin_path = f"{pub_parent_path}/Vitamin Admission Series"
    if vitamin_path not in folder_ids:
        vit_info = next((v for v in live_folders.values() if v.get("id") == VITAMIN_EXISTING_FOLDER_ID), None)
        assert vit_info, "Existing Vitamin Admission Series folder not found!"
        if vit_info["parent_id"] != pub_parent_id:
            move_item(VITAMIN_EXISTING_FOLDER_ID, pub_parent_id, old_parent_id=vit_info["parent_id"], name=vit_info["name"])
        folder_ids[vitamin_path] = VITAMIN_EXISTING_FOLDER_ID

    for path in sorted(all_folder_prefixes, key=lambda s: (s.count("/"), s)):
        if path in folder_ids:
            continue
        parent_path, name = (path.rsplit("/", 1) if "/" in path else ("", path))
        folder_ids[path] = mkdir_item(name, folder_ids[parent_path])

    print(f"Ready with {len(folder_ids)-1} target folders.", flush=True)

    # 2. Move the 11 existing shortcuts into their target publisher subfolders
    sc_move_tasks = []
    for sc_id, (_, dest_path) in EXISTING_SHORTCUT_MOVES.items():
        if sc_id in live_shortcuts:
            cur_p = live_shortcuts[sc_id]["parent_id"]
            dst_p = folder_ids[dest_path]
            if cur_p != dst_p:
                sc_move_tasks.append((sc_id, dst_p, cur_p, live_shortcuts[sc_id]["name"]))

    # 3. Move all 122 physical PDFs to their primary category subfolders
    pdf_move_tasks = []
    for fid, (dest_path, _) in PDF_MAP.items():
        cur_p = live_pdfs[fid]["parent_id"]
        dst_p = folder_ids[dest_path]
        if cur_p != dst_p:
            pdf_move_tasks.append((fid, dst_p, cur_p, live_pdfs[fid]["name"]))

    move_errors: list[str] = []
    all_moves = sc_move_tasks + pdf_move_tasks
    print(f"Executing {len(pdf_move_tasks)} PDF moves + {len(sc_move_tasks)} existing shortcut moves...", flush=True)
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(move_item, fid, dst, cur, nm, True, True): nm for fid, dst, cur, nm in all_moves}
        done = 0
        for fut in as_completed(futs):
            done += 1
            try:
                fut.result()
            except Exception as exc:
                move_errors.append(f"{futs[fut]}: {exc}")
            if done % 25 == 0 or done == len(all_moves):
                print(f"  Moves progress: {done}/{len(all_moves)} (errors={len(move_errors)})", flush=True)

    assert not move_errors, f"Move errors encountered: {move_errors}"

    # 4. Create secondary & publisher shortcuts (checking existing folder contents for idempotency)
    shortcut_targets_needed: dict[str, set[str]] = {}
    for fid, (_, sc_paths) in PDF_MAP.items():
        for sp in sc_paths:
            shortcut_targets_needed.setdefault(sp, set()).add(fid)

    shortcut_tasks: list[tuple[str, str, str]] = []
    existing_sc_targets_by_folder: dict[str, set[str]] = {}
    for sp in sorted(shortcut_targets_needed):
        sfid = folder_ids[sp]
        items = gdrive_ls(sfid)
        existing_targets = set()
        for it in items:
            if it.get("mimeType") == "application/vnd.google-apps.shortcut":
                tid = (it.get("shortcutDetails") or {}).get("targetId")
                if tid:
                    existing_targets.add(tid)
                # Also match by exact name if shortcutDetails omitted
                existing_targets.add(it["name"])
            else:
                existing_targets.add(it["id"])
        existing_sc_targets_by_folder[sp] = existing_targets
        for fid in sorted(shortcut_targets_needed[sp]):
            fname = live_pdfs[fid]["name"]
            if fid not in existing_targets and fname not in existing_targets:
                shortcut_tasks.append((fid, sfid, f"{sp} <- {fname}"))

    sc_errors: list[str] = []
    print(f"Creating {len(shortcut_tasks)} publisher & cross-category shortcuts...", flush=True)
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(create_shortcut, fid, sfid, desc): desc for fid, sfid, desc in shortcut_tasks}
        done = 0
        for fut in as_completed(futs):
            done += 1
            try:
                fut.result()
            except Exception as exc:
                sc_errors.append(f"{futs[fut]}: {exc}")
            if done % 25 == 0 or done == len(shortcut_tasks):
                print(f"  Shortcuts progress: {done}/{len(shortcut_tasks)} (errors={len(sc_errors)})", flush=True)

    flush_log()
    assert not sc_errors, f"Shortcut errors encountered: {sc_errors}"

    # 5. Post-execution verification scan inside Admission & Entrance Preparation
    print("Running verification scan on Admission & Entrance Preparation...", flush=True)
    final_pdfs, final_shortcuts, final_folders = collect_live_items()
    root_stray_files = [x for x in gdrive_ls(ADMISSION_ROOT_ID) if x.get("mimeType") != "application/vnd.google-apps.folder"]
    empty_folders = []
    folder_counts: dict[str, dict[str, int]] = {}
    for p, finfo in sorted(final_folders.items()):
        if not p:
            continue
        direct_items = gdrive_ls(finfo["id"])
        if not direct_items:
            empty_folders.append(p)
        n_pdf = sum(1 for x in direct_items if x.get("mimeType") == "application/pdf")
        n_sc = sum(1 for x in direct_items if x.get("mimeType") == "application/vnd.google-apps.shortcut")
        if n_pdf or n_sc:
            folder_counts[p] = {"pdfs": n_pdf, "shortcuts": n_sc, "folder_id": finfo["id"]}

    missing_after = set(live_pdfs) - set(final_pdfs)
    assert not missing_after, f"Lost PDFs after reorg: {missing_after}"
    assert len(final_pdfs) == 122, f"Expected 122 PDFs after reorg, got {len(final_pdfs)}"
    assert len(root_stray_files) == 0, f"Root has stray files: {[x['name'] for x in root_stray_files]}"
    assert not empty_folders, f"Empty folders created: {empty_folders}"

    plan_records = []
    for fid, finfo in sorted(final_pdfs.items(), key=lambda kv: kv[1]["name"]):
        dest_path, sc_paths = PDF_MAP[fid]
        plan_records.append({
            "drive_file_id": fid,
            "filename": finfo["name"],
            "size_bytes": int(finfo.get("size") or 0),
            "primary_folder": dest_path,
            "primary_folder_id": folder_ids[dest_path],
            "shortcut_folders": sc_paths,
        })

    out = {
        "admission_root_id": ADMISSION_ROOT_ID,
        "total_pdfs_verified": len(final_pdfs),
        "total_shortcuts_verified": len(final_shortcuts),
        "total_subfolders_verified": len(final_folders) - 1,
        "root_stray_files": 0,
        "empty_folders": empty_folders,
        "pdf_moves_executed": len(pdf_move_tasks),
        "existing_shortcut_moves_executed": len(sc_move_tasks),
        "new_shortcuts_created": len(shortcut_tasks),
        "folder_ids": folder_ids,
        "folder_counts": folder_counts,
        "files": plan_records,
    }
    out_path = DATA / "admission_reorg_plan_and_result.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n=== ADMISSION REORG COMPLETE ===")
    print(f"PDFs: {len(final_pdfs)} | Shortcuts: {len(final_shortcuts)} | Folders: {len(final_folders)-1} | Stray root files: 0 | Empty folders: 0")
    print(f"Saved full plan & result to {out_path}")


if __name__ == "__main__":
    main()
