import re
from typing import Dict


_VAR_LINE_RE = re.compile(r"--(?P<key>[a-zA-Z0-9_-]+)\s*:\s*(?P<val>[^;]+);?")


def _map_key(k: str) -> str:
    # Accept already-correct DaisyUI vars as-is
    if k in {"p","pc","s","sc","a","ac","n","nc","b1","b2","b3","bc","in","inc","su","suc","wa","wac","er","erc"}:
        return f"--{k}"
    # Map builder --color-* and base/neutral names to DaisyUI runtime vars
    m: Dict[str, str] = {
        "color-primary": "--p",
        "color-primary-content": "--pc",
        "color-secondary": "--s",
        "color-secondary-content": "--sc",
        "color-accent": "--a",
        "color-accent-content": "--ac",
        "color-neutral": "--n",
        "color-neutral-content": "--nc",
        "color-base-100": "--b1",
        "color-base-200": "--b2",
        "color-base-300": "--b3",
        "color-base-content": "--bc",
        "color-info": "--in",
        "color-info-content": "--inc",
        "color-success": "--su",
        "color-success-content": "--suc",
        "color-warning": "--wa",
        "color-warning-content": "--wac",
        "color-error": "--er",
        "color-error-content": "--erc",
    }
    if k in m:
        return m[k]
    # Pass through radius/depth/size vars in builder format
    if k.startswith("radius-") or k in {"border","depth","noise","size-selector","size-field"}:
        return f"--{k}"
    # Unknown var: ignore by returning empty key
    return ""


def normalize_daisyui_builder_css(raw: str) -> str:
    """Extract CSS variable declarations from a DaisyUI builder snippet and
    map them to DaisyUI runtime variables.

    Accepts either lines with --color-* or already-correct --p/--b1 vars.
    Returns a CSS string with semicolon-terminated declarations, suitable
    to inject inside a [data-theme] rule.
    """
    if not raw:
        return ""
    out: Dict[str, str] = {}
    for line in raw.splitlines():
        line = line.strip()
        # Skip wrapper lines like @plugin/name, name:, default:, braces
        if not line or line.startswith("@") or line.endswith("{") or line == "}" or ":" in line and not line.strip().startswith("--"):
            # allow-only var lines (starting with --)
            pass
        m = _VAR_LINE_RE.search(line)
        if not m:
            continue
        key = m.group("key")
        val = m.group("val").strip().rstrip(";")
        mapped = _map_key(key)
        if mapped:
            out[mapped] = val
    # Build CSS lines
    return "\n".join(f"  {k}: {v};" for k, v in out.items())
