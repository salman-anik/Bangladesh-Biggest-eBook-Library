import React, { createContext, useContext, useMemo } from 'react';

import {
  DARK_THEME,
  FONT_SCALE_MULT,
  THEME_PRESETS,
  type ThemeTokens,
} from '../theme';
import type { FontScaleKey, ThemeMode, ThemePresetKey } from '../types';

interface ThemeContextValue {
  theme: ThemeTokens;
  mode: ThemeMode;
  preset: ThemePresetKey;
  fontScale: FontScaleKey;
  fontMult: number;
  fs: (base: number) => number;
  setThemeMode: (mode: ThemeMode) => void;
  setThemePreset: (preset: ThemePresetKey) => void;
  setFontScale: (scale: FontScaleKey) => void;
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: DARK_THEME,
  mode: 'dark',
  preset: 'espresso',
  fontScale: 'normal',
  fontMult: 1.0,
  fs: (base: number) => base,
  setThemeMode: () => {},
  setThemePreset: () => {},
  setFontScale: () => {},
});

interface ProviderProps {
  mode: ThemeMode;
  preset: ThemePresetKey;
  fontScale: FontScaleKey;
  onChangeMode: (mode: ThemeMode) => void;
  onChangePreset: (preset: ThemePresetKey) => void;
  onChangeFontScale: (scale: FontScaleKey) => void;
  children: React.ReactNode;
}

export function ThemeProvider({
  mode,
  preset,
  fontScale,
  onChangeMode,
  onChangePreset,
  onChangeFontScale,
  children,
}: ProviderProps) {
  const value = useMemo<ThemeContextValue>(() => {
    const chosenPreset = THEME_PRESETS[preset] || THEME_PRESETS.espresso;
    const theme = chosenPreset[mode] || DARK_THEME;
    const fontMult = FONT_SCALE_MULT[fontScale] ?? 1.0;
    return {
      theme,
      mode,
      preset,
      fontScale,
      fontMult,
      fs: (base: number) => Math.round(base * fontMult * 10) / 10,
      setThemeMode: onChangeMode,
      setThemePreset: onChangePreset,
      setFontScale: onChangeFontScale,
    };
  }, [mode, preset, fontScale, onChangeMode, onChangePreset, onChangeFontScale]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useAppTheme(): ThemeContextValue {
  return useContext(ThemeContext);
}
