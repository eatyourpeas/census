(function () {
  if (!window.Sortable) return;
  document.querySelectorAll(".orderable-list").forEach(function (listEl) {
    new Sortable(listEl, {
      animation: 150,
      handle: ".drag-handle",
      forceFallback: true,
      onStart: function () {
        document.body.classList.add("select-none");
      },
      onEnd: function () {
        document.body.classList.remove("select-none");
      },
    });
  });
})();
