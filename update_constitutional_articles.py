#!/usr/bin/env python3
"""
update_constitutional_articles.py

Automates the extraction and formatting of Articles from the Meritocratic Republic of Canada
DOCX into properly indented JSON files for web display.

Follows the exact indentation rules from indenting instructions.txt:
- Top-level (1., 2., ...): 0 leading spaces before number; text after "X.     "
- Letter (a), b), ...): 6 leading spaces before letter
- Roman (i), ii), ...): 12 leading spaces before roman
- Parenthesised ((i), (ii), ...): 18 leading spaces before parenthesis
- Continuation lines: aligned under the start of the clause text (typically 8, 14, 20, 26 spaces)

Usage:
  python update_constitutional_articles.py                # Regenerate ALL articles (01 to 31)
  python update_constitutional_articles.py --article 5    # Only Article 5 (padded as 05)
  python update_constitutional_articles.py --article 1 --dry-run   # Preview without writing

The script reads from the master DOCX and produces article-XX.json in the output directory.
This ensures the digital representation of the Constitution remains synchronized with the
authoritative source document, supporting transparent dissemination of the Meritocratic framework.
"""

import re
import json
import argparse
from pathlib import Path
from typing import Optional, Tuple, List
from docx import Document

# Configuration
DOCX_PATH = Path(r"C:\Users\Joseph E Postma\Documents\Illuminism\MRC\websources\completePDF\Meritocratic Republic of Canada.docx")
OUTPUT_DIR = Path(r"C:\Users\Joseph E Postma\Documents\Illuminism\MRC\websources\articles")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def detect_clause_level(line: str) -> Optional[Tuple[str, str, str, int]]:
    """
    Detect clause marker and return (level, marker, rest_text, base_indent).
    Returns None if not a clause starter.
    """
    stripped = line.strip()
    if not stripped:
        return None

    # Top-level: 1. or 10. etc.
    m = re.match(r'^(\d+)\.\s+(.*)$', stripped)
    if m:
        marker = f"{m.group(1)}."
        rest = m.group(2)
        return ("top", marker, rest, 0)

    # Roman numeral subclause: i) ii) iii) ... (any valid roman numeral)
    m = re.match(r'^([ivxlcdm]+)\)\s+(.*)$', stripped, re.IGNORECASE)
    if m:
        roman_str = m.group(1).lower()
        # Special-case: single letters that will never be used as roman numerals
        if roman_str in ('c', 'd', 'l'):
            pass  # fall through to letter check
        else:
            marker = roman_str + ")"
            rest = m.group(2)
            return ("roman", marker, rest, 12)

    # Letter subclause: a) b) etc. (single letter, after roman check)
    m = re.match(r'^([a-z])\)\s+(.*)$', stripped, re.IGNORECASE)
    if m:
        marker = f"{m.group(1)})"
        rest = m.group(2)
        return ("letter", marker, rest, 6)

    # Parenthesised roman: (i) (ii) ... up to (xxx)
    paren_roman = (
        r'^\((m{0,3})(c[md]|d?c{0,3})(x[cl]|l?x{0,3})(i[xv]|v?i{0,3})\)\s+(.*)$'
    )
    m = re.match(paren_roman, stripped, re.IGNORECASE)
    if m:
        marker = "(" + (m.group(1) + m.group(2) + m.group(3) + m.group(4)).lower() + ")"
        rest = m.group(5)
        return ("paren", marker, rest, 18)

    return None

