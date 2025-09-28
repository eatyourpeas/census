(() => {
  const textarea = document.querySelector('textarea[name="markdown"]');
  const previewContainer = document.getElementById("bulk-structure-preview");
  const countBadge = document.getElementById("bulk-structure-count");
  const openModalButton = document.getElementById("bulk-import-open-modal");
  const confirmDialog = document.getElementById("bulk-import-confirm");
  const cancelModalButton = document.getElementById("bulk-import-cancel");

  if (openModalButton && confirmDialog && cancelModalButton) {
    openModalButton.addEventListener("click", () => {
      if (typeof confirmDialog.showModal === "function") {
        confirmDialog.showModal();
      }
    });

    cancelModalButton.addEventListener("click", () => {
      if (typeof confirmDialog.close === "function") {
        confirmDialog.close();
      }
    });

    confirmDialog.addEventListener("cancel", (event) => {
      event.preventDefault();
      if (typeof confirmDialog.close === "function") {
        confirmDialog.close();
      }
    });
  }

  if (!textarea || !previewContainer) {
    return;
  }

  const slugify = (text) =>
    (text || "")
      .toString()
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, " ")
      .trim()
      .replace(/[\s_-]+/g, "-")
      .replace(/^-+|-+$/g, "");

  const allocateId = (preferred, fallback, registry) => {
    let base = preferred ? slugify(preferred) : "";
    if (!base) {
      base = slugify(fallback);
    }
    let candidate = base || fallback || "item";
    const original = candidate;
    let counter = 2;
    while (registry.has(candidate)) {
      candidate = `${original}-${counter++}`;
    }
    registry.add(candidate);
    return candidate;
  };

  const extractTitleAndId = (rawTitle, fallbackId, registry) => {
    let title = rawTitle || "";
    let explicitId;
    const match = title.match(/\{([^{}]+)\}\s*$/);
    if (match) {
      explicitId = match[1].trim();
      title = title.slice(0, match.index).trim();
    }
    const id = allocateId(explicitId, fallbackId, registry);
    return { title: title.trim(), id, explicitId };
  };

  const createIdToken = (text, variant) => {
    const el = document.createElement("code");
    el.textContent = text;
    el.className =
      "inline-flex items-center rounded border px-2 py-0.5 font-mono text-xs tracking-tight";

    if (variant === "group") {
      el.style.backgroundColor = "hsl(var(--p) / 0.18)";
      el.style.borderColor = "hsl(var(--p) / 0.35)";
      el.style.color = "hsl(var(--p))";
    } else if (variant === "question") {
      el.style.backgroundColor = "hsl(var(--s) / 0.16)";
      el.style.borderColor = "hsl(var(--s) / 0.32)";
      el.style.color = "hsl(var(--s))";
    } else {
      el.style.backgroundColor = "hsl(var(--in) / 0.15)";
      el.style.borderColor = "hsl(var(--in) / 0.3)";
      el.style.color = "hsl(var(--in))";
    }

    return el;
  };

  const createMetaBadge = (variant, label) => {
    const badge = document.createElement("span");
    badge.className =
      "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium";
    badge.style.backgroundColor = "hsl(var(--p) / 0.18)";
    badge.style.borderColor = "hsl(var(--p) / 0.35)";
    badge.style.color = "hsl(var(--p))";

    const icon = document.createElement("span");
    icon.setAttribute("aria-hidden", "true");
    icon.className = "leading-none";
    icon.textContent = variant === "repeat" ? "++" : "➜";

    const text = document.createElement("span");
    text.textContent = label;

    badge.appendChild(icon);
    badge.appendChild(text);

    return badge;
  };

  const parseStructure = (md) => {
    const rawLines = (md || "").split(/\r?\n/);
    const normalized = rawLines.map((raw) => {
      let depth = 0;
      let i = 0;
      while (i < raw.length) {
        const char = raw[i];
        if (char === ">") {
          depth += 1;
          i += 1;
          if (raw[i] === " ") {
            i += 1;
          }
          continue;
        }
        if (char === " ") {
          i += 1;
          continue;
        }
        break;
      }
      const content = raw.slice(i);
      return {
        depth,
        content,
        trimmed: content.trim(),
      };
    });

    const groups = [];
    const warnings = [];
    const groupIds = new Set();
    const questionIds = new Set();
    const pendingRepeat = new Map();
    let currentGroup = null;

    const isGroupHeading = (line) => /^#(?!#)\s+/.test(line);
    const isQuestionHeading = (line) => /^##\s+/.test(line);

    for (let i = 0; i < normalized.length; i += 1) {
      const { trimmed, depth } = normalized[i];
      if (!trimmed) {
        continue;
      }

      const repeatMatch = trimmed.match(/^REPEAT(?:-(\d+))?$/i);
      if (repeatMatch) {
        pendingRepeat.set(
          depth,
          repeatMatch[1] ? parseInt(repeatMatch[1], 10) : null
        );
        continue;
      }

      if (isGroupHeading(trimmed)) {
        const rawTitle = trimmed.replace(/^#\s+/, "").trim();
        const { title, id: groupId } = extractTitleAndId(
          rawTitle,
          `group-${groups.length + 1}`,
          groupIds
        );
        let description = "";
        for (let j = i + 1; j < normalized.length; j += 1) {
          const lookahead = normalized[j].trimmed;
          if (!lookahead) {
            continue;
          }
          if (isGroupHeading(lookahead) || isQuestionHeading(lookahead)) {
            break;
          }
          if (!/^\(.*\)$/.test(lookahead) && !lookahead.startsWith("?")) {
            description = lookahead;
          }
          break;
        }
        currentGroup = {
          title: title || "Untitled group",
          id: groupId,
          description,
          questions: [],
          repeat: pendingRepeat.has(depth)
            ? { maxCount: pendingRepeat.get(depth) }
            : null,
        };
        if (pendingRepeat.has(depth)) {
          pendingRepeat.delete(depth);
        }
        groups.push(currentGroup);
        continue;
      }

      if (isQuestionHeading(trimmed)) {
        const rawTitle = trimmed.replace(/^##\s+/, "").trim();
        if (!currentGroup) {
          warnings.push(
            `Question “${
              rawTitle || "Untitled"
            }” appears before any group heading. It will be imported into an auto-created group.`
          );
          const { id: fallbackGroupId } = extractTitleAndId(
            "Ungrouped",
            `group-${groups.length + 1}`,
            groupIds
          );
          currentGroup = {
            title: "Ungrouped",
            id: fallbackGroupId,
            description: "",
            questions: [],
            repeat: null,
          };
          groups.push(currentGroup);
        }

        const { title, id: questionId } = extractTitleAndId(
          rawTitle,
          `${currentGroup.id}-${currentGroup.questions.length + 1}`,
          questionIds
        );
        const question = {
          title: title || "Untitled question",
          id: questionId,
          description: "",
          type: "",
          branches: [],
        };

        for (let j = i + 1; j < normalized.length; j += 1) {
          const lookahead = normalized[j].trimmed;
          if (!lookahead) {
            continue;
          }
          if (isGroupHeading(lookahead) || isQuestionHeading(lookahead)) {
            break;
          }
          if (
            !question.description &&
            !/^\(.*\)$/.test(lookahead) &&
            !lookahead.startsWith("?")
          ) {
            question.description = lookahead;
          } else if (!question.type && /^\(.*\)$/.test(lookahead)) {
            question.type = lookahead.slice(1, -1).trim();
          } else if (/^\?\s*/.test(lookahead)) {
            const branchMatch = lookahead.match(
              /^\?\s*when\s+(.+?)\s*->\s*\{([^{}]+)\}\s*$/i
            );
            if (branchMatch) {
              const condition = branchMatch[1].trim();
              const targetRaw = branchMatch[2].trim();
              question.branches.push({
                condition,
                target: slugify(targetRaw),
                targetRaw,
              });
            }
          }
        }

        currentGroup.questions.push(question);
      }
    }

    return { groups, warnings };
  };

  const renderStructure = ({ groups, warnings }) => {
    previewContainer.innerHTML = "";
    previewContainer.setAttribute("aria-busy", "true");

    if (warnings.length) {
      const warningBox = document.createElement("div");
      warningBox.className = "alert alert-warning text-sm";
      const heading = document.createElement("div");
      heading.className = "font-semibold";
      heading.textContent = "Notes";
      warningBox.appendChild(heading);
      const list = document.createElement("ul");
      list.className = "list-disc pl-5 mt-1 space-y-1";
      warnings.forEach((message) => {
        const li = document.createElement("li");
        li.textContent = message;
        list.appendChild(li);
      });
      warningBox.appendChild(list);
      previewContainer.appendChild(warningBox);
    }

    let totalQuestions = 0;

    if (!groups.length) {
      const empty = document.createElement("div");
      empty.className = "text-sm text-base-content/70";
      empty.textContent =
        "Add a # heading for a group and ## headings for questions to see the structure preview.";
      previewContainer.appendChild(empty);
      previewContainer.setAttribute("aria-busy", "false");
      if (countBadge) {
        countBadge.classList.add("hidden");
      }
      return;
    }

    groups.forEach((group) => {
      totalQuestions += group.questions.length;
      const groupCard = document.createElement("div");
      groupCard.className =
        "rounded-lg border border-base-300 bg-base-100 p-4 shadow-sm space-y-3";

      const header = document.createElement("div");
      header.className =
        "flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between";

      const titleWrap = document.createElement("div");
      titleWrap.className = "flex flex-wrap items-center gap-2";
      const groupBadge = createIdToken(group.id, "group");

      const title = document.createElement("span");
      title.className = "font-medium text-base-content";
      title.textContent = group.title;

      titleWrap.appendChild(groupBadge);
      titleWrap.appendChild(title);

      header.appendChild(titleWrap);

      const headerMeta = document.createElement("div");
      headerMeta.className = "flex flex-wrap items-center gap-2";
      headerMeta.style.marginLeft = "auto";

      if (group.repeat) {
        const repeatLabel = group.repeat.maxCount
          ? `Repeat ×${group.repeat.maxCount}`
          : "Repeat";
        headerMeta.appendChild(createMetaBadge("repeat", repeatLabel));
      }

      const questionCount = document.createElement("span");
      questionCount.className = "text-xs text-base-content/60";
      questionCount.textContent = `${group.questions.length} question${
        group.questions.length === 1 ? "" : "s"
      }`;
      headerMeta.appendChild(questionCount);

      header.appendChild(headerMeta);
      groupCard.appendChild(header);

      if (group.description) {
        const description = document.createElement("p");
        description.className = "text-sm text-base-content/70";
        description.textContent = group.description;
        groupCard.appendChild(description);
      }

      if (group.questions.length) {
        const questionList = document.createElement("div");
        questionList.className = "space-y-2";

        group.questions.forEach((question, index) => {
          const questionRow = document.createElement("div");
          questionRow.className =
            "rounded-md border border-base-300 bg-base-200/60 p-3";

          const rowHeader = document.createElement("div");
          rowHeader.className =
            "flex flex-wrap items-center gap-2 justify-between";

          const questionWrap = document.createElement("div");
          questionWrap.className = "flex flex-wrap items-center gap-2";

          const questionBadge = createIdToken(question.id, "question");

          const questionTitle = document.createElement("span");
          questionTitle.className = "font-medium text-sm text-base-content";
          questionTitle.textContent = `${index + 1}. ${question.title}`;

          questionWrap.appendChild(questionBadge);
          questionWrap.appendChild(questionTitle);
          rowHeader.appendChild(questionWrap);

          const rowMeta = document.createElement("div");
          rowMeta.className = "flex flex-wrap items-center gap-2";
          rowMeta.style.marginLeft = "auto";

          if (question.type) {
            const typePill = createIdToken(question.type, "info");
            typePill.classList.add("uppercase", "tracking-wide");
            rowMeta.appendChild(typePill);
          }

          if (rowMeta.childNodes.length) {
            rowHeader.appendChild(rowMeta);
          }

          questionRow.appendChild(rowHeader);

          if (question.description) {
            const questionDescription = document.createElement("p");
            questionDescription.className = "text-xs text-base-content/70 mt-2";
            questionDescription.textContent = question.description;
            questionRow.appendChild(questionDescription);
          }

          if (question.branches.length) {
            const branchList = document.createElement("div");
            branchList.className = "mt-2 space-y-1";

            question.branches.forEach((branch) => {
              const row = document.createElement("div");
              row.className =
                "flex items-center justify-between gap-2 rounded px-2 py-1 text-xs";
              row.style.backgroundColor = "hsl(var(--p) / 0.12)";
              row.style.border = "1px solid hsl(var(--p) / 0.3)";

              const when = document.createElement("span");
              when.className = "font-medium";
              when.textContent = `when ${branch.condition}`;

              const targetBadge = createMetaBadge(
                "branch",
                `{${branch.targetRaw}}`
              );

              row.appendChild(when);
              row.appendChild(targetBadge);
              branchList.appendChild(row);
            });

            questionRow.appendChild(branchList);
          }

          questionList.appendChild(questionRow);
        });

        groupCard.appendChild(questionList);
      }

      previewContainer.appendChild(groupCard);
    });

    if (countBadge) {
      countBadge.classList.remove("hidden");
      countBadge.textContent = `${groups.length} group${
        groups.length === 1 ? "" : "s"
      }, ${totalQuestions} question${totalQuestions === 1 ? "" : "s"}`;
    }

    previewContainer.setAttribute("aria-busy", "false");
  };

  const updatePreview = () => {
    const parsed = parseStructure(textarea.value);
    renderStructure(parsed);
  };

  let scheduled = false;
  const scheduleUpdate = () => {
    if (scheduled) {
      return;
    }
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      updatePreview();
    });
  };

  textarea.addEventListener("input", scheduleUpdate);
  textarea.addEventListener("change", scheduleUpdate);

  updatePreview();
})();
