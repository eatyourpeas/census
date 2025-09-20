from __future__ import annotations

import re
from typing import Any, Dict, List


class BulkParseError(Exception):
    pass


def parse_bulk_markdown(md_text: str) -> List[Dict[str, Any]]:
    """
    Parse markdown into groups and questions.

    Grammar (loose, line-oriented):
    - # Group Title
      <group description>

    - ## Question Title
      <question description>
      (type)
      For option types: one "- Option" per line
      For likert number: key-value lines like "min: 1", "max: 5", optional "left: Low", "right: High"

    Supported types (case-insensitive in parentheses):
      text | text number | mc_single | mc_multi | dropdown | orderable | yesno | image | likert categories | likert number
    """
    if not md_text or not md_text.strip():
        raise BulkParseError("Markdown is empty")

    lines = md_text.splitlines()
    i = 0
    groups: List[Dict[str, Any]] = []
    current_group: Dict[str, Any] | None = None
    current_question: Dict[str, Any] | None = None

    def is_heading(s: str) -> bool:
        s_strip = s.lstrip()
        return s_strip.startswith('# ' ) or s_strip.startswith('## ')

    while i < len(lines):
        raw = lines[i]
        line = raw.strip()
        # Group heading
        if line.startswith('# ') and not line.startswith('## '):
            title = line[2:].strip()
            # find next non-empty as group description (if not a heading)
            desc = ''
            j = i + 1
            while j < len(lines) and lines[j].strip() == '':
                j += 1
            if j < len(lines) and not is_heading(lines[j]):
                desc = lines[j].strip()
                i = j
            current_group = {"name": title, "description": desc, "questions": []}
            groups.append(current_group)
            current_question = None
        # Question heading
        elif line.startswith('## '):
            if not current_group:
                raise BulkParseError(f"Question declared before any group at line {i+1}")
            qtitle = line[3:].strip()
            # next non-empty: question description
            qdesc = ''
            j = i + 1
            while j < len(lines) and lines[j].strip() == '':
                j += 1
            if j < len(lines) and not is_heading(lines[j]) and not re.match(r"^\(.*\)$", lines[j].strip()):
                qdesc = lines[j].strip()
                i = j
            # next non-empty: (type)
            k = i + 1
            while k < len(lines) and lines[k].strip() == '':
                k += 1
            if k >= len(lines) or not re.match(r"^\(.*\)$", lines[k].strip()):
                raise BulkParseError(f"Missing (type) for question '{qtitle}' around line {i+1}")
            type_line = lines[k].strip()[1:-1].strip().lower()
            i = k
            current_question = {"title": qtitle, "description": qdesc, "type": type_line, "options": [], "kv": {}}
            current_group["questions"].append(current_question)
        else:
            # Within a question: parse options or likert kv pairs
            if current_question:
                if line.startswith('- '):
                    current_question["options"].append(line[2:].strip())
                else:
                    m = re.match(r"^(min|max|left|right)\s*:\s*(.*)$", line, re.IGNORECASE)
                    if m:
                        key = m.group(1).lower()
                        val = m.group(2).strip()
                        current_question["kv"][key] = val
            # else ignore stray text
        i += 1

    # Normalize and validate
    for g in groups:
        if not g["name"]:
            raise BulkParseError("A group is missing a title")
        for q in g["questions"]:
            t = q["type"].lower()
            # map types
            if t in {"text", "text free", "text freetext"}:
                q["final_type"] = "text"
                q["final_options"] = [{"type": "text", "format": "free"}]
            elif t in {"text number", "number", "numeric"}:
                q["final_type"] = "text"
                q["final_options"] = [{"type": "text", "format": "number"}]
            elif t in {"mc_single", "single", "radio"}:
                q["final_type"] = "mc_single"
                q["final_options"] = q["options"][:]
            elif t in {"mc_multi", "multi", "checkbox"}:
                q["final_type"] = "mc_multi"
                q["final_options"] = q["options"][:]
            elif t in {"dropdown", "select"}:
                q["final_type"] = "dropdown"
                q["final_options"] = q["options"][:]
            elif t in {"orderable", "rank", "ranking"}:
                q["final_type"] = "orderable"
                q["final_options"] = q["options"][:]
            elif t in {"yesno", "yes/no", "boolean"}:
                q["final_type"] = "yesno"
                q["final_options"] = []
            elif t in {"image", "image choice", "image-choice"}:
                q["final_type"] = "image"
                q["final_options"] = q["options"][:]
            elif t.startswith("likert"):
                if "categories" in t:
                    if not q["options"]:
                        raise BulkParseError(f"Likert categories requires category lines for question '{q['title']}'")
                    q["final_type"] = "likert"
                    q["final_options"] = [{"type": "categories", "labels": q["options"][:]}]
                else:
                    # number scale
                    try:
                        min_v = int(q["kv"].get("min", "1"))
                        max_v = int(q["kv"].get("max", "5"))
                    except ValueError:
                        raise BulkParseError(f"Likert number requires integer min/max for question '{q['title']}'")
                    if min_v >= max_v:
                        raise BulkParseError(f"Likert number min must be < max for question '{q['title']}'")
                    q["final_type"] = "likert"
                    q["final_options"] = [{
                        "type": "number-scale",
                        "min": min_v,
                        "max": max_v,
                        "left_label": q["kv"].get("left", ""),
                        "right_label": q["kv"].get("right", ""),
                    }]
            else:
                raise BulkParseError(f"Unsupported question type '{q['type']}' for '{q['title']}'")

    return groups
