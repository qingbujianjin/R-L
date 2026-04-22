import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { THEMES, THEME_ORDER } from "./themes";

type ThemeId = keyof typeof THEMES;

type ThemeContextType = {
  themeId: ThemeId;
  setThemeId: (id: ThemeId) => void;
  theme: (typeof THEMES)[ThemeId];
  cycleTheme: () => void;
};

const STORAGE_KEY = "literary-theme";
const LEGACY_STORAGE_KEY = "literary-easter-theme";
const ThemeContext = createContext<ThemeContextType | null>(null);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [themeId, setThemeId] = useState<ThemeId>("nightTender");

  useEffect(() => {
    const cached = (localStorage.getItem(STORAGE_KEY) || localStorage.getItem(LEGACY_STORAGE_KEY)) as ThemeId | null;
    if (cached && THEMES[cached]) {
      setThemeId(cached);
    }
  }, []);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, themeId);
    const palette = THEMES[themeId].palette;
    const root = document.documentElement;
    Object.entries(palette).forEach(([key, value]) => {
      root.style.setProperty(key, value);
    });
    document.body.setAttribute("data-theme", themeId);

    // Console easter eggs.
    if (themeId === "outsider") {
      console.log("今天，妈妈死了。也可能是昨天，我不知道。");
    } else if (themeId === "aleph") {
      console.log("在一个点里，宇宙没有边界。");
    } else {
      console.log(THEMES[themeId].easterEgg);
    }
  }, [themeId]);

  const cycleTheme = () => {
    const index = THEME_ORDER.indexOf(themeId);
    const nextId = THEME_ORDER[(index + 1) % THEME_ORDER.length] as ThemeId;
    setThemeId(nextId);
  };

  const value = useMemo(
    () => ({
      themeId,
      setThemeId,
      theme: THEMES[themeId],
      cycleTheme,
    }),
    [themeId]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useTheme must be used inside ThemeProvider");
  }
  return ctx;
}
