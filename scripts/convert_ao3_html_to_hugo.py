#!/usr/bin/env python3
"""Convert an AO3 Calibre-style HTML export into Hugo content files.

- Input: single HTML file containing all chapters (like DVN_Dad_must_die.html)
- Output:
  content/zh/novels/<slug>/_index.md
  content/zh/novels/<slug>/01.md ...

Designed to be dependency-free (stdlib only).
"""

from __future__ import annotations

import argparse
import html
import os
import re
from pathlib import Path
from html.parser import HTMLParser


WS_RE = re.compile(r"\s+")


def clean_text(s: str) -> str:
    s = html.unescape(s)
    s = s.replace("\u00a0", " ")
    s = WS_RE.sub(" ", s)
    return s.strip()


class AO3Parser(HTMLParser):
    """Parse either:

    1) Calibre-style AO3 HTML exports (older workflow)
    2) Raw AO3 "view_full_work" HTML pages (current workflow)

    Dependency-free (stdlib HTMLParser).
    """

    def __init__(self):
        super().__init__(convert_charrefs=False)

        # Calibre-export signals
        self.in_h1 = False
        self.in_h2_heading = False  # <h2 class="heading">Chapter 1: ...

        # AO3 page signals
        self.in_work_title_h2 = False  # <h2 class="title heading">Work title</h2>
        self.in_chapter_h3_title = False  # <h3 class="title">Chapter N: ...</h3>

        # Summary capture (both formats end up using blockquote.userstuff somewhere in a "preface")
        self.in_summary_block = False
        self.capture_summary = []

        self.title = None

        self.current_chapter = None  # dict with keys: num,title,paras
        self.chapters = []

        # Chapter content capture
        self._in_chapter_content = False
        self._content_div_depth = 0  # tracks nested div depth for the current userstuff/module
        self._p_buf = []
        self._tag_stack = []

    def handle_startendtag(self, tag, attrs):
        # XHTML-style self-closing tags like <br /> land here.
        if self._in_chapter_content and tag == "br":
            self._p_buf.append("\n\n")
        return

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self._tag_stack.append(tag)

        if tag == "h1":
            self.in_h1 = True

        # AO3 page work title
        if tag == "h2" and attrs.get("class") == "title heading":
            self.in_work_title_h2 = True

        # Summary appears as <blockquote class="userstuff">...</blockquote> in preface meta
        # (AO3 page uses <blockquote class="userstuff"> inside <div class="summary module">)
        if tag == "blockquote" and attrs.get("class") == "userstuff" and self.title is not None and not self.chapters:
            self.in_summary_block = True

        # Calibre-export chapter heading: <h2 class="heading">Chapter 1: ...</h2>
        if tag == "h2" and attrs.get("class") == "heading":
            self.in_h2_heading = True

        # AO3 page chapter heading (inside <div class="chapter" id="chapter-N"> ...)
        if tag == "h3" and attrs.get("class") == "title":
            self.in_chapter_h3_title = True
            self._h3_title_buf = []

        # Chapter content start:
        # - Calibre export: <div class="userstuff">
        # - AO3 page: <div class="userstuff module" role="article"> OR <div class="userstuff"> for one-shots
        if tag == "div":
            cls = attrs.get("class") or ""
            is_userstuff = cls == "userstuff" or cls.startswith("userstuff ") or cls.endswith(" userstuff") or "userstuff" in cls.split()

            # AO3 one-shot pages have a single <div class="userstuff"> under "Work Text" without a Chapter N heading.
            if is_userstuff and self.current_chapter is None and self.title and not self.chapters and not self.in_summary_block:
                self.current_chapter = {"num": 1, "title": self.title, "paras": []}

            if is_userstuff and self.current_chapter is not None and not self._in_chapter_content:
                self._in_chapter_content = True
                self._content_div_depth = 1
            elif self._in_chapter_content:
                # nested div inside content
                self._content_div_depth += 1

        if self._in_chapter_content:
            if tag == "p":
                self._p_buf = []
            if tag == "br":
                # Treat HTML <br> as a paragraph break for nicer reading in Markdown.
                self._p_buf.append("\n\n")
            if tag in ("em", "i"):
                self._p_buf.append("*")
            if tag in ("strong", "b"):
                self._p_buf.append("**")

    def handle_endtag(self, tag):
        # close formatting markers
        if self._in_chapter_content:
            if tag in ("em", "i"):
                self._p_buf.append("*")
            if tag in ("strong", "b"):
                self._p_buf.append("**")

            if tag == "p":
                txt = "".join(self._p_buf)
                txt = html.unescape(txt)
                txt = txt.replace("\u00a0", " ")

                # Normalize spaces but preserve intentional paragraph breaks (blank lines).
                txt = txt.replace("\r\n", "\n")
                txt = re.sub(r"[\t ]+", " ", txt)
                # Trim each line but keep empty lines
                txt = "\n".join([line.strip() for line in txt.split("\n")])
                # Collapse 3+ newlines to 2
                txt = re.sub(r"\n{3,}", "\n\n", txt).strip()

                if txt:
                    self.current_chapter["paras"].append(txt)
                self._p_buf = []

            if tag == "div":
                self._content_div_depth -= 1
                if self._content_div_depth <= 0:
                    # closing the userstuff/module div ends chapter content.
                    self._in_chapter_content = False
                    self._content_div_depth = 0
                    if self.current_chapter and self.current_chapter.get("paras"):
                        # finalize chapter
                        self.chapters.append(self.current_chapter)
                        self.current_chapter = None

        if tag == "h1":
            self.in_h1 = False

        if tag == "h2":
            self.in_h2_heading = False
            self.in_work_title_h2 = False

        if tag == "h3":
            if self.in_chapter_h3_title and hasattr(self, "_h3_title_buf"):
                t = clean_text("".join(self._h3_title_buf))
                if t:
                    m = re.match(r"Chapter\s+(\d+)\s*:\s*(.+)", t)
                    if m:
                        num = int(m.group(1))
                        ch_title = m.group(2).strip()
                        self.current_chapter = {"num": num, "title": ch_title, "paras": []}
                self._h3_title_buf = []
            self.in_chapter_h3_title = False

        if tag == "blockquote" and self.in_summary_block:
            self.in_summary_block = False

        # pop stack
        if self._tag_stack:
            self._tag_stack.pop()

    def handle_data(self, data):
        if self.in_h1:
            t = clean_text(data)
            if t:
                self.title = t

        if self.in_work_title_h2:
            t = clean_text(data)
            if t and t.lower() not in ("beta", "archive of our own"):
                # Override generic site headings like "beta" captured elsewhere.
                self.title = t

        if self.in_summary_block:
            # keep raw-ish, we'll join with blank lines later
            t = data
            if t:
                self.capture_summary.append(t)

        # Calibre-export chapter heading
        if self.in_h2_heading:
            t = clean_text(data)
            if t:
                m = re.match(r"Chapter\s+(\d+)\s*:\s*(.+)", t)
                if m:
                    num = int(m.group(1))
                    ch_title = m.group(2).strip()
                    self.current_chapter = {"num": num, "title": ch_title, "paras": []}

        # AO3 page chapter heading: HTML splits text across nodes (<a>Chapter 1</a>: Title)
        if self.in_chapter_h3_title and hasattr(self, "_h3_title_buf"):
            self._h3_title_buf.append(data)

        if self._in_chapter_content:
            # Buffer text inside chapter content
            self._p_buf.append(data)


