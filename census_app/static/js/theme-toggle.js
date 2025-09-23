(function () {
  const KEY = "census-theme"; // values: 'system' | 'census-light' | 'census-dark'
  const htmlEl = document.documentElement;
  const select = document.getElementById("theme-select");
  const ddBtn = document.getElementById("theme-dropdown-btn");
  const ddLabel = document.getElementById("theme-current-label");
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

  function labelFor(pref) {
    switch (pref) {
      case "census-light":
        return "Light";
      case "census-dark":
        return "Dark";
      case "system":
      default:
        return "System";
    }
  }

  function hydrate() {
    const saved = readSaved();
    if (saved) {
      applyTheme(saved);
      if (select) select.value = normalize(saved) || saved;
      if (ddLabel) ddLabel.textContent = labelFor(saved);
      return saved;
    }
    // default to current server-set theme, but set select to 'system' if it matches OS
    const current =
      normalize(htmlEl.getAttribute("data-theme")) || "census-light";
    const systemTheme = effectiveTheme("system");
    if (select) {
      select.value = current === systemTheme ? "system" : current;
    }
    if (ddLabel) {
      ddLabel.textContent = labelFor(
        current === systemTheme ? "system" : current
      );
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

    if (select) {
      select.addEventListener("change", () => {
        const pref = select.value; // 'system' | 'census-light' | 'census-dark'
        applyTheme(pref);
        persist(pref);
        if (ddLabel) ddLabel.textContent = labelFor(pref);
      });
    }

    // Dropdown menu handling (use event delegation and pointerdown for reliability)
    if (ddBtn) {
      const dd = ddBtn.closest(".dropdown");
      const menu = dd ? dd.querySelector(".dropdown-content") : null;

      function setTheme(pref) {
        applyTheme(pref);
        persist(pref);
        if (ddLabel) ddLabel.textContent = labelFor(pref);
        if (select) select.value = pref;
        // update active marker
        if (menu) {
          menu
            .querySelectorAll("li")
            .forEach((li) => li.classList.remove("active"));
          const targetBtn = menu.querySelector(`[data-theme-choice="${pref}"]`);
          if (targetBtn) {
            const li = targetBtn.closest("li");
            if (li) li.classList.add("active");
          }
        }
        // close dropdown by blurring the button (focus-based dropdown)
        ddBtn.blur();
      }

      // hydrate active marker
      const current =
        readSaved() ||
        normalize(htmlEl.getAttribute("data-theme")) ||
        "census-light";
      if (menu) {
        const systemTheme = effectiveTheme("system");
        const prefShown = current === systemTheme ? "system" : current;
        menu
          .querySelectorAll("li")
          .forEach((li) => li.classList.remove("active"));
        const activeBtn = menu.querySelector(
          `[data-theme-choice="${prefShown}"]`
        );
        if (activeBtn) {
          const li = activeBtn.closest("li");
          if (li) li.classList.add("active");
        }
      }

      if (menu) {
        // Use pointerdown so the handler runs even if focus changes immediately
        menu.addEventListener("pointerdown", (e) => {
          const target = e.target.closest("[data-theme-choice]");
          if (!target) return;
          e.preventDefault();
          const pref = target.getAttribute("data-theme-choice");
          setTheme(pref);
        });
        // Fallback for click (some devices)
        menu.addEventListener("click", (e) => {
          const target = e.target.closest("[data-theme-choice]");
          if (!target) return;
          e.preventDefault();
          const pref = target.getAttribute("data-theme-choice");
          setTheme(pref);
        });
      }
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
