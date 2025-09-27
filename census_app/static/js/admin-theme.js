(function () {
  try {
    var storageKey = "census:admin-theme";
    var meta = document.querySelector('meta[name="census-theme"]');
    var defaultTheme = (meta && meta.getAttribute("content")) || "census-light";
    var theme = localStorage.getItem(storageKey) || defaultTheme;
    var statusNode = null;
    var toggleNode = null;

    function applyTheme(t) {
      document.documentElement.setAttribute("data-theme", t);
      try {
        localStorage.setItem(storageKey, t);
      } catch (e) {}
      // Update toggle aria state and announce
      if (toggleNode) {
        var isDark = t === "census-dark";
        toggleNode.setAttribute("aria-pressed", String(isDark));
        // Optional: reflect current mode in the control label
        var baseLabel =
          toggleNode.getAttribute("data-theme-toggle-label") || "Toggle theme";
        toggleNode.textContent = baseLabel;
      }
      if (statusNode) {
        var msg =
          t === "census-dark" ? "Dark theme enabled" : "Light theme enabled";
        statusNode.textContent = msg;
      }
    }

    // Apply at load
    applyTheme(theme);

    // Wire up toggle if present
    function nextTheme(current) {
      return current === "census-light" ? "census-dark" : "census-light";
    }

    document.addEventListener("DOMContentLoaded", function () {
      toggleNode = document.getElementById("admin-theme-toggle");
      statusNode = document.getElementById("admin-theme-status");
      if (toggleNode) {
        // Initialize aria-pressed according to current theme
        toggleNode.setAttribute(
          "aria-pressed",
          String(theme === "census-dark")
        );
        toggleNode.addEventListener(
          "click",
          function (e) {
            e.preventDefault();
            var current =
              document.documentElement.getAttribute("data-theme") ||
              defaultTheme;
            applyTheme(nextTheme(current));
          },
          true
        );
      }
    });
  } catch (e) {
    // noop
  }
})();
