(function () {
  let currentEditingRow = null;
  let currentEditingCard = null;
  let currentEditButton = null;
  let builderEditorCard = null;
  let editButtonsDelegated = false;

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
    bindEditButtons();
    const el = container.querySelector("#questions-draggable");
    if (!el || el.dataset.sortableBound) return;
    el.dataset.sortableBound = "1";
    new Sortable(el, {
      handle: "[data-drag-handle]",
      filter: "[data-drag-ignore]",
      preventOnFilter: false,
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
        bindEditButtons(document);
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

  function initConditionForms(scope) {
    const root = scope || document;
    const forms = root.querySelectorAll("[data-condition-form]");
    forms.forEach((form) => {
      if (form.dataset.conditionBound) return;
      form.dataset.conditionBound = "1";

      const operatorSelect = form.querySelector("[data-condition-operator]");
      const valueWrapper = form.querySelector("[data-condition-value]");
      const valueInput = form.querySelector('input[name="value"]');
      const targetRadios = form.querySelectorAll(
        'input[name="target_selector"]'
      );
      const questionWrapper = form.querySelector(
        '[data-target-wrapper="question"]'
      );
      const groupWrapper = form.querySelector('[data-target-wrapper="group"]');
      const questionSelect = form.querySelector(
        '[data-target-select="question"]'
      );
      const groupSelect = form.querySelector('[data-target-select="group"]');

      const toggleValueField = () => {
        if (!operatorSelect) return;
        const option = operatorSelect.options[operatorSelect.selectedIndex];
        const requiresValue = option
          ? option.getAttribute("data-requires-value") !== "0"
          : true;
        if (valueWrapper) {
          valueWrapper.classList.toggle("hidden", !requiresValue);
        }
        if (valueInput) {
          valueInput.disabled = !requiresValue;
        }
      };

      const toggleTargetFields = () => {
        let selected = "question";
        targetRadios.forEach((radio) => {
          if (radio.checked) selected = radio.value;
        });

        const enableQuestion = selected === "question";
        const enableGroup = selected === "group";

        if (questionWrapper) {
          questionWrapper.classList.toggle("hidden", !enableQuestion);
        }
        if (groupWrapper) {
          groupWrapper.classList.toggle("hidden", !enableGroup);
        }
        if (questionSelect) {
          questionSelect.disabled = !enableQuestion;
        }
        if (groupSelect) {
          groupSelect.disabled = !enableGroup;
        }
      };

      if (operatorSelect) {
        operatorSelect.addEventListener("change", toggleValueField);
      }
      targetRadios.forEach((radio) => {
        radio.addEventListener("change", toggleTargetFields);
      });

      toggleValueField();
      toggleTargetFields();
    });
  }

  function updateFormModeUI(form, mode) {
    const isEdit = mode === "edit";
    form.dataset.mode = mode;
    const toggleHidden = (selector, hidden) => {
      form.querySelectorAll(selector).forEach((el) => {
        el.classList.toggle("hidden", hidden);
      });
    };
    toggleHidden('[data-editor-label="headline-add"]', isEdit);
    toggleHidden('[data-editor-label="headline-edit"]', !isEdit);
    toggleHidden('[data-editor-label="submit-add"]', isEdit);
    toggleHidden('[data-editor-label="submit-edit"]', !isEdit);
    toggleHidden('[data-editor-label="edit-hint"]', !isEdit);
    const cancelBtn = form.querySelector('[data-action="cancel-edit"]');
    if (cancelBtn) cancelBtn.classList.toggle("hidden", !isEdit);
  }

  function focusFirstField(form) {
    const firstField = form.querySelector(
      "input:not([type=hidden]):not([disabled]), textarea, select"
    );
    if (firstField && firstField.focus) {
      firstField.focus();
    }
  }

  function exitEditMode(form, options) {
    if (!form) return;
    const opts = Object.assign({ reset: false, focus: false }, options || {});
    const createUrl =
      form.dataset.createUrl ||
      form.getAttribute("data-create-url") ||
      form.getAttribute("hx-post");
    if (createUrl) {
      form.setAttribute("hx-post", createUrl);
    }
    const createTarget =
      form.dataset.createTarget ||
      form.getAttribute("data-create-target") ||
      form.getAttribute("hx-target") ||
      "";
    if (createTarget) {
      form.setAttribute("hx-target", createTarget);
    } else {
      form.removeAttribute("hx-target");
    }
    const createSwap =
      form.dataset.createSwap ||
      form.getAttribute("data-create-swap") ||
      form.getAttribute("hx-swap") ||
      "";
    if (createSwap) {
      form.setAttribute("hx-swap", createSwap);
    } else {
      form.removeAttribute("hx-swap");
    }
    delete form.dataset.editingQuestionId;
    delete form.dataset.currentEditUrl;
    if (currentEditingCard) {
      currentEditingCard.classList.remove("is-active");
    }
    if (builderEditorCard) {
      builderEditorCard.classList.remove("is-active");
    }
    if (currentEditingRow && currentEditingRow.parentElement) {
      currentEditingRow.classList.remove("is-editing");
    }
    if (currentEditButton) {
      currentEditButton.classList.remove("is-active");
    }
    currentEditingRow = null;
    currentEditingCard = null;
    currentEditButton = null;
    updateFormModeUI(form, "add");
    if (opts.reset) {
      form.reset();
      if (typeof form._refreshCreateToggles === "function") {
        form._refreshCreateToggles();
      } else {
        const evtChange = new Event("change", { bubbles: true });
        const checkedType = form.querySelector('input[name="type"]:checked');
        if (checkedType) checkedType.dispatchEvent(evtChange);
      }
    }
    if (opts.focus) {
      focusFirstField(form);
    }
  }

  function populateFormForPayload(form, payload) {
    if (!form || !payload) return;
    const textInput = form.querySelector('input[name="text"]');
    if (textInput) {
      textInput.value = payload.text || "";
    }

    const typeInput = payload.type
      ? form.querySelector(`input[name="type"][value="${payload.type}"]`)
      : null;
    if (typeInput) {
      typeInput.checked = true;
      typeInput.dispatchEvent(new Event("change", { bubbles: true }));
    } else if (typeof form._refreshCreateToggles === "function") {
      form._refreshCreateToggles();
    }

    const requiredInput = form.querySelector('input[name="required"]');
    if (requiredInput) {
      requiredInput.checked = Boolean(payload.required);
    }

    const optionsField = form.querySelector('textarea[name="options"]');
    if (optionsField) {
      if (Array.isArray(payload.options)) {
        optionsField.value = payload.options.join("\n");
      } else if (typeof payload.options === "string") {
        optionsField.value = payload.options;
      } else {
        optionsField.value = "";
      }
    }

    // Restore prefilled dataset selection if present
    if (payload.type === "dropdown" && payload.prefilled_dataset) {
      const prefilledCheckbox = form.querySelector(
        'input[name="use_prefilled_options"]'
      );
      const prefilledDataset = form.querySelector(
        'select[name="prefilled_dataset"]'
      );

      if (prefilledCheckbox && prefilledDataset) {
        prefilledCheckbox.checked = true;
        prefilledCheckbox.dispatchEvent(new Event("change", { bubbles: true }));

        // Set the dataset value
        prefilledDataset.value = payload.prefilled_dataset;

        // Store the dataset key on the textarea for later save
        if (optionsField) {
          optionsField.dataset.prefilledDataset = payload.prefilled_dataset;
        }
      }
    }

    if (payload.type === "text") {
      const fmt = payload.text_format || payload.textFormat || "free";
      const fmtInput = form.querySelector(
        `input[name="text_format"][value="${fmt}"]`
      );
      if (fmtInput) fmtInput.checked = true;
    }

    if (payload.type === "likert") {
      const likertMode =
        payload.likert_mode || payload.likertMode || "categories";
      const likertRadio = form.querySelector(
        `input[name="likert_mode"][value="${likertMode}"]`
      );
      if (likertRadio) {
        likertRadio.checked = true;
        likertRadio.dispatchEvent(new Event("change", { bubbles: true }));
      }
      if (likertMode === "number") {
        const minField = form.querySelector('input[name="likert_min"]');
        const maxField = form.querySelector('input[name="likert_max"]');
        const leftField = form.querySelector('input[name="likert_left_label"]');
        const rightField = form.querySelector(
          'input[name="likert_right_label"]'
        );
        if (minField)
          minField.value =
            payload.likert_min !== undefined && payload.likert_min !== null
              ? payload.likert_min
              : "1";
        if (maxField)
          maxField.value =
            payload.likert_max !== undefined && payload.likert_max !== null
              ? payload.likert_max
              : "5";
        if (leftField) leftField.value = payload.likert_left_label || "";
        if (rightField) rightField.value = payload.likert_right_label || "";
      } else {
        const catsField = form.querySelector(
          'textarea[name="likert_categories"]'
        );
        if (catsField) {
          if (Array.isArray(payload.likert_categories)) {
            catsField.value = payload.likert_categories.join("\n");
          } else if (typeof payload.likert_categories === "string") {
            catsField.value = payload.likert_categories;
          } else {
            catsField.value = "";
          }
        }
      }
    }

    // Restore follow-up configuration for MC/Dropdown/Orderable questions
    if (
      payload.type === "mc_single" ||
      payload.type === "mc_multi" ||
      payload.type === "dropdown" ||
      payload.type === "orderable"
    ) {
      if (
        typeof form._populateFollowupOptions === "function" &&
        payload.followup_config
      ) {
        // Convert followup_config object to expected format
        const followupConfig = {};
        for (const [key, value] of Object.entries(payload.followup_config)) {
          followupConfig[parseInt(key)] = value;
        }
        form._populateFollowupOptions(optionsField.value, followupConfig);
      } else if (typeof form._populateFollowupOptions === "function") {
        form._populateFollowupOptions(optionsField.value, null);
      }
    }

    // Restore follow-up configuration for Yes/No questions
    if (payload.type === "yesno" && payload.yesno_followup_config) {
      const config = payload.yesno_followup_config;

      // Yes followup
      const yesCheckbox = form.querySelector(
        'input[name="yesno_yes_followup"]'
      );
      const yesLabel = form.querySelector(
        'input[name="yesno_yes_followup_label"]'
      );
      if (yesCheckbox && config.yes) {
        yesCheckbox.checked = config.yes.enabled || false;
      }
      if (yesLabel && config.yes) {
        yesLabel.value = config.yes.label || "";
      }

      // No followup
      const noCheckbox = form.querySelector('input[name="yesno_no_followup"]');
      const noLabel = form.querySelector(
        'input[name="yesno_no_followup_label"]'
      );
      if (noCheckbox && config.no) {
        noCheckbox.checked = config.no.enabled || false;
      }
      if (noLabel && config.no) {
        noLabel.value = config.no.label || "";
      }
    }

    const groupSelect = form.querySelector('select[name="group_id"]');
    if (groupSelect) {
      if (payload.group_id) {
        groupSelect.value = String(payload.group_id);
      } else {
        groupSelect.value = "";
      }
    }

    if (textInput && textInput.focus) {
      textInput.focus();
    }
  }

  function enterEditMode(form, payload, button, editUrl) {
    if (!form || !payload) return;
    if (!form.dataset.createUrl) {
      form.dataset.createUrl =
        form.getAttribute("data-create-url") ||
        form.getAttribute("hx-post") ||
        "";
    }
    if (!form.dataset.createTarget) {
      form.dataset.createTarget =
        form.getAttribute("data-create-target") ||
        form.getAttribute("hx-target") ||
        "";
    }
    if (!form.dataset.createSwap) {
      form.dataset.createSwap =
        form.getAttribute("data-create-swap") ||
        form.getAttribute("hx-swap") ||
        "outerHTML";
    }
    const destination = editUrl;
    if (destination) {
      form.setAttribute("hx-post", destination);
      form.dataset.currentEditUrl = destination;
    } else {
      delete form.dataset.currentEditUrl;
    }
    form.dataset.editingQuestionId =
      payload.id != null ? String(payload.id) : "";

    if (payload.id != null) {
      form.setAttribute("hx-target", `#question-row-${payload.id}`);
      form.setAttribute("hx-swap", "outerHTML");
    }

    const nextRow = button.closest("li");
    const nextCard = nextRow
      ? nextRow.querySelector("[data-question-card]")
      : null;

    if (!builderEditorCard) {
      builderEditorCard = form.closest("[data-builder-editor-card]") || null;
    }

    if (currentEditButton && currentEditButton !== button) {
      currentEditButton.classList.remove("is-active");
    }
    currentEditButton = button;
    if (currentEditButton) {
      currentEditButton.classList.add("is-active");
    }

    if (currentEditingCard && currentEditingCard !== nextCard) {
      currentEditingCard.classList.remove("is-active");
    }
    if (currentEditingRow && currentEditingRow !== nextRow) {
      currentEditingRow.classList.remove("is-editing");
    }

    currentEditingRow = nextRow;
    currentEditingCard = nextCard;
    if (currentEditingRow) {
      currentEditingRow.classList.add("is-editing");
    }
    if (currentEditingCard) {
      currentEditingCard.classList.add("is-active");
    }
    if (builderEditorCard) {
      builderEditorCard.classList.add("is-active");
    }

    updateFormModeUI(form, "edit");
    form.reset();
    if (typeof form._refreshCreateToggles === "function") {
      form._refreshCreateToggles();
    }
    populateFormForPayload(form, payload);
    form.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function handleEditButtonClick(btn) {
    const form = document.getElementById("create-question-form");
    if (!form || !document.body.contains(btn)) return;

    if (currentEditButton === btn && btn.classList.contains("is-active")) {
      exitEditMode(form, { reset: true, focus: true });
      return;
    }

    const payloadId = btn.dataset.payloadId;
    if (!payloadId) return;
    const scriptEl = document.getElementById(payloadId);
    if (!scriptEl) return;
    const raw = (scriptEl.textContent || "").trim();
    if (!raw) {
      console.error("Question payload was empty", scriptEl);
      return;
    }
    let payload;
    try {
      payload = JSON.parse(raw);
      if (typeof payload === "string") {
        payload = JSON.parse(payload);
      }
    } catch (err) {
      console.error("Failed to parse question payload", err);
      return;
    }

    const base = form.dataset.editUrlBase || "";
    const explicitUrl = btn.dataset.editUrl;
    const questionId =
      payload && payload.id != null ? String(payload.id) : null;
    let editUrl = explicitUrl || null;
    if (!editUrl && base && questionId) {
      editUrl = base.replace(/\/$/, "") + "/" + questionId + "/edit";
    }
    if (!editUrl) {
      console.error("Could not determine edit URL for question", payload);
      return;
    }

    enterEditMode(form, payload, btn, editUrl);
  }

  function bindEditButtons() {
    if (editButtonsDelegated) return;
    editButtonsDelegated = true;
    document.addEventListener("click", function (evt) {
      const btn = evt.target.closest('button[data-action="edit-question"]');
      if (!btn) return;
      evt.preventDefault();
      handleEditButtonClick(btn);
    });
  }

  function bindCancelButton(form) {
    if (!form) return;
    const cancelBtn = form.querySelector('[data-action="cancel-edit"]');
    if (!cancelBtn || cancelBtn.dataset.bound) return;
    cancelBtn.dataset.bound = "1";
    cancelBtn.addEventListener("click", function () {
      exitEditMode(form, { reset: true, focus: true });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    initSortable(document);
    scheduleDismissals(document);
    initCreateFormToggles();
    renumberQuestions(document);
    bindEditButtons();
    bindCancelButton(document.getElementById("create-question-form"));
    initConditionForms(document);
  });

  // Add CSRF header to all HTMX requests and coerce edit submissions to the correct endpoint
  document.body.addEventListener("htmx:configRequest", function (evt) {
    const detail = evt.detail || {};
    const headers = detail.headers || (detail.headers = {});
    headers["X-CSRFToken"] = csrfToken();

    const src = detail.elt || null;
    if (!src) return;
    const form =
      src.id === "create-question-form"
        ? src
        : src.closest && src.closest("#create-question-form");
    if (!form) return;

    const editingId = form.dataset.editingQuestionId || "";
    if (!editingId) return;

    const explicitUrl = form.dataset.currentEditUrl || "";
    const base = form.dataset.editUrlBase || "";
    let editUrl = explicitUrl;
    if (!editUrl && base) {
      editUrl = base.replace(/\/$/, "") + "/" + editingId + "/edit";
    }
    if (editUrl) {
      detail.path = editUrl;
      headers["HX-Request-Path"] = editUrl;
    }
    const targetSelector = `#question-row-${editingId}`;
    headers["HX-Target"] = targetSelector;
    if (!detail.target) {
      const explicitTarget = document.querySelector(targetSelector);
      if (explicitTarget) {
        detail.target = explicitTarget;
      }
    }
  });

  // Disable the Add button while submitting to avoid double posts
  document.body.addEventListener("htmx:beforeRequest", function (evt) {
    const src = evt.detail && evt.detail.elt ? evt.detail.elt : null;
    const form = document.getElementById("create-question-form");
    if (
      src &&
      form &&
      (src === form || (src.closest && src.closest("#create-question-form")))
    ) {
      const btn = form.querySelector('button[type="submit"]');
      if (btn) btn.disabled = true;
    }
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
      initConditionForms(document);
      // If this swap was triggered by the create-question form submission, reset the form
      const src = evt.detail && evt.detail.elt ? evt.detail.elt : null;
      const form = document.getElementById("create-question-form");
      if (
        src &&
        form &&
        (src === form || (src.closest && src.closest("#create-question-form")))
      ) {
        exitEditMode(form, { reset: true, focus: true });
      }
    }
    // Re-bind toggles for the create form if present
    if (document.getElementById("create-question-form")) {
      initCreateFormToggles();
      bindCancelButton(document.getElementById("create-question-form"));
    }
    bindEditButtons();
    initConditionForms(target);
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
      exitEditMode(form, { reset: true, focus: true });
    }
    // Always re-enable submit button after request completes
    const form = document.getElementById("create-question-form") || src;
    if (form) {
      const btn = form.querySelector('button[type="submit"]');
      if (btn) btn.disabled = false;
    }
  });

  document.addEventListener("pointerdown", function (evt) {
    const form = document.getElementById("create-question-form");
    if (!form || !form.dataset.editingQuestionId) return;
    const target = evt.target;
    if (!target) return;
    const activeCard = currentEditingCard;
    const editorCard =
      builderEditorCard || form.closest("[data-builder-editor-card]") || null;
    if (
      (activeCard && (activeCard === target || activeCard.contains(target))) ||
      (editorCard && (editorCard === target || editorCard.contains(target))) ||
      (currentEditButton &&
        (currentEditButton === target || currentEditButton.contains(target)))
    ) {
      return;
    }
    exitEditMode(form, { reset: true, focus: false });
  });

  function initCreateFormToggles() {
    const form = document.getElementById("create-question-form");
    if (!form || form.dataset.togglesBound) return;
    form.dataset.togglesBound = "1";

    const textSection = form.querySelector('[data-section="text-options"]');
    const optsSection = form.querySelector('[data-section="options"]');
    const likertSection = form.querySelector('[data-section="likert"]');
    const yesnoFollowupSection = form.querySelector(
      '[data-section="yesno-followup"]'
    );
    const likertCat = likertSection
      ? likertSection.querySelector('[data-likert="categories"]')
      : null;
    const likertNum = likertSection
      ? likertSection.querySelector('[data-likert="number"]')
      : null;

    // Prefilled dataset controls
    const prefilledToggle = form.querySelector("[data-prefilled-toggle]");
    const prefilledSection = form.querySelector("[data-prefilled-section]");
    const prefilledContainer = form.querySelector("[data-prefilled-container]");
    const prefilledDataset = form.querySelector("[data-prefilled-dataset]");
    const loadDatasetBtn = form.querySelector("[data-load-dataset]");
    const optionsTextarea = form.querySelector('textarea[name="options"]');

    // Follow-up controls
    const followupContainer = form.querySelector(
      "[data-options-followup-container]"
    );
    const followupList = form.querySelector("[data-followup-options-list]");
    const refreshFollowupBtn = form.querySelector(
      "[data-refresh-followup-options]"
    );

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
      const isDropdown = type === "dropdown";
      const isLikert = type === "likert";
      const isYesNo = type === "yesno";

      // Show/hide follow-up for mc/dropdown/orderable (not image or likert)
      const showFollowup =
        type === "mc_single" ||
        type === "mc_multi" ||
        type === "dropdown" ||
        type === "orderable";

      if (textSection) textSection.classList.toggle("hidden", !isText);
      if (optsSection) optsSection.classList.toggle("hidden", !isMC);
      if (likertSection) likertSection.classList.toggle("hidden", !isLikert);
      if (yesnoFollowupSection)
        yesnoFollowupSection.classList.toggle("hidden", !isYesNo);

      // Show/hide follow-up container within options section
      if (followupContainer) {
        followupContainer.classList.toggle("hidden", !showFollowup);
      }

      // Only show prefilled options for dropdown type
      if (prefilledContainer) {
        prefilledContainer.classList.toggle("hidden", !isDropdown);
      }
      // Reset prefilled checkbox if switching away from dropdown
      if (!isDropdown && prefilledToggle && prefilledToggle.checked) {
        prefilledToggle.checked = false;
        if (prefilledSection) {
          prefilledSection.classList.add("hidden");
        }
        if (prefilledDataset) {
          prefilledDataset.value = "";
        }
      }

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

    // Function to populate follow-up options based on textarea content
    function populateFollowupOptions(optionsText, followupConfig) {
      if (!followupList) return;

      const lines = (optionsText || "")
        .split("\n")
        .map((s) => s.trim())
        .filter((s) => s);
      if (lines.length === 0) {
        followupList.innerHTML =
          '<p class="text-xs opacity-60">Enter options above first</p>';
        return;
      }

      const html = lines
        .map((line, idx) => {
          const isEnabled =
            followupConfig &&
            followupConfig[idx] &&
            followupConfig[idx].enabled;
          const label =
            followupConfig && followupConfig[idx]
              ? followupConfig[idx].label
              : "Please elaborate";

          return `
          <div class="flex items-start gap-2 p-2 bg-base-100 rounded border border-base-300">
            <input type="checkbox" class="checkbox checkbox-sm mt-1" name="option_${idx}_followup" id="option-${idx}-followup" ${
            isEnabled ? "checked" : ""
          } />
            <div class="flex-1 min-w-0">
              <label for="option-${idx}-followup" class="text-sm font-medium cursor-pointer block truncate" title="${line}">${line}</label>
              <input type="text" name="option_${idx}_followup_label" class="input input-xs input-bordered w-full mt-1" placeholder="Follow-up label..." value="${label}" />
            </div>
          </div>
        `;
        })
        .join("");

      followupList.innerHTML = html;
    }

    // Refresh follow-up options button
    if (refreshFollowupBtn && optionsTextarea) {
      refreshFollowupBtn.addEventListener("click", function () {
        populateFollowupOptions(optionsTextarea.value, null);
      });
    }

    // Prefilled dataset toggle handler
    if (prefilledToggle && prefilledSection) {
      prefilledToggle.addEventListener("change", function () {
        const isChecked = prefilledToggle.checked;
        prefilledSection.classList.toggle("hidden", !isChecked);
        if (!isChecked && prefilledDataset) {
          prefilledDataset.value = "";
        }
      });
    }

    // Load dataset button handler
    if (loadDatasetBtn && prefilledDataset && optionsTextarea) {
      loadDatasetBtn.addEventListener("click", async function () {
        const datasetKey = prefilledDataset.value;
        if (!datasetKey) {
          if (typeof window.showToast === "function") {
            window.showToast("Please select a dataset first", "error");
          } else {
            alert("Please select a dataset first");
          }
          return;
        }

        // Show loading state with spinner
        loadDatasetBtn.disabled = true;
        const originalContent = loadDatasetBtn.innerHTML;
        loadDatasetBtn.innerHTML =
          '<span class="loading loading-spinner loading-xs"></span> Loading...';

        try {
          const response = await fetch(`/api/datasets/${datasetKey}/`, {
            method: "GET",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": csrfToken(),
            },
            credentials: "same-origin",
          });

          if (!response.ok) {
            throw new Error(`Failed to load dataset: ${response.statusText}`);
          }

          const data = await response.json();
          if (data.options && Array.isArray(data.options)) {
            optionsTextarea.value = data.options.join("\n");
            // Store the dataset key as a data attribute for later retrieval
            optionsTextarea.dataset.prefilledDataset = datasetKey;
            // Also refresh follow-up options
            populateFollowupOptions(optionsTextarea.value, null);
            if (typeof window.showToast === "function") {
              window.showToast(
                `Loaded ${data.options.length} options`,
                "success"
              );
            }
          } else {
            throw new Error("Invalid response format");
          }
        } catch (error) {
          console.error("Error loading dataset:", error);
          if (typeof window.showToast === "function") {
            window.showToast("Failed to load dataset options", "error");
          } else {
            alert("Failed to load dataset options: " + error.message);
          }
        } finally {
          // Restore button state
          loadDatasetBtn.disabled = false;
          loadDatasetBtn.innerHTML = originalContent;
        }
      });
    }

    // Expose refresh and populate functions so we can call them externally
    form._refreshCreateToggles = refresh;
    form._populateFollowupOptions = populateFollowupOptions;

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