def to_frontmatter(title: str, weight: int, date: str | None = None) -> str:
    lines = ["---", f'title: "{title.replace("\"", "\\\"")}"']
    if date:
        lines.append(f"date: {date}")
    lines.append(f"weight: {weight}")
    lines.append("---\n")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True, help="Input AO3 HTML file")
    ap.add_argument("--slug", required=True, help="Novel slug (folder name)")
    ap.add_argument("--lang", default="zh", choices=["zh", "en"], help="Language")
    ap.add_argument("--base", default=str(Path(__file__).resolve().parents[1]), help="Repo root")
    args = ap.parse_args()

    html_text = Path(args.inp).read_text(encoding="utf-8", errors="replace")

    p = AO3Parser()
    p.feed(html_text)

    if not p.title:
        raise SystemExit("Could not detect title (<h1>)")
    if not p.chapters:
        raise SystemExit("Could not detect chapters")

    repo = Path(args.base)
    out_dir = repo / "content" / args.lang / "novels" / args.slug
    out_dir.mkdir(parents=True, exist_ok=True)

    # write novel index
    summary_raw = "".join(p.capture_summary).strip()
    summary_raw = html.unescape(summary_raw)
    summary_raw = summary_raw.replace("\r\n", "\n")
    # crude paragraph breaks: AO3 summary has <p> but parser captured text; reflow lightly
    summary = "\n".join([line.strip() for line in summary_raw.splitlines() if line.strip()])

    # User requested: no covers needed for these imports.
    # Use an existing placeholder so we don't create broken <img> links.
    cover_default = "/img/books/dad-must-die/cover.svg"
    idx = "\n".join([
        "---",
        f'title: "{p.title.replace("\"", "\\\"")}"',
        f'summary: "{clean_text(summary)[:140].replace("\"", "\\\"")}"',
        "params:",
        f'  cover: "{cover_default}"',
        f'  tagline: "{clean_text(summary).replace("\"", "\\\"")}"',
        "---\n",
    ])
    (out_dir / "_index.md").write_text(idx, encoding="utf-8")

    # chapters
    for ch in sorted(p.chapters, key=lambda x: x["num"]):
        num = ch["num"]
        fn = f"{num:02d}.md"
        body = "\n\n".join(ch["paras"]).strip() + "\n"
        md = to_frontmatter(ch["title"], weight=num) + body
        (out_dir / fn).write_text(md, encoding="utf-8")

    print(f"Wrote novel index + {len(p.chapters)} chapters to {out_dir}")


if __name__ == "__main__":
    main()
