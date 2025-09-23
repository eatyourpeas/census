(function () {
  // mark when toast script is loaded (for quick console checks)
  try {
    window._toastLoaded = true;
  } catch (e) {}
  function ensureRoot() {
    var root = document.getElementById("toast-root");
    if (!root) {
      root = document.createElement("div");
      root.id = "toast-root";
      root.className = "toast toast-top toast-end z-[1000]";
      root.setAttribute("aria-live", "polite");
      root.setAttribute("aria-atomic", "true");
      // Inline fallback styles in case Tailwind/DaisyUI purges 'toast' classes
      try {
        root.style.position = "fixed";
        root.style.top = "1rem";
        root.style.right = "1rem";
        root.style.display = "flex";
        root.style.flexDirection = "column";
        root.style.gap = "0.5rem";
        root.style.zIndex = "999999"; // above sticky toolbars
        root.style.pointerEvents = "none"; // let clicks pass except on alerts
      } catch (e) {}
      // Prefer to place near end of body to avoid layout interference
      (document.body || document.documentElement).appendChild(root);
    }
    return root;
  }

  function makeToast(message, type) {
    try {
      var root = ensureRoot();
      var colors = {
        success: "alert-success",
        info: "alert-info",
        warning: "alert-warning",
        error: "alert-error",
      };
      var cls = colors[type] || colors.info;
      var wrap = document.createElement("div");
      wrap.className = "alert " + cls + " shadow";
      // Allow interactions on the alert itself
      wrap.style.pointerEvents = "auto";
      // Fallback minimal styling (visible even without DaisyUI)
      try {
        if (!wrap.style.backgroundColor) wrap.style.backgroundColor = "#1f2937"; // gray-800
        if (!wrap.style.color) wrap.style.color = "#fff";
        if (!wrap.style.padding) wrap.style.padding = "0.5rem 0.75rem";
        if (!wrap.style.borderRadius) wrap.style.borderRadius = "0.5rem";
        if (!wrap.style.boxShadow)
          wrap.style.boxShadow = "0 2px 8px rgba(0,0,0,0.2)";
      } catch (e) {}
      // content
      var span = document.createElement("span");
      span.textContent = message;
      wrap.appendChild(span);
      // close button
      var btn = document.createElement("button");
      btn.setAttribute("type", "button");
      btn.className = "btn btn-ghost btn-xs ml-2";
      btn.setAttribute("aria-label", "Close");
      btn.innerHTML = "&times;";
      btn.addEventListener("click", function () {
        dismiss(wrap);
      });
      wrap.appendChild(btn);
      // insert
      root.appendChild(wrap);
      try {
        console.debug("Toast appended:", message, type);
      } catch (e) {}
      // auto dismiss
      setTimeout(function () {
        dismiss(wrap);
      }, 2000);
    } catch (e) {
      console && console.warn && console.warn("Toast error", e);
    }
  }
  function dismiss(el) {
    if (!el) return;
    el.classList.add("transition", "duration-500");
    el.style.opacity = "0";
    setTimeout(function () {
      if (el && el.parentElement) {
        el.remove();
      }
    }, 500);
  }
  // expose globally
  window.showToast = function (message, type) {
    try {
      console.debug("showToast:", message, type);
    } catch (e) {}
    makeToast(message, type || "info");
  };
})();
