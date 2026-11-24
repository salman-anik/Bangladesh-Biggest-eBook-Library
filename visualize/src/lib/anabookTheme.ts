export type ThemeMode = "light" | "dark";

export type ThemePresetKey =
  | "espresso"
  | "matcha"
  | "midnight"
  | "sepia"
  | "rosewood";

export interface ThemeTokens {
  bg: string;
  surface: string;
  surfaceAlt: string;
  surfaceDeep: string;
  cardDot: string;
  accent: string;
  accentSoft: string;
  cream: string;
  creamInk: string;
  ink: string;
  muted: string;
  sage: string;
  border: string;
  borderSubtle: string;
  danger: string;
}

export interface ThemePresetDefinition {
  label: string;
  swatches: [string, string, string];
  dark: ThemeTokens;
  light: ThemeTokens;
}

export interface CategoryPalette {
  bg: string;
  border: string;
  orb: string;
  badgeBg: string;
  accent: string;
}

export interface BookProgress {
  bookId: string;
  currentPage: number;
  totalPages: number;
  progressPct: number;
  updatedAt: string;
}

export interface AuthorDetailRecord {
  name?: string;
  group?: string;
  shortDesc?: string;
  bio?: string;
  wikiUrl?: string;
}

export const DARK_THEME: ThemeTokens = {
  bg: "#11100F",
  surface: "#2D2826",
  surfaceAlt: "#1D1A18",
  surfaceDeep: "#0B0A09",
  cardDot: "#423B38",
  accent: "#C6927A",
  accentSoft: "rgba(198, 146, 122, 0.18)",
  cream: "#F2ECE6",
  creamInk: "#171412",
  ink: "#F7F3EE",
  muted: "#9E9590",
  sage: "#5F7A6F",
  border: "#3D3532",
  borderSubtle: "#26211F",
  danger: "#D9736A",
};

export const LIGHT_THEME: ThemeTokens = {
  bg: "#FAF7F4",
  surface: "#FFFFFF",
  surfaceAlt: "#F2ECE6",
  surfaceDeep: "#E8E0D8",
  cardDot: "#DFD5CC",
  accent: "#B56E52",
  accentSoft: "rgba(181, 110, 82, 0.14)",
  cream: "#221E1C",
  creamInk: "#FAF7F4",
  ink: "#171412",
  muted: "#6E6560",
  sage: "#4D6B5F",
  border: "#E5DDD5",
  borderSubtle: "#EFE8E1",
  danger: "#C94A4A",
};