def format_article_content(content_block: str) -> str:
    """
    Reformat the raw content block into a single string with exact indentation per rules.
    Handles both numbered clauses and unnumbered introductory/closing paragraphs.
    """
    lines = content_block.split('\n')
    formatted_lines: List[str] = []
    current_clause = None  # (level, marker, text_parts[])

    def flush_clause():
        nonlocal current_clause
        if current_clause is None:
            return
        level, marker, parts = current_clause
        text = ' '.join(parts)
        if level == "top":
            prefix = f"{marker}     {text}"
        elif level == "letter":
            prefix = f"{' ' * 6}{marker}     {text}"
        elif level == "roman":
            prefix = f"{' ' * 12}{marker}     {text}"
        elif level == "paren":
            prefix = f"{' ' * 18}{marker}     {text}"
        else:
            prefix = text
        if level == "top" and formatted_lines and formatted_lines[-1] not in ('', None):
            formatted_lines.append('')
        formatted_lines.append(prefix)
        current_clause = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        detection = detect_clause_level(line)

        if detection:
            flush_clause()
            level, marker, rest, _ = detection
            current_clause = (level, marker, [rest])
        else:
            # Unnumbered paragraph or continuation
            if current_clause is not None:
                # Treat as continuation of current clause
                current_clause[2].append(stripped)
            else:
                # Unnumbered paragraph at 0 spaces
                if formatted_lines and formatted_lines[-1] not in ('', None):
                    formatted_lines.append('')
                formatted_lines.append(stripped)

    flush_clause()

    result = '\n'.join(formatted_lines)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()

def extract_article_block(doc: Document, article_num: int) -> Optional[Tuple[str, str, str]]:
    """
    Extract (title, content_block, precis) for a given article number from the DOCX.
    Collects every paragraph between the target article heading and the next article heading,
    then splits the collected block on the first "Precis:" paragraph.
    """
    paragraphs = doc.paragraphs
    title = None
    article_paras = []
    in_article = False

    article_heading_pattern = re.compile(rf'^Article\s+{article_num}\s*[–-]\s*(.+)$', re.IGNORECASE)
    next_article_pattern = re.compile(r'^Article\s+\d+\s*[–-]', re.IGNORECASE)

    for para in paragraphs:
        text = para.text.strip()
        if not text:
            continue

        heading_match = article_heading_pattern.match(text)
        if heading_match and not in_article:
            title = heading_match.group(1).strip()
            in_article = True
            continue

        if in_article:
            if next_article_pattern.match(text):
                break
            article_paras.append(text)

    if not title or not article_paras:
        return None

    # Find the first paragraph that starts with "Precis:"
    precis_start = None
    for i, p in enumerate(article_paras):
        if p.lower().startswith('precis:'):
            precis_start = i
            break

    if precis_start is not None:
        content_paras = article_paras[:precis_start]
        precis_paras = article_paras[precis_start:]
        # Strip the "Precis:" prefix from the first precis paragraph
        if precis_paras:
            precis_paras[0] = precis_paras[0][7:].strip()
    else:
        content_paras = article_paras
        precis_paras = []

    content_block = '\n'.join(content_paras)
    precis = '\n\n'.join([p for p in precis_paras if p]) if precis_paras else ""

    return title, content_block, precis

def generate_article_json(article_num: int, dry_run: bool = False) -> Optional[dict]:
    """Generate the JSON dict for one article from the DOCX."""
    doc = Document(DOCX_PATH)

    result = extract_article_block(doc, article_num)
    if not result:
        print(f"ERROR: Could not extract Article {article_num}")
        return None

    title, content_raw, precis = result

    formatted_content = format_article_content(content_raw)

    article_data = {
        "number": article_num,
        "title": title,
        "content": formatted_content,
        "precis": precis
    }

    if not dry_run:
        json_path = OUTPUT_DIR / f"article-{article_num:02d}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(article_data, f, ensure_ascii=False, indent=2)
        print(f"Generated: {json_path}")
    else:
        print(f"DRY-RUN Article {article_num}: {title}")
        print(f"Content preview (first 500 chars):\n{formatted_content[:500]}...\n")
        print(f"Precis preview (first 300 chars):\n{precis[:300]}...\n")

    return article_data

def main():
    parser = argparse.ArgumentParser(description="Update constitutional article JSON files from master DOCX.")
    parser.add_argument("--article", type=int, required=True, help="Article number to process (1-31)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing files")
    args = parser.parse_args()

    if not 1 <= args.article <= 31:
        print("Article number must be between 1 and 31.")
        return
    generate_article_json(args.article, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
