(() => {
  const textarea = document.querySelector('textarea[name="markdown"]');
  const previewContainer = document.getElementById("bulk-structure-preview");
  const countBadge = document.getElementById("bulk-structure-count");

  if (!textarea || !previewContainer) {
    return;
  }

  const slugify = (text) => {
    return (text || "")
      .toString()
      .normalize("NFKD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, " ")
      .trim()
      .replace(/[\s_-]+/g, "-")
      .replace(/^-+|-+$/g, "");
  };

  const makeUniqueId = (label, fallback, registry, scopePrefix) => {
    let base = slugify(label);
    if (!base) {
      base = slugify(fallback) || fallback.replace(/\s+/g, "-");
    }
    if (scopePrefix) {
      base = `${scopePrefix}-${base}`;
    }
    let candidate = base;
    let counter = 2;
    while (registry.has(candidate)) {
      candidate = `${base}-${counter++}`;
    }
    registry.add(candidate);
    return candidate;
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

  const parseStructure = (md) => {
    const lines = (md || "").split(/\r?\n/);
    const groups = [];
    const warnings = [];
    const groupIds = new Set();
    const questionIds = new Set();
    let currentGroup = null;

    const isGroupHeading = (line) => /^#(?!#)\s+/.test(line);
    const isQuestionHeading = (line) => /^##\s+/.test(line);

    for (let i = 0; i < lines.length; i += 1) {
      const raw = lines[i];
      const trimmed = raw.trim();
      if (!trimmed) {
        continue;
      }

      if (isGroupHeading(trimmed)) {
        const title = trimmed.replace(/^#\s+/, "").trim();
        const groupId = makeUniqueId(
          title,
          `group-${groups.length + 1}`,
          groupIds
        );
        let description = "";
        for (let j = i + 1; j < lines.length; j += 1) {
          const lookahead = lines[j].trim();
          if (!lookahead) {
            continue;
          }
          if (isGroupHeading(lookahead) || isQuestionHeading(lookahead)) {
            break;
          }
          if (!/^\(.*\)$/.test(lookahead)) {
            description = lookahead;
          }
          break;
        }
        currentGroup = {
          title: title || "Untitled group",
          id: groupId,
          description,
          questions: [],
        };
        groups.push(currentGroup);
        continue;
      }

      if (isQuestionHeading(trimmed)) {
        const title = trimmed.replace(/^##\s+/, "").trim();
        if (!currentGroup) {
          warnings.push(
            `Question “${
              title || "Untitled"
            }” appears before any group heading. It will be imported into an auto-created group.`
          );
          const fallbackGroupId = makeUniqueId(
            "Ungrouped",
            `group-${groups.length + 1}`,
            groupIds
          );
          currentGroup = {
            title: "Ungrouped",
            id: fallbackGroupId,
            description: "",
            questions: [],
          };
          groups.push(currentGroup);
        }

        const questionId = makeUniqueId(
          title,
          `question-${questionIds.size + 1}`,
          questionIds,
          currentGroup.id
        );
        const question = {
          title: title || "Untitled question",
          id: questionId,
          description: "",
          type: "",
        };

        for (let j = i + 1; j < lines.length; j += 1) {
          const lookahead = lines[j].trim();
          if (!lookahead) {
            continue;
          }
          if (isGroupHeading(lookahead) || isQuestionHeading(lookahead)) {
            break;
          }
          if (!question.description && !/^\(.*\)$/.test(lookahead)) {
            question.description = lookahead;
          } else if (!question.type && /^\(.*\)$/.test(lookahead)) {
            question.type = lookahead.slice(1, -1).trim();
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

      const questionCount = document.createElement("span");
      questionCount.className = "text-xs text-base-content/60";
      questionCount.textContent = `${group.questions.length} question${
        group.questions.length === 1 ? "" : "s"
      }`;
      header.appendChild(questionCount);
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

          if (question.type) {
            const typePill = createIdToken(question.type, "info");
            typePill.classList.add("uppercase", "tracking-wide");
            rowHeader.appendChild(typePill);
          }

          questionRow.appendChild(rowHeader);

          if (question.description) {
            const questionDescription = document.createElement("p");
            questionDescription.className = "text-xs text-base-content/70 mt-2";
            questionDescription.textContent = question.description;
            questionRow.appendChild(questionDescription);
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
