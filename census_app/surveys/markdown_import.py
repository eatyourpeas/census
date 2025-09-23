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
        return s_strip.startswith("# ") or s_strip.startswith("## ")

    while i < len(lines):
        raw = lines[i]
        line = raw.strip()
        # Group heading
        if line.startswith("# ") and not line.startswith("## "):
            title = line[2:].strip()
            # find next non-empty as group description (if not a heading)
            desc = ""
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            if j < len(lines) and not is_heading(lines[j]):
                desc = lines[j].strip()
                i = j
            current_group = {"name": title, "description": desc, "questions": []}
            groups.append(current_group)
            current_question = None
        # Question heading
        elif line.startswith("## "):
            if not current_group:
                raise BulkParseError(
                    f"Question declared before any group at line {i+1}"
                )
            qtitle = line[3:].strip()
            # next non-empty: question description
            qdesc = ""
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            if (
                j < len(lines)
                and not is_heading(lines[j])
                and not re.match(r"^\(.*\)$", lines[j].strip())
            ):
                qdesc = lines[j].strip()
                i = j
            # next non-empty: (type)
            k = i + 1
            while k < len(lines) and lines[k].strip() == "":
                k += 1
            if k >= len(lines) or not re.match(r"^\(.*\)$", lines[k].strip()):
                raise BulkParseError(
                    f"Missing (type) for question '{qtitle}' around line {i+1}"
                )
            type_line = lines[k].strip()[1:-1].strip().lower()
            i = k
            current_question = {
                "title": qtitle,
                "description": qdesc,
                "type": type_line,
                "options": [],
                "kv": {},
            }
            current_group["questions"].append(current_question)
        else:
            # Within a question: parse options or likert kv pairs
            if current_question:
                if line.startswith("- "):
                    current_question["options"].append(line[2:].strip())
                else:
                    m = re.match(
                        r"^(min|max|left|right)\s*:\s*(.*)$", line, re.IGNORECASE
                    )
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
                        raise BulkParseError(
                            f"Likert categories requires category lines for question '{q['title']}'"
                        )
                    q["final_type"] = "likert"
                    q["final_options"] = [
                        {"type": "categories", "labels": q["options"][:]}
                    ]
                else:
                    # number scale
                    try:
                        min_v = int(q["kv"].get("min", "1"))
                        max_v = int(q["kv"].get("max", "5"))
                    except ValueError:
                        raise BulkParseError(
                            f"Likert number requires integer min/max for question '{q['title']}'"
                        )
                    if min_v >= max_v:
                        raise BulkParseError(
                            f"Likert number min must be < max for question '{q['title']}'"
                        )
                    q["final_type"] = "likert"
                    q["final_options"] = [
                        {
                            "type": "number-scale",
                            "min": min_v,
                            "max": max_v,
                            "left_label": q["kv"].get("left", ""),
                            "right_label": q["kv"].get("right", ""),
                        }
                    ]
            else:
                raise BulkParseError(
                    f"Unsupported question type '{q['type']}' for '{q['title']}'"
                )

    return groups


def parse_bulk_markdown_with_collections(md_text: str) -> Dict[str, Any]:
    """
    Parse markdown into groups/questions and detect simple REPEAT markers for collections.

    Rules:
    - A line (optionally prefixed by ">" for nesting) that equals "REPEAT" or "REPEAT-<N>"
      applies to the next group heading at the same nesting depth.
    - Nesting depth is the count of leading ">" characters before the REPEAT line and/or group heading.
    - REPEAT without a number means unlimited (no max); REPEAT-5 means max_count=5.

    Returns dict: {"groups": [...], "repeats": [{group_index, depth, max_count, parent_index} ...]}
    """
    if not md_text or not md_text.strip():
        raise BulkParseError("Markdown is empty")

    raw_lines = md_text.splitlines()
    cleaned_lines: List[str] = []
    pending_repeat: Dict[int, int | None] = {}  # depth -> max or None
    repeats: List[Dict[str, int | None]] = []
    import re as _re

    # Track a stack of the most recent repeated group indices at each depth
    repeat_stack: List[int] = []  # stores group_index at each depth
    group_count_seen = 0

    for raw in raw_lines:
        # Count leading '>' as depth
        s = raw
        depth = 0
        i = 0
        while i < len(s):
            if s[i] == ">":
                depth += 1
                i += 1
                # optional space after '>'
                if i < len(s) and s[i] == " ":
                    i += 1
                continue
            elif s[i] == " ":
                # allow leading spaces between blockquotes
                i += 1
                continue
            break
        content = s[i:].rstrip()

        # REPEAT marker?
        m = _re.match(r"^REPEAT(?:-(\d+))?$", content.strip(), flags=_re.IGNORECASE)
        if m:
            maxv = int(m.group(1)) if m.group(1) else None
            pending_repeat[depth] = maxv
            # do not include this line in cleaned markdown
            continue

        # Group heading detection (top-level groups only: '# ')
        if content.strip().startswith("# ") and not content.strip().startswith("## "):
            # Trim or expand repeat_stack to current depth
            while len(repeat_stack) > depth:
                repeat_stack.pop()
            # add cleaned heading line (without blockquote)
            cleaned_lines.append(content)
            # If a repeat is pending at this depth, register it for this group index
            if depth in pending_repeat:
                parent_index = repeat_stack[-1] if repeat_stack else None
                repeats.append(
                    {
                        "group_index": group_count_seen,
                        "depth": depth,
                        "max_count": pending_repeat[depth],
                        "parent_index": parent_index,
                    }
                )
                # Update stack: this group becomes the latest repeated group at this depth
                repeat_stack.append(group_count_seen)
                del pending_repeat[depth]
            else:
                # non-repeated group at this depth trims deeper stack but doesn't extend
                pass
            group_count_seen += 1
            continue

        # For all other lines, strip blockquote markers for parsing and include
        cleaned_lines.append(content)

    cleaned_md = "\n".join(cleaned_lines)
    groups = parse_bulk_markdown(cleaned_md)
    return {"groups": groups, "repeats": repeats}