export const THEME_PRESETS: Record<ThemePresetKey, ThemePresetDefinition> = {
  espresso: {
    label: "Espresso",
    swatches: ["#11100F", "#2D2826", "#C6927A"],
    dark: DARK_THEME,
    light: LIGHT_THEME,
  },
  matcha: {
    label: "Matcha",
    swatches: ["#0F1613", "#1E2B24", "#8DB596"],
    dark: {
      bg: "#0F1613",
      surface: "#1E2B24",
      surfaceAlt: "#15201A",
      surfaceDeep: "#090F0C",
      cardDot: "#2B3B32",
      accent: "#8DB596",
      accentSoft: "rgba(141, 181, 150, 0.18)",
      cream: "#EEF2EC",
      creamInk: "#0F1613",
      ink: "#F3F7F2",
      muted: "#8FA396",
      sage: "#6B997C",
      border: "#2D3F35",
      borderSubtle: "#1D2B24",
      danger: "#D9736A",
    },
    light: {
      bg: "#F5F8F4",
      surface: "#FFFFFF",
      surfaceAlt: "#EAF0E8",
      surfaceDeep: "#DDE6DA",
      cardDot: "#CFDCCF",
      accent: "#4C7A5B",
      accentSoft: "rgba(76, 122, 91, 0.15)",
      cream: "#1B2A20",
      creamInk: "#F5F8F4",
      ink: "#142018",
      muted: "#5D6E62",
      sage: "#3E6B4E",
      border: "#D4E0D2",
      borderSubtle: "#E6EEE4",
      danger: "#C94A4A",
    },
  },
  midnight: {
    label: "Midnight",
    swatches: ["#0C101C", "#1B2236", "#D8B26E"],
    dark: {
      bg: "#0C101C",
      surface: "#1B2236",
      surfaceAlt: "#131829",
      surfaceDeep: "#080B14",
      cardDot: "#2A334E",
      accent: "#D8B26E",
      accentSoft: "rgba(216, 178, 110, 0.18)",
      cream: "#EDF0F8",
      creamInk: "#0C101C",
      ink: "#F5F7FC",
      muted: "#8E99B5",
      sage: "#5B8C85",
      border: "#2B3552",
      borderSubtle: "#1C2338",
      danger: "#DF6E6E",
    },
    light: {
      bg: "#F4F6FC",
      surface: "#FFFFFF",
      surfaceAlt: "#E9EEF8",
      surfaceDeep: "#DCE3F2",
      cardDot: "#CBD4EC",
      accent: "#4A5D9E",
      accentSoft: "rgba(74, 93, 158, 0.14)",
      cream: "#192038",
      creamInk: "#F4F6FC",
      ink: "#12182B",
      muted: "#5D6782",
      sage: "#3F7670",
      border: "#D5DDF0",
      borderSubtle: "#E7ECF8",
      danger: "#C94A4A",
    },
  },
  sepia: {
    label: "Sepia",
    swatches: ["#17120E", "#2C2119", "#D49B54"],
    dark: {
      bg: "#17120E",
      surface: "#2C2119",
      surfaceAlt: "#211812",
      surfaceDeep: "#100C09",
      cardDot: "#3E3024",
      accent: "#D49B54",
      accentSoft: "rgba(212, 155, 84, 0.18)",
      cream: "#F5EAD8",
      creamInk: "#17120E",
      ink: "#F9F1E4",
      muted: "#A89886",
      sage: "#6D8262",
      border: "#423327",
      borderSubtle: "#2B211A",
      danger: "#D46A5E",
    },
    light: {
      bg: "#F7EFE2",
      surface: "#FFFBF3",
      surfaceAlt: "#EFE3CF",
      surfaceDeep: "#E3D3B8",
      cardDot: "#D6C2A3",
      accent: "#8B5A2B",
      accentSoft: "rgba(139, 90, 43, 0.14)",
      cream: "#2B1F14",
      creamInk: "#FFFBF3",
      ink: "#241A10",
      muted: "#756352",
      sage: "#556B4B",
      border: "#DECBB0",
      borderSubtle: "#EBDEC9",
      danger: "#B8473E",
    },
  },
  rosewood: {
    label: "Rosewood",
    swatches: ["#161014", "#2A1F26", "#D48E9B"],
    dark: {
      bg: "#161014",
      surface: "#2A1F26",
      surfaceAlt: "#1F171C",
      surfaceDeep: "#0E0A0D",
      cardDot: "#3C2C35",
      accent: "#D48E9B",
      accentSoft: "rgba(212, 142, 155, 0.18)",
      cream: "#F6ECEF",
      creamInk: "#161014",
      ink: "#FAF2F4",
      muted: "#A38F96",
      sage: "#6B8A7E",
      border: "#403039",
      borderSubtle: "#2A1F26",
      danger: "#E06C75",
    },
    light: {
      bg: "#FBF5F7",
      surface: "#FFFFFF",
      surfaceAlt: "#F3E7EB",
      surfaceDeep: "#E8D6DC",
      cardDot: "#DFC7D0",
      accent: "#A65568",
      accentSoft: "rgba(166, 85, 104, 0.14)",
      cream: "#2B1C22",
      creamInk: "#FBF5F7",
      ink: "#24171C",
      muted: "#78626A",
      sage: "#4F7366",
      border: "#E6D3DA",
      borderSubtle: "#F0E3E8",
      danger: "#C44755",
    },
  },
};

export const BENTO_PALETTES: Record<
  string,
  { dark: CategoryPalette; light: CategoryPalette }
