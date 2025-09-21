(function () {
  function csrfToken() {
    var name = "csrftoken";
    var m = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
    return m ? m[2] : "";
  }

  function init() {
    var el = document.getElementById("groups-draggable");
    if (!el || el.dataset.bound) return;
    el.dataset.bound = "1";
    var canEdit = (el.getAttribute("data-can-edit") || "false") === "true";
    if (!window.Sortable || !canEdit) return;
    var dirty = false;
    var saveBtn = document.getElementById("save-order-btn");
    new Sortable(el, {
      handle: ".drag-handle",
      animation: 150,
      forceFallback: true,
      onEnd: function () {
        renumber(el);
        dirty = true;
        if (saveBtn) saveBtn.disabled = false;
      },
    });
    // initial numbering
    renumber(el);
    if (saveBtn)
      saveBtn.addEventListener("click", function () {
        if (!dirty) return;
        submitOrder(el).then(function (ok) {
          if (ok === false) return;
          dirty = false;
          saveBtn.disabled = true;
        });
      });
  }

  function renumber(root) {
    var i = 1;
    root.querySelectorAll(".q-number").forEach(function (b) {
      b.textContent = String(i++);
    });
  }

  function submitOrder(el) {
    var ids = Array.from(el.querySelectorAll("[data-gid]")).map(function (li) {
      return li.dataset.gid;
    });
    var url = el.getAttribute("data-reorder-url");
    if (!url) return;
    var body = new URLSearchParams({ order: ids.join(",") });
    return fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-CSRFToken": csrfToken(),
      },
      body: body,
    })
      .then(function (resp) {
        if (resp.ok) {
          // Do not reload; let the badge numbers remain as-is
          return true;
        } else {
          console.error("Failed to save order");
          return false;
        }
      })
      .catch(function (err) {
        console.error(err);
        return false;
      });
  }

  document.addEventListener("DOMContentLoaded", init);
  document.addEventListener("DOMContentLoaded", function () {
    var nameInput = document.getElementById("create-group-name");
    var submitBtn = document.getElementById("create-group-submit");
    if (!nameInput || !submitBtn) return;
    function refresh() {
      var hasText = (nameInput.value || "").trim().length > 0;
      submitBtn.disabled = !hasText;
    }
    nameInput.addEventListener("input", refresh);
    refresh();
  });
})();
