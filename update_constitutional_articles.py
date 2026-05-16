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
PDF_PATH = Path(r"C:\Users\Joseph E Postma\Documents\Illuminism\MRC\websources\completePDF\Meritocratic Republic of Canada.pdf")
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
    Each clause is output as a single line (original line breaks within clauses are discarded).
    """
    lines = content_block.split('\n')
    formatted_lines: List[str] = []
    current_clause = None  # (level, marker, text_parts[])
    i = 0

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
        # Add blank line before new top-level clause (except first)
        if level == "top" and formatted_lines and formatted_lines[-1] not in ('', None):
            formatted_lines.append('')
        formatted_lines.append(prefix)
        current_clause = None

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        detection = detect_clause_level(line)

        if detection:
            flush_clause()
            level, marker, rest, _ = detection
            current_clause = (level, marker, [rest])
        else:
            # Continuation text for current clause
            if current_clause is not None:
                current_clause[2].append(stripped)

        i += 1

    flush_clause()

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
    Matches "Article N – " and captures the actual title from the heading.
    """
    title_pattern = rf'Article {article_num} – (.*)'

    matches = list(re.finditer(title_pattern, full_text))
    for m in matches:
        title = m.group(1).strip()
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
            # Remove standalone page numbers (pure digits)
            content_lines = [ln for ln in content_lines if not re.match(r'^\d+$', ln.strip())]
            content_block = '\n'.join(content_lines).strip()

            # Remove page numbers (standalone numeric lines or trailing numbers)
            precis_text = re.sub(r'(?m)^\s*\d+\s*$', '', precis_raw)  # remove lines that are only digits
            precis_text = re.sub(r'\n\s*\d+\s*$', '', precis_text)    # remove trailing page number at end

            # Reconstruct paragraphs, treating single newlines inside paragraphs as continuation
            # (handles PDF page breaks inside a paragraph)
            lines = precis_text.splitlines()
            paragraphs = []
            current_para_lines = []

            sentence_end = re.compile(r'[.!?]$')

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    # blank line -> end of paragraph
                    if current_para_lines:
                        paragraphs.append(' '.join(current_para_lines))
                        current_para_lines = []
                    continue

                current_para_lines.append(stripped)

                # If line ends with sentence punctuation, treat as end of paragraph
                if sentence_end.search(stripped):
                    paragraphs.append(' '.join(current_para_lines))
                    current_para_lines = []

            # Flush any remaining lines
            if current_para_lines:
                paragraphs.append(' '.join(current_para_lines))

            precis = '\n\n'.join(paragraphs)

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
    parser.add_argument("--article", type=int, required=True, help="Article number to process (1-31)")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing files")
    args = parser.parse_args()

    if not 1 <= args.article <= 31:
        print("Article number must be between 1 and 31.")
        return
    generate_article_json(args.article, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
