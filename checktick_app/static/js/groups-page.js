(function () {
  function $(sel, root) {
    return (root || document).querySelector(sel);
  }
  function $all(sel, root) {
    return Array.from((root || document).querySelectorAll(sel));
  }

  function init() {
    var root = $("#groups-draggable");
    if (!root) return;
    var createBtn = $("#create-repeat-btn");
    var modal = $("#repeat-modal");
    var inputIds = $("#repeat-group-ids");
    var selected = new Set();

    function refresh() {
      if (createBtn) createBtn.disabled = selected.size === 0;
      var bar = $("#selection-toolbar");
      var count = $("#selection-count");
      if (bar && count) {
        count.textContent = String(selected.size);
        bar.classList.toggle("hidden", selected.size === 0);
      }
    }

    function updateSelection(li, isChecked) {
      var icon = li.querySelector(".sel-repeat-icon");
      var tile = li.querySelector(".selectable-group");
      if (isChecked) {
        selected.add(li.dataset.gid);
        if (tile) {
          tile.dataset.selected = "1";
          tile.style.outline =
            "2px solid color-mix(in oklch, var(--p) 45%, transparent)";
          tile.style.backgroundColor =
            "color-mix(in oklch, var(--p) 12%, transparent)";
        }
        if (icon) icon.classList.remove("hidden");
      } else {
        selected.delete(li.dataset.gid);
        if (tile) {
          delete tile.dataset.selected;
          tile.style.outline = "";
          tile.style.backgroundColor = "";
        }
        if (icon) icon.classList.add("hidden");
      }
    }

    root.addEventListener("click", function (e) {
      var li = e.target.closest("li[data-gid]");
      if (!li) return;
      if (
        e.target.closest(".drag-handle") ||
        e.target.closest("form") ||
        e.target.closest(".select-checkbox")
      )
        return;
      // If the click is on a builder link, allow normal navigation
      var a = e.target.closest('a[href*="/builder/"]');
      if (a) return;
      var cb = li.querySelector(".select-checkbox");
      if (!cb) return;
      cb.checked = !cb.checked;
      updateSelection(li, cb.checked);
      refresh();
    });

    root.addEventListener("change", function (e) {
      if (!e.target.classList.contains("select-checkbox")) return;
      var li = e.target.closest("li[data-gid]");
      if (!li) return;
      updateSelection(li, e.target.checked);
      refresh();
    });

    var clearBtn = $("#clear-selection");
    if (clearBtn)
      clearBtn.addEventListener("click", function () {
        $all("li[data-gid]", root).forEach(function (li) {
          var cb = li.querySelector(".select-checkbox");
          if (!cb) return;
          cb.checked = false;
          updateSelection(li, false);
        });
        selected.clear();
        refresh();
      });

    if (createBtn)
      createBtn.addEventListener("click", function () {
        if (!selected.size) return;
        if (inputIds) inputIds.value = Array.from(selected).join(",");
        if (modal && modal.showModal) modal.showModal();
      });

    var cancelBtn = $("#repeat-cancel-btn");
    if (cancelBtn && modal)
      cancelBtn.addEventListener("click", function () {
        modal.close();
      });

    // Initialize from any pre-checked boxes
    $all("li[data-gid]", root).forEach(function (li) {
      var cb = li.querySelector(".select-checkbox");
      if (cb && cb.checked) {
        selected.add(li.dataset.gid);
        updateSelection(li, true);
      }
    });
    refresh();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
