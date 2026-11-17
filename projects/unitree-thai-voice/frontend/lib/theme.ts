export type Theme = "light" | "dark";

export const THEME_STORAGE_KEY = "g1-theme";

export function isTheme(value: string | null | undefined): value is Theme {
  return value === "light" || value === "dark";
}

export function getStoredTheme(): Theme {
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    return isTheme(stored) ? stored : "dark";
  } catch {
    return "dark";
  }
}

export function applyTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = theme;
  document.querySelector('meta[name="theme-color"]')?.setAttribute(
    "content", theme === "light" ? "#edf3fa" : "#050b15",
  );
}

// Runs before the page is painted so saved light mode does not flash dark.
export const THEME_BOOTSTRAP_SCRIPT = `(function(){var t="dark";try{var s=localStorage.getItem("g1-theme");if(s==="light"||s==="dark")t=s}catch(e){}document.documentElement.dataset.theme=t;document.documentElement.style.colorScheme=t;var m=document.querySelector('meta[name="theme-color"]');if(m)m.setAttribute("content",t==="light"?"#edf3fa":"#050b15")})();`;
