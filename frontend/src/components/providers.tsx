"use client";

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

import { translate, type Key, type Lang } from "../lib/i18n";

export type Theme = "dark" | "paper";

type AppContextValue = {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: Key) => string;
};

const AppContext = createContext<AppContextValue | null>(null);
const THEME_KEY = "nirikkha.theme";
const LANG_KEY = "nirikkha.lang";

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    /* storage blocked: the choice lasts for this page only */
  }
}

export function Providers({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("dark");
  const [lang, setLangState] = useState<Lang>("en");

  useEffect(() => {
    if (read(THEME_KEY) === "paper") setThemeState("paper");
    if (read(LANG_KEY) === "bn") setLangState("bn");
  }, []);

  const setTheme = useCallback((next: Theme) => {
    setThemeState(next);
    document.documentElement.dataset.theme = next;
    write(THEME_KEY, next);
  }, []);

  const setLang = useCallback((next: Lang) => {
    setLangState(next);
    document.documentElement.lang = next;
    write(LANG_KEY, next);
  }, []);

  const t = useCallback((key: Key) => translate(lang, key), [lang]);

  return <AppContext.Provider value={{ theme, setTheme, lang, setLang, t }}>{children}</AppContext.Provider>;
}

export function useApp(): AppContextValue {
  const value = useContext(AppContext);
  if (!value) throw new Error("useApp must be used inside <Providers>");
  return value;
}