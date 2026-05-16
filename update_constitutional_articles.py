#!/usr/bin/env python3
"""
update_constitutional_articles.py

Automates the extraction and formatting of Articles from the Meritocratic Republic of Canada
PDF (or adaptable to DOCX) into properly indented JSON files for web display.

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

The script reads from the master PDF and produces article-XX.json in the output directory.
This ensures the digital representation of the Constitution remains synchronized with the
authoritative source document, supporting transparent dissemination of the Meritocratic framework.
"""

import pdfplumber
import re
import json
import argparse
from pathlib import Path
from typing import Optional, Tuple, List

# Configuration
PDF_PATH = Path("/home/workdir/attachments/Meritocratic Republic of Canada - TRIM.pdf")
OUTPUT_DIR = Path("/home/workdir/artifacts")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def get_article_title_and_number(article_num: int) -> Tuple[str, str]:
    """Map article number to expected title (for validation)."""
    titles = {
        1: "Freedom of Speech and Expression",
        2: "Freedom of Inquiry and Redress",
        3: "Right to Keep and Bear Arms and Self-Defence",
        4: "Medical Freedom and the Healing Arts",
        5: "Protection of Children and the Integrity of Biological Sex",
        6: "Motherhood, Fatherhood, and the Unborn",
        7: "Religious Freedom and Cultural Continuity",
        8: "Merit, National Preference, and Demographic Continuity",
        9: "Citizenship, Descent, and National Registries",
        10: "The Two Founding Peoples and Their Languages",
        11: "Emergency Powers",
        12: "Sovereignty",
        13: "Structure of Government",
        14: "Public Service",
        15: "The Judiciary and Public Safety",
        16: "Citizenship and the Franchise",
        17: "Marriage, Divorce, and the Protection of the Family",
        18: "Education",
        19: "Agriculture and Food",
        20: "Fiscal and Monetary Sovereignty",
        21: "Health and Medical Care",
        22: "Infrastructure, Energy, and National Development",
        23: "Human Primacy",
        24: "Property Rights and Economic Liberty",
        25: "Environmental and Resource Sovereignty",
        26: "Equality Before the Law",
        27: "National Solidarity and Temporary Assistance",
        28: "Military Service, National Defence, and Policing",
        29: "Territorial Integrity and Provincial Relations",
        30: "Amendment and Revision of Articles and Provisions",
        31: "Abrogation and the Eternal Right of the People",
    }
    return titles.get(article_num, "Unknown Title"), f"{article_num:02d}"

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

    # Roman numeral subclause: i) ii) iii) iv) etc. FIRST (to catch i), ii) before single-letter a))
    m = re.match(r'^(i{1,3}|iv|v|vi{1,3}|ix|x)\)\s+(.*)$', stripped, re.IGNORECASE)
    if m:
        marker = f"{m.group(1)})"
        rest = m.group(2)
        return ("roman", marker, rest, 12)

    # Letter subclause: a) b) etc. (single letter, after roman check)
    m = re.match(r'^([a-z])\)\s+(.*)$', stripped, re.IGNORECASE)
    if m:
        marker = f"{m.group(1)})"
        rest = m.group(2)
        return ("letter", marker, rest, 6)

    # Parenthesised roman: (i) (ii) etc.
    m = re.match(r'^\((i{1,3}|iv|v|vi{1,3}|ix|x)\)\s+(.*)$', stripped, re.IGNORECASE)
    if m:
        marker = f"({m.group(1)})"
        rest = m.group(2)
        return ("paren", marker, rest, 18)

    return None

