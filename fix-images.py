#!/usr/bin/env python3
"""Fix broken Next.js image URLs in mirrored Soundwave HTML files."""

import re
import shutil
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, parse_qs

SITE_ROOT = Path("/Users/David/Desktop/song app/tonetouchmusic.sakibhasan.dev")


def rel_to_root(filepath: Path) -> str:
    depth = len(filepath.relative_to(SITE_ROOT).parts) - 1
    return "../" * depth if depth else ""


def decode_next_url(raw_src: str) -> Optional[str]:
    """Extract the original url= value from a Next.js image src."""
    # Handle HTML-encoded ampersands
    normalized = raw_src.replace("&amp;", "&")
    if "?url=" not in normalized:
        return None
    query = normalized.split("?", 1)[1]
    params = parse_qs(query)
    urls = params.get("url")
    return unquote(urls[0]) if urls else None


def fix_local_next_src(raw_src: str, prefix: str) -> str:
    """Strip query string from mirrored _next/image*.jpg|png paths."""
    normalized = raw_src.replace("&amp;", "&")
    if "?url=" in normalized:
        path = normalized.split("?", 1)[0]
        if path.startswith("/"):
            return prefix + path.lstrip("/")
        if not path.startswith("../") and not path.startswith("./"):
            return prefix + path
        return path
    return raw_src


def resolve_src(raw_src: str, prefix: str) -> str:
    decoded = decode_next_url(raw_src)
    if decoded:
        if "logo.png" in decoded.lower() or decoded in ("/logo.png", "/logo.png?v=2"):
            return f"{prefix}logo.png"
        if decoded.startswith("http://") or decoded.startswith("https://"):
            return decoded
        if decoded.startswith("/"):
            return prefix + decoded.lstrip("/")
        return decoded

    if "image11fb" in raw_src or raw_src.endswith("logo.png"):
        return f"{prefix}logo.png"

    if "_next/image" in raw_src and "?url=" in raw_src:
        return fix_local_next_src(raw_src, prefix)

    if raw_src.startswith("/"):
        return prefix + raw_src.lstrip("/")

    return raw_src


def fix_img_tag(tag: str, prefix: str) -> str:
    def repl_src(match: re.Match[str]) -> str:
        quote = match.group(1)
        value = match.group(2)
        return f'src={quote}{resolve_src(value, prefix)}{quote}'

    tag = re.sub(r'src=(["\'])([^"\']*)\1', repl_src, tag)
    tag = re.sub(r'\s+srcSet=(["\'])[^"\']*\1', "", tag, flags=re.IGNORECASE)
    tag = re.sub(r'\s+srcset=(["\'])[^"\']*\1', "", tag, flags=re.IGNORECASE)
    return tag


def fix_html(content: str, prefix: str) -> str:
    content = re.sub(
        r"<img[^>]*>",
        lambda m: fix_img_tag(m.group(0), prefix),
        content,
        flags=re.IGNORECASE,
    )
    # Fix any remaining absolute /_next/image? references outside img tags (rare)
    content = re.sub(
        r'/_next/image\?[^"\'\s>]+',
        lambda m: resolve_src(m.group(0), prefix),
        content,
    )
    return content


def main() -> None:
    logo = SITE_ROOT / "logo.png"
    next_logo = SITE_ROOT / "_next" / "image11fb.png"
    if logo.exists():
        shutil.copy2(logo, next_logo)

    changed = 0
    for filepath in SITE_ROOT.rglob("*.html"):
        original = filepath.read_text(encoding="utf-8", errors="ignore")
        prefix = rel_to_root(filepath)
        updated = fix_html(original, prefix)
        if updated != original:
            filepath.write_text(updated, encoding="utf-8")
            changed += 1

    print(f"Updated {changed} HTML files")
    print(f"Synced logo to {next_logo}")


if __name__ == "__main__":
    main()
