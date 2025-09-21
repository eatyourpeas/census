(function () {
  const KEY = "census-theme"; // values: 'system' | 'census-light' | 'census-dark'
  const htmlEl = document.documentElement;
  const select = document.getElementById("theme-select");
  const media = window.matchMedia("(prefers-color-scheme: dark)");

  function normalize(pref) {
    switch (pref) {
      case "census":
      case "light":
        return "census-light";
      case "dark":
        return "census-dark";
      case "system":
      case "census-light":
      case "census-dark":
        return pref;
      default:
        return null;
    }
  }

  function effectiveTheme(pref) {
    if (pref === "system") {
      return media.matches ? "census-dark" : "census-light";
    }
    return pref || "census-light";
  }

  function applyTheme(pref) {
    const theme = effectiveTheme(normalize(pref) || pref);
    htmlEl.setAttribute("data-theme", theme);
  }

  function readSaved() {
    try {
      const raw = localStorage.getItem(KEY);
      return normalize(raw) || raw;
    } catch (_) {
      return null;
    }
  }

  function persist(pref) {
    try {
      localStorage.setItem(KEY, pref);
    } catch (_) {}
  }

  function hydrate() {
    const saved = readSaved();
    if (saved) {
      applyTheme(saved);
      if (select) select.value = normalize(saved) || saved;
      return saved;
    }
    // default to current server-set theme, but set select to 'system' if it matches OS
    const current =
      normalize(htmlEl.getAttribute("data-theme")) || "census-light";
    const systemTheme = effectiveTheme("system");
    if (select) {
      select.value = current === systemTheme ? "system" : current;
    }
    // apply current as-is (server default) without persisting
    applyTheme(current);
    return null;
  }

  function onMediaChange() {
    const saved = readSaved();
    if (saved === "system" || !saved) {
      applyTheme("system");
      if (select && select.value === "system") {
        // keep select as 'system'; visual theme changes automatically
      }
    }
  }

  function init() {
    hydrate();
    // watch OS changes
    if (typeof media.addEventListener === "function") {
      media.addEventListener("change", onMediaChange);
    } else if (typeof media.addListener === "function") {
      // Safari
      media.addListener(onMediaChange);
    }

    if (!select) return;
    select.addEventListener("change", () => {
      const pref = select.value; // 'system' | 'census-light' | 'census-dark'
      applyTheme(pref);
      persist(pref);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