def format_article_content(content_block: str) -> str:
    """
    Reformat the raw content block into a single string with exact indentation per rules.
    """
    lines = content_block.split('\n')
    formatted_lines: List[str] = []
    last_level = None
    last_text_start_col = 0  # approximate column where clause text starts

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            # Preserve some blank lines between major sections
            if formatted_lines and formatted_lines[-1] != '':
                formatted_lines.append('')
            i += 1
            continue

        detection = detect_clause_level(line)

        if detection:
            level, marker, rest, base_indent = detection
            last_level = level

            if level == "top":
                prefix = f"{marker}     {rest}"  # 0 leading + 5 spaces after .
                last_text_start_col = len(f"{marker}     ")
            elif level == "letter":
                prefix = f"{' ' * 6}{marker}     {rest}"
                last_text_start_col = 6 + len(f"{marker}     ")
            elif level == "roman":
                prefix = f"{' ' * 12}{marker}     {rest}"
                last_text_start_col = 12 + len(f"{marker}     ")
            elif level == "paren":
                prefix = f"{' ' * 18}{marker}     {rest}"
                last_text_start_col = 18 + len(f"{marker}     ")
            else:
                prefix = stripped
                last_text_start_col = 0

            # Add blank line before new top-level clause (except first)
            if level == "top" and formatted_lines and formatted_lines[-1] not in ('', None):
                formatted_lines.append('')

            formatted_lines.append(prefix)
        else:
            # Continuation line or unnumbered header/ transitional text
            if last_level == "top":
                align = ' ' * 8 + stripped   # typical 8 spaces for top-level continuation
            elif last_level == "letter":
                align = ' ' * 14 + stripped
            elif last_level == "roman":
                align = ' ' * 20 + stripped
            elif last_level == "paren":
                align = ' ' * 26 + stripped
            else:
                # Unnumbered intro or header (0 spaces) or default
                align = stripped

            formatted_lines.append(align)

        i += 1

    # Clean up multiple blank lines
    result = '\n'.join(formatted_lines)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()

def extract_precis(full_text: str, article_start_pos: int) -> str:
    """Extract and clean the Precis section following an Article."""
    remaining = full_text[article_start_pos:]
    precis_match = re.search(r'Precis:\s*\n(.*?)(?=\nArticle \d+ –|\Z)', remaining, re.DOTALL)
    if not precis_match:
        return ""
    precis_text = precis_match.group(1).strip()
    # Normalize paragraphs
    paras = [p.strip() for p in re.split(r'\n\s*\n', precis_text) if p.strip()]
    return '\n\n'.join(paras)

def extract_article_block(full_text: str, article_num: int) -> Optional[Tuple[str, str, str]]:
    """
    Extract (title, content_block, precis) for a given article number.
    Picks the content occurrence (not TOC).
    """
    title, _ = get_article_title_and_number(article_num)
    # Pattern for title
    title_pattern = rf'Article {article_num} – {re.escape(title)}'

    matches = list(re.finditer(title_pattern, full_text))
    for m in matches:
        start_pos = m.start()
        following_text = full_text[start_pos : start_pos + 400]
        # Heuristic: real content has the first clause soon after
        if re.search(rf'{article_num}\.\s', following_text):
            # Find end: next Article or end of document
            end_search = re.search(r'\nArticle \d+ – ', full_text[start_pos + 1:])
            if end_search:
                block_end = start_pos + 1 + end_search.start()
            else:
                block_end = len(full_text)

            block = full_text[start_pos:block_end]

            # Split content and precis
            precis_split = re.split(r'\nPrecis:\s*\n', block, maxsplit=1)
            if len(precis_split) == 2:
                content_raw = precis_split[0]
                precis_raw = precis_split[1]
            else:
                content_raw = block
                precis_raw = ""

            # Clean content: remove the title line itself for formatting start
            content_lines = content_raw.split('\n')
            # Skip the "Article X – Title" line and any page number/header
            content_lines = [ln for ln in content_lines if not (ln.strip().startswith('Article ') and str(article_num) in ln)]
            content_block = '\n'.join(content_lines).strip()

            precis = '\n\n'.join([p.strip() for p in re.split(r'\n\s*\n', precis_raw) if p.strip()])

            return title, content_block, precis

    return None

def generate_article_json(article_num: int, dry_run: bool = False) -> Optional[dict]:
    """Generate the JSON dict for one article."""
    with pdfplumber.open(PDF_PATH) as pdf:
        full_text = '\n'.join(page.extract_text() or '' for page in pdf.pages)

    result = extract_article_block(full_text, article_num)
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
    parser = argparse.ArgumentParser(description="Update constitutional article JSON files from master PDF.")
    parser.add_argument("--article", type=int, help="Process only this article number (1-31)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing files")
    args = parser.parse_args()

    if args.article:
        if not 1 <= args.article <= 31:
            print("Article number must be between 1 and 31.")
            return
        generate_article_json(args.article, dry_run=args.dry_run)
    else:
        print("Regenerating all 31 Articles from the master PDF...")
        for num in range(1, 32):
            generate_article_json(num, dry_run=args.dry_run)
        print("\nAll articles processed. JSON files are in", OUTPUT_DIR)

if __name__ == "__main__":
    main()
