"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  THEME_PRESETS,
  ThemeMode,
  ThemePresetKey,
  ThemeTokens,
} from "@/lib/anabookTheme";
import { STORAGE_KEYS } from "@/lib/userLibraryStore";

const PRESET_ORDER: ThemePresetKey[] = [
  "espresso",
  "matcha",
  "midnight",
  "sepia",
  "rosewood",
];

interface WebThemeContextValue {
  presetKey: ThemePresetKey;
  themeMode: ThemeMode;
  theme: ThemeTokens;
  hydrated: boolean;
  setPresetKey: (key: ThemePresetKey) => void;
  setThemeMode: (mode: ThemeMode) => void;
  toggleThemeMode: () => void;
  cyclePreset: () => void;
  commandOpen: boolean;
  setCommandOpen: React.Dispatch<React.SetStateAction<boolean>>;
}

const WebThemeContext = createContext<WebThemeContextValue>({
  presetKey: "espresso",
  themeMode: "light",
  theme: THEME_PRESETS.espresso.light,
  hydrated: false,
  setPresetKey: () => {},
  setThemeMode: () => {},
  toggleThemeMode: () => {},
  cyclePreset: () => {},
  commandOpen: false,
  setCommandOpen: () => {},
});

/**
 * Global AnaBook theme & Command Palette provider persisted across Home and Online Library.
 */
export function WebThemeProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [presetKey, setPresetKey] = useState<ThemePresetKey>("espresso");
  const [themeMode, setThemeMode] = useState<ThemeMode>("light");
  const [hydrated, setHydrated] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEYS.THEME);
      if (raw) {
        const parsed = JSON.parse(raw) as {
          preset?: ThemePresetKey;
          mode?: ThemeMode;
        };
        if (parsed?.preset && THEME_PRESETS[parsed.preset]) {
          setPresetKey(parsed.preset);
        }
        if (parsed?.mode === "light" || parsed?.mode === "dark") {
          setThemeMode(parsed.mode);
        }
      }
    } catch {
      // Ignore storage error
    } finally {
      setHydrated(true);
    }
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    try {
      localStorage.setItem(
        STORAGE_KEYS.THEME,
        JSON.stringify({ preset: presetKey, mode: themeMode })
      );
    } catch {
      // Ignore storage error
    }
  }, [hydrated, presetKey, themeMode]);

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCommandOpen((open) => !open);
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  const toggleThemeMode = useCallback(() => {
    setThemeMode((m) => (m === "light" ? "dark" : "light"));
  }, []);

  const cyclePreset = useCallback(() => {
    setPresetKey((prev) => {
      const idx = PRESET_ORDER.indexOf(prev);
      return PRESET_ORDER[(idx + 1) % PRESET_ORDER.length];
    });
  }, []);

  const theme = useMemo(() => {
    const def = THEME_PRESETS[presetKey] || THEME_PRESETS.espresso;
    return def[themeMode];
  }, [presetKey, themeMode]);

  const value = useMemo<WebThemeContextValue>(
    () => ({
      presetKey,
      themeMode,
      theme,
      hydrated,
      setPresetKey,
      setThemeMode,
      toggleThemeMode,
      cyclePreset,
      commandOpen,
      setCommandOpen,
    }),
    [
      presetKey,
      themeMode,
      theme,
      hydrated,
      toggleThemeMode,
      cyclePreset,
      commandOpen,
    ]
  );

  return (
    <WebThemeContext.Provider value={value}>
      {children}
    </WebThemeContext.Provider>
  );
}

export function useWebTheme(): WebThemeContextValue {
  return useContext(WebThemeContext);
}
