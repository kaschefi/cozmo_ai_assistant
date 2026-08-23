import React, { createContext, useContext, useEffect, useState } from 'react';

export type ThemeId = string;

export interface ThemeOption {
  id: ThemeId;
  name: string;
  description: string;
  previewColors: string[];
}

export const THEME_OPTIONS: ThemeOption[] = [
  {
    id: 'default',
    name: 'Default',
    description: 'Minimalist obsidian dark monochrome with neutral accents',
    previewColors: ['#030407', '#18181b', '#71717a', '#ffffff'],
  },
  {
    id: 'black-ice',
    name: 'Black Ice',
    description: 'Obsidian depths, glacial teal glow & crystal frost',
    previewColors: ['#020407', '#083c4d', '#00f3ff', '#e0f8ff'],
  },
  {
    id: 'royal',
    name: 'Royal',
    description: 'Majestic obsidian, 24k gold lasers & crisp white typography',
    previewColors: ['#030407', '#1a1812', '#d4af37', '#ffffff'],
  },
  {
    id: 'it',
    name: 'IT',
    description: 'ASCII particle drift data streams, cyber green & deep cyber black',
    previewColors: ['#020503', '#052e16', '#00ff66', '#ffffff'],
  },
];

interface ThemeContextValue {
  theme: ThemeId;
  setTheme: (theme: ThemeId) => void;
  themes: ThemeOption[];
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setThemeState] = useState<ThemeId>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('moka_home_theme') as ThemeId;
      if (saved && THEME_OPTIONS.some((t) => t.id === saved)) {
        return saved;
      }
    }
    return 'default';
  });

  const setTheme = (newTheme: ThemeId) => {
    setThemeState(newTheme);
    if (typeof window !== 'undefined') {
      localStorage.setItem('moka_home_theme', newTheme);
      document.documentElement.setAttribute('data-theme', newTheme);
    }
  };

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, themes: THEME_OPTIONS }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = (): ThemeContextValue => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

export default ThemeContext;
