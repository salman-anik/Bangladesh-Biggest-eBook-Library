import type { FontScaleKey, ThemePresetKey } from './types';

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

export const DARK_THEME: ThemeTokens = {
  bg: '#11100F',
  surface: '#2D2826',
  surfaceAlt: '#1D1A18',
  surfaceDeep: '#0B0A09',
  cardDot: '#423B38',
  accent: '#C6927A',
  accentSoft: 'rgba(198, 146, 122, 0.18)',
  cream: '#F2ECE6',
  creamInk: '#171412',
  ink: '#F7F3EE',
  muted: '#9E9590',
  sage: '#5F7A6F',
  border: '#3D3532',
  borderSubtle: '#26211F',
  danger: '#D9736A',
};

export const LIGHT_THEME: ThemeTokens = {
  bg: '#FAF7F4',
  surface: '#FFFFFF',
  surfaceAlt: '#F2ECE6',
  surfaceDeep: '#E8E0D8',
  cardDot: '#DFD5CC',
  accent: '#B56E52',
  accentSoft: 'rgba(181, 110, 82, 0.14)',
  cream: '#221E1C',
  creamInk: '#FAF7F4',
  ink: '#171412',
  muted: '#6E6560',
  sage: '#4D6B5F',
  border: '#E5DDD5',
  borderSubtle: '#EFE8E1',
  danger: '#C94A4A',
};

export interface ThemePresetDefinition {
  label: string;
  swatches: [string, string, string];
  dark: ThemeTokens;
  light: ThemeTokens;
}

export const THEME_PRESETS: Record<ThemePresetKey, ThemePresetDefinition> = {
  espresso: {
    label: 'Espresso',
    swatches: ['#11100F', '#2D2826', '#C6927A'],
    dark: DARK_THEME,
    light: LIGHT_THEME,
  },
  matcha: {
    label: 'Matcha',
    swatches: ['#0F1613', '#1E2B24', '#8DB596'],
    dark: {
      bg: '#0F1613',
      surface: '#1E2B24',
      surfaceAlt: '#15201A',
      surfaceDeep: '#090F0C',
      cardDot: '#2B3B32',
      accent: '#8DB596',
      accentSoft: 'rgba(141, 181, 150, 0.18)',
      cream: '#EEF2EC',
      creamInk: '#0F1613',
      ink: '#F3F7F2',
      muted: '#8FA396',
      sage: '#6B997C',
      border: '#2D3F35',
      borderSubtle: '#1D2B24',
      danger: '#D9736A',
    },
    light: {
      bg: '#F5F8F4',
      surface: '#FFFFFF',
      surfaceAlt: '#EAF0E8',
      surfaceDeep: '#DDE6DA',
      cardDot: '#CFDCCF',
      accent: '#4C7A5B',
      accentSoft: 'rgba(76, 122, 91, 0.15)',
      cream: '#1B2A20',
      creamInk: '#F5F8F4',
      ink: '#142018',
      muted: '#5D6E62',
      sage: '#3E6B4E',
      border: '#D4E0D2',
      borderSubtle: '#E6EEE4',
      danger: '#C94A4A',
    },
  },
  midnight: {
    label: 'Midnight',
    swatches: ['#0C101C', '#1B2236', '#D8B26E'],
    dark: {
      bg: '#0C101C',
      surface: '#1B2236',
      surfaceAlt: '#131829',
      surfaceDeep: '#080B14',
      cardDot: '#2A334E',
      accent: '#D8B26E',
      accentSoft: 'rgba(216, 178, 110, 0.18)',
      cream: '#EDF0F8',
      creamInk: '#0C101C',
      ink: '#F5F7FC',
      muted: '#8E99B5',
      sage: '#5B8C85',
      border: '#2B3552',
      borderSubtle: '#1C2338',
      danger: '#DF6E6E',
    },
    light: {
      bg: '#F4F6FC',
      surface: '#FFFFFF',
      surfaceAlt: '#E9EEF8',
      surfaceDeep: '#DCE3F2',
      cardDot: '#CBD4EC',
      accent: '#4A5D9E',
      accentSoft: 'rgba(74, 93, 158, 0.14)',
      cream: '#192038',
      creamInk: '#F4F6FC',
      ink: '#12182B',
      muted: '#5D6782',
      sage: '#3F7670',
      border: '#D5DDF0',
      borderSubtle: '#E7ECF8',
      danger: '#C94A4A',
    },
  },
  sepia: {
    label: 'Sepia',
    swatches: ['#17120E', '#2C2119', '#D49B54'],
    dark: {
      bg: '#17120E',
      surface: '#2C2119',
      surfaceAlt: '#211812',
      surfaceDeep: '#100C09',
      cardDot: '#3E3024',
      accent: '#D49B54',
      accentSoft: 'rgba(212, 155, 84, 0.18)',
      cream: '#F5EAD8',
      creamInk: '#17120E',
      ink: '#F9F1E4',
      muted: '#A89886',
      sage: '#6D8262',
      border: '#423327',
      borderSubtle: '#2B211A',
      danger: '#D46A5E',
    },
    light: {
      bg: '#F7EFE2',
      surface: '#FFFBF3',
      surfaceAlt: '#EFE3CF',
      surfaceDeep: '#E3D3B8',
      cardDot: '#D6C2A3',
      accent: '#8B5A2B',
      accentSoft: 'rgba(139, 90, 43, 0.14)',
      cream: '#2B1F14',
      creamInk: '#FFFBF3',
      ink: '#241A10',
      muted: '#756352',
      sage: '#556B4B',
      border: '#DECBB0',
      borderSubtle: '#EBDEC9',
      danger: '#B8473E',
    },
  },
  rosewood: {
    label: 'Rosewood',
    swatches: ['#161014', '#2A1F26', '#D48E9B'],
    dark: {
      bg: '#161014',
      surface: '#2A1F26',
      surfaceAlt: '#1F171C',
      surfaceDeep: '#0E0A0D',
      cardDot: '#3C2C35',
      accent: '#D48E9B',
      accentSoft: 'rgba(212, 142, 155, 0.18)',
      cream: '#F6ECEF',
      creamInk: '#161014',
      ink: '#FAF2F4',
      muted: '#A38F96',
      sage: '#6B8A7E',
      border: '#403039',
      borderSubtle: '#2A1F26',
      danger: '#E06C75',
    },
    light: {
      bg: '#FBF5F7',
      surface: '#FFFFFF',
      surfaceAlt: '#F3E7EB',
      surfaceDeep: '#E8D6DC',
      cardDot: '#DFC7D0',
      accent: '#A65568',
      accentSoft: 'rgba(166, 85, 104, 0.14)',
      cream: '#2B1C22',
      creamInk: '#FBF5F7',
      ink: '#24171C',
      muted: '#78626A',
      sage: '#4F7366',
      border: '#E6D3DA',
      borderSubtle: '#F0E3E8',
      danger: '#C44755',
    },
  },
};

export const FONT_SCALE_MULT: Record<FontScaleKey, number> = {
  small: 0.9,
  normal: 1.0,
  large: 1.15,
};

export const THEME = DARK_THEME;

export const QUOTES = [
  {
    text: 'বই কিনে কেউ দেউলিয়া হয় না। জ্ঞানই মানুষের প্রকৃত মুক্তি ও আলোর পথ।',
    author: 'সৈয়দ মুজতবা আলী / Syed Mujtaba Ali',
  },
  {
    text: 'A room without books is like a body without a soul.',
    author: 'Marcus Tullius Cicero',
  },
  {
    text: 'The more that you read, the more things you will know. The more that you learn, the more places you will go.',
    author: 'Dr. Seuss',
  },
  {
    text: 'মানুষ তার বইয়ের সমান বড়; প্রতিটি পৃষ্ঠা নতুন এক পৃথিবীর দরজা খুলে দেয়।',
    author: 'Bangladesh eBook Library',
  },
  {
    text: 'Education is the most powerful weapon which you can use to change the world.',
    author: 'Nelson Mandela',
  },
];
