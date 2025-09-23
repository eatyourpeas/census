(function () {
  function csrfToken() {
    const name = "csrftoken";
    const m = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
    return m ? m[2] : "";
  }

  function scheduleDismissals(root) {
    const scope = root || document;
    const alerts = scope.querySelectorAll("#questions-list .alert");
    alerts.forEach((el) => {
      if (el.dataset.autodismissBound) return;
      el.dataset.autodismissBound = "1";
      setTimeout(() => {
        el.classList.add("transition-opacity", "duration-700");
        el.classList.add("opacity-0");
        setTimeout(() => {
          if (el && el.parentElement) el.remove();
        }, 800);
      }, 1500);
    });
  }

  function initSortable(container) {
    if (!container) return;
    const el = container.querySelector("#questions-draggable");
    if (!el || el.dataset.sortableBound) return;
    el.dataset.sortableBound = "1";
    new Sortable(el, {
      handle: ".drag-handle",
      animation: 150,
      forceFallback: true,
      onEnd: function () {
        const ids = Array.from(el.querySelectorAll("[data-qid]")).map(
          (li) => li.dataset.qid
        );
        const body = new URLSearchParams({ order: ids.join(",") });
        fetch(
          el.dataset.reorderUrl ||
            window.location.pathname.replace(/\/$/, "") + "/questions/reorder",
          {
            method: "POST",
            headers: {
              "Content-Type": "application/x-www-form-urlencoded",
              "X-CSRFToken": csrfToken(),
              "X-Requested-With": "XMLHttpRequest",
            },
            body,
          }
        )
          .then((resp) => {
            if (!resp.ok) {
              console.error("Failed to persist question order", resp.status);
              return;
            }
            renumberQuestions(el);
            if (typeof window.showToast === "function") {
              window.showToast("Order saved", "success");
            }
          })
          .catch((err) => {
            console.error("Error persisting question order", err);
          });
      },
    });
  }

  function renumberQuestions(scope) {
    const root = scope || document;
    const items = root.querySelectorAll("#questions-draggable > li[data-qid]");
    let i = 1;
    items.forEach((li) => {
      const badge = li.querySelector(".q-number");
      if (badge) {
        badge.textContent = String(i);
      }
      i += 1;
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initSortable(document);
    scheduleDismissals(document);
    initCreateFormToggles();
    renumberQuestions(document);
  });

  if (window.htmx) {
    // Add CSRF header to all HTMX requests
    document.body.addEventListener("htmx:configRequest", function (evt) {
      evt.detail.headers["X-CSRFToken"] = csrfToken();
    });
    // Re-init Sortable after swaps that touch the questions list
    document.body.addEventListener("htmx:afterSwap", function (evt) {
      const target = (evt.detail && evt.detail.target) || evt.target;
      if (!target) return;
      if (
        target.id === "questions-list" ||
        (target.closest && target.closest("#questions-list"))
      ) {
        initSortable(document);
        scheduleDismissals(document);
        renumberQuestions(document);
        // If this swap was triggered by the create-question form submission, reset the form
        const src = evt.detail && evt.detail.elt ? evt.detail.elt : null;
        const form = document.getElementById("create-question-form");
        if (
          src &&
          form &&
          (src === form ||
            (src.closest && src.closest("#create-question-form")))
        ) {
          // Reset to initial defaults
          form.reset();
          // Re-apply conditional visibility based on defaults
          if (typeof form._refreshCreateToggles === "function") {
            form._refreshCreateToggles();
          } else {
            // Fallback: trigger a change event to force recompute
            const evtChange = new Event("change", { bubbles: true });
            const checkedType = form.querySelector(
              'input[name="type"]:checked'
            );
            if (checkedType) checkedType.dispatchEvent(evtChange);
          }
          // Focus first usable input for faster entry
          const firstField = form.querySelector(
            "input:not([type=hidden]):not([disabled]), textarea, select"
          );
          if (firstField && firstField.focus) firstField.focus();
        }
      }
      // Re-bind toggles for the create form if present
      if (document.getElementById("create-question-form")) {
        initCreateFormToggles();
      }
    });

    // Also reset form after the request completes successfully, even if no swap occurred
    document.body.addEventListener("htmx:afterRequest", function (evt) {
      const src = evt.detail && evt.detail.elt ? evt.detail.elt : null;
      if (
        !src ||
        !(
          src.id === "create-question-form" ||
          (src.closest && src.closest("#create-question-form"))
        )
      )
        return;
      const xhr = evt.detail && evt.detail.xhr ? evt.detail.xhr : null;
      if (xhr && xhr.status >= 200 && xhr.status < 300) {
        const form = document.getElementById("create-question-form") || src;
        if (!form) return;
        form.reset();
        if (typeof form._refreshCreateToggles === "function") {
          form._refreshCreateToggles();
        }
        const firstField = form.querySelector(
          "input:not([type=hidden]):not([disabled]), textarea, select"
        );
        if (firstField && firstField.focus) firstField.focus();
      }
    });
  }

  function initCreateFormToggles() {
    const form = document.getElementById("create-question-form");
    if (!form || form.dataset.togglesBound) return;
    form.dataset.togglesBound = "1";

    const textSection = form.querySelector('[data-section="text-options"]');
    const optsSection = form.querySelector('[data-section="options"]');
    const likertSection = form.querySelector('[data-section="likert"]');
    const likertCat = likertSection
      ? likertSection.querySelector('[data-likert="categories"]')
      : null;
    const likertNum = likertSection
      ? likertSection.querySelector('[data-likert="number"]')
      : null;

    function refresh() {
      const checked = form.querySelector('input[name="type"]:checked');
      const type = checked ? checked.value : null;
      if (!type) return;
      const isText = type === "text";
      const isMC =
        type === "mc_single" ||
        type === "mc_multi" ||
        type === "dropdown" ||
        type === "orderable" ||
        type === "image";
      const isLikert = type === "likert";

      if (textSection) textSection.classList.toggle("hidden", !isText);
      if (optsSection) optsSection.classList.toggle("hidden", !isMC);
      if (likertSection) likertSection.classList.toggle("hidden", !isLikert);

      if (isLikert && likertSection) {
        const modeChecked = form.querySelector(
          'input[name="likert_mode"]:checked'
        );
        const mode = modeChecked ? modeChecked.value : "categories";
        if (likertCat)
          likertCat.classList.toggle("hidden", mode !== "categories");
        if (likertNum) likertNum.classList.toggle("hidden", mode !== "number");
      }
    }

    // Expose refresh so we can call it after external resets
    form._refreshCreateToggles = refresh;

    form.addEventListener("change", function (e) {
      if (
        e.target &&
        (e.target.name === "type" || e.target.name === "likert_mode")
      ) {
        refresh();
      }
    });

    // Initial state
    refresh();
  }
})();
