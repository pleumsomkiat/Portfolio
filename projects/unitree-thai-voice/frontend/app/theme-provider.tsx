"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { applyTheme, getStoredTheme, isTheme, THEME_STORAGE_KEY, type Theme } from "../lib/theme";

const ThemeContext = createContext<{ theme: Theme; setTheme: (theme: Theme) => void } | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, updateTheme] = useState<Theme>("dark");

  useEffect(() => {
    const initialTheme = getStoredTheme();
    updateTheme(initialTheme);
    applyTheme(initialTheme);

    const syncTheme = (event: StorageEvent) => {
      if (event.key !== THEME_STORAGE_KEY && event.key !== null) return;
      const nextTheme = isTheme(event.newValue) ? event.newValue : "dark";
      updateTheme(nextTheme);
      applyTheme(nextTheme);
    };
    window.addEventListener("storage", syncTheme);
    return () => window.removeEventListener("storage", syncTheme);
  }, []);

  const setTheme = useCallback((nextTheme: Theme) => {
    updateTheme(nextTheme);
    applyTheme(nextTheme);
    try {
      window.localStorage.setItem(THEME_STORAGE_KEY, nextTheme);
    } catch {
      // The current page still switches themes when browser storage is blocked.
    }
  }, []);

  const value = useMemo(() => ({ theme, setTheme }), [theme, setTheme]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error("useTheme must be used within ThemeProvider");
  return context;
}