> = {
  bangla: {
    dark: {
      bg: "#2B1815",
      border: "#4A2823",
      orb: "rgba(229, 128, 102, 0.16)",
      badgeBg: "rgba(0, 0, 0, 0.34)",
      accent: "#F2A38F",
    },
    light: {
      bg: "#FCEEE9",
      border: "#F0CFC3",
      orb: "rgba(210, 100, 72, 0.14)",
      badgeBg: "rgba(255, 255, 255, 0.85)",
      accent: "#9E4029",
    },
  },
  religion: {
    dark: {
      bg: "#132620",
      border: "#23453A",
      orb: "rgba(95, 194, 154, 0.16)",
      badgeBg: "rgba(0, 0, 0, 0.34)",
      accent: "#8BE0BC",
    },
    light: {
      bg: "#E8F5EF",
      border: "#C2E3D4",
      orb: "rgba(46, 138, 102, 0.14)",
      badgeBg: "rgba(255, 255, 255, 0.85)",
      accent: "#1F6B4E",
    },
  },
  education: {
    dark: {
      bg: "#161F33",
      border: "#283A5E",
      orb: "rgba(116, 160, 245, 0.16)",
      badgeBg: "rgba(0, 0, 0, 0.34)",
      accent: "#9CC0FF",
    },
    light: {
      bg: "#EBF1FC",
      border: "#C7D8F7",
      orb: "rgba(62, 108, 204, 0.14)",
      badgeBg: "rgba(255, 255, 255, 0.85)",
      accent: "#274E9E",
    },
  },
  authors: {
    dark: {
      bg: "#292012",
      border: "#4A381D",
      orb: "rgba(235, 182, 88, 0.16)",
      badgeBg: "rgba(0, 0, 0, 0.34)",
      accent: "#F4C97A",
    },
    light: {
      bg: "#FDF4E3",
      border: "#F2DAB0",
      orb: "rgba(196, 136, 36, 0.14)",
      badgeBg: "rgba(255, 255, 255, 0.85)",
      accent: "#8F5B0A",
    },
  },
  series: {
    dark: {
      bg: "#25172E",
      border: "#442A54",
      orb: "rgba(198, 132, 242, 0.16)",
      badgeBg: "rgba(0, 0, 0, 0.34)",
      accent: "#D8A6FC",
    },
    light: {
      bg: "#F4ECFA",
      border: "#DEC7F0",
      orb: "rgba(136, 68, 194, 0.14)",
      badgeBg: "rgba(255, 255, 255, 0.85)",
      accent: "#6B2A9E",
    },
  },
  reference: {
    dark: {
      bg: "#122429",
      border: "#21424B",
      orb: "rgba(86, 198, 214, 0.16)",
      badgeBg: "rgba(0, 0, 0, 0.34)",
      accent: "#8AE0EC",
    },
    light: {
      bg: "#E7F6F8",
      border: "#BFE4EA",
      orb: "rgba(34, 140, 158, 0.14)",
      badgeBg: "rgba(255, 255, 255, 0.85)",
      accent: "#126473",
    },
  },
  english: {
    dark: {
      bg: "#2C1622",
      border: "#4D263C",
      orb: "rgba(238, 120, 174, 0.16)",
      badgeBg: "rgba(0, 0, 0, 0.34)",
      accent: "#F69EC5",
    },
    light: {
      bg: "#FCECF3",
      border: "#F2C7DA",
      orb: "rgba(194, 58, 118, 0.14)",
      badgeBg: "rgba(255, 255, 255, 0.85)",
      accent: "#992257",
    },
  },
  slate: {
    dark: {
      bg: "#1F2024",
      border: "#35373F",
      orb: "rgba(164, 170, 186, 0.15)",
      badgeBg: "rgba(0, 0, 0, 0.34)",
      accent: "#C2C7D4",
    },
    light: {
      bg: "#F1F2F5",
      border: "#D7DBE2",
      orb: "rgba(104, 112, 128, 0.13)",
      badgeBg: "rgba(255, 255, 255, 0.85)",
      accent: "#454C59",
    },
  },
};

const BENTO_FALLBACK_KEYS = [
  "bangla",
  "religion",
  "education",
  "authors",
  "series",
  "reference",
  "english",
  "slate",
] as const;

export function getCategoryPalette(
  name: string,
  mode: ThemeMode
): CategoryPalette {
  const low = (name || "").toLowerCase();
  let key: (typeof BENTO_FALLBACK_KEYS)[number] | undefined;
  if (low.includes("bangla books")) key = "bangla";
  else if (low.includes("religion")) key = "religion";
  else if (low.includes("education")) key = "education";
  else if (low.includes("authors")) key = "authors";
  else if (low.includes("series")) key = "series";
  else if (low.includes("reference")) key = "reference";
  else if (low.includes("english")) key = "english";
  else if (low.includes("review") || low.includes("unclassified")) key = "slate";

  if (!key) {
    let hash = 0;
    for (let i = 0; i < low.length; i++) {
      hash = (hash * 31 + low.charCodeAt(i)) >>> 0;
    }
    key = BENTO_FALLBACK_KEYS[hash % BENTO_FALLBACK_KEYS.length];
  }
  return BENTO_PALETTES[key][mode];
}

export const QUOTES = [
  {
    text: "বই কিনে কেউ দেউলিয়া হয় না। জ্ঞানই মানুষের প্রকৃত মুক্তি ও আলোর পথ।",
    author: "সৈয়দ মুজতবা আলী / Syed Mujtaba Ali",
  },
  {
    text: "A room without books is like a body without a soul.",
    author: "Marcus Tullius Cicero",
  },
  {
    text: "The more that you read, the more things you will know. The more that you learn, the more places you will go.",
    author: "Dr. Seuss",
  },
  {
    text: "মানুষ তার বইয়ের সমান বড়; প্রতিটি পৃষ্ঠা নতুন এক পৃথিবীর দরজা খুলে দেয়।",
    author: "Bangladesh eBook Library",
  },
  {
    text: "Education is the most powerful weapon which you can use to change the world.",
    author: "Nelson Mandela",
  },
];
