#!/usr/bin/env python3
"""
Import translations from markdown files in docs/languages/
into the corresponding .po files, preserving HTML tags and newlines from the English template.

Usage:
    python3 import_translations_standalone.py [--dry-run]
"""

import re
import sys
from pathlib import Path


# Map markdown filenames to locale folder names
LANGUAGE_MAP = {
    'arabic.md': 'ar',
    'chinese.md': 'zh_Hans',
    'french.md': 'fr',
    'german.md': 'de',
    'hindi.md': 'hi',
    'italian.md': 'it',
    'polish.md': 'pl',
    'portuguese.md': 'pt',
    'spanish.md': 'es',
    'urdu.md': 'ur',
    'welsh.md': 'cy',
}


def clean_text(text):
    """Remove HTML tags and normalize whitespace/newlines from text"""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Replace \n with space
    text = text.replace('\\n', ' ')
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def parse_markdown_file(md_path):
    """Parse markdown file and extract English->Translation mappings"""
    translations = {}

    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Match table rows with format: | number | English | Translation |
    pattern = r'\|\s*\d+\.\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|'

    for match in re.finditer(pattern, content, re.MULTILINE):
        english = match.group(1).strip()
        translation = match.group(2).strip()

        if english and translation:
            # Clean the English text for lookup
            cleaned_english = clean_text(english)
            if cleaned_english:
                translations[cleaned_english] = translation

    return translations


def parse_po_file(po_path):
    """Parse .po file and return list of entry dictionaries"""
    entries = []

    with open(po_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    current_entry = {
        'comments': [],
        'msgid': '',
        'msgstr': '',
        'msgid_lines': [],
        'msgstr_lines': [],
    }

    in_msgid = False
    in_msgstr = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith('#'):
            # Comment line
            if in_msgid or in_msgstr:
                # Save previous entry
                if current_entry['msgid'] is not None:
                    entries.append(current_entry)
                current_entry = {
                    'comments': [line.rstrip()],
                    'msgid': '',
                    'msgstr': '',
                    'msgid_lines': [],
                    'msgstr_lines': [],
                }
                in_msgid = False
                in_msgstr = False
            else:
                current_entry['comments'].append(line.rstrip())

        elif stripped.startswith('msgid'):
            # Start of msgid
            in_msgid = True
            in_msgstr = False
            # Extract the quoted string
            match = re.match(r'msgid\s+"(.*)"', stripped)
            if match:
                current_entry['msgid'] = match.group(1)
                current_entry['msgid_lines'].append(line.rstrip())

        elif stripped.startswith('msgstr'):
            # Start of msgstr
            in_msgid = False
            in_msgstr = True
            # Extract the quoted string
            match = re.match(r'msgstr\s+"(.*)"', stripped)
            if match:
                current_entry['msgstr'] = match.group(1)
                current_entry['msgstr_lines'].append(line.rstrip())

        elif stripped.startswith('"') and (in_msgid or in_msgstr):
            # Continuation of msgid or msgstr (multiline)
            match = re.match(r'"(.*)"', stripped)
            if match:
                if in_msgid:
                    current_entry['msgid'] += match.group(1)
                    current_entry['msgid_lines'].append(line.rstrip())
                elif in_msgstr:
                    current_entry['msgstr'] += match.group(1)
                    current_entry['msgstr_lines'].append(line.rstrip())

        elif not stripped:
            # Empty line - end of entry
            if current_entry['msgid'] is not None:
                entries.append(current_entry)
            current_entry = {
                'comments': [],
                'msgid': '',
                'msgstr': '',
                'msgid_lines': [],
                'msgstr_lines': [],
            }
            in_msgid = False
            in_msgstr = False

    # Don't forget the last entry
    if current_entry['msgid'] is not None and current_entry['msgid']:
        entries.append(current_entry)

    return entries


def update_po_entries(po_entries, translations, english_lookup):
    """Update po_entries with translations using english_lookup for matching"""
    updated_count = 0
    not_found = []

    for translation_key, translation_value in translations.items():
        # Find the corresponding English entry
        if translation_key in english_lookup:
            english_entry = english_lookup[translation_key]
            original_msgid = english_entry['msgid']

            # Find this msgid in the po_entries and update it
            for entry in po_entries:
                if entry['msgid'] == original_msgid:
                    # Update msgstr if it's different
                    if entry['msgstr'] != translation_value:
                        entry['msgstr'] = translation_value
                        updated_count += 1
                    break
        else:
            not_found.append(translation_key[:60])

    return updated_count, not_found


def write_po_file(po_path, entries):
    """Write updated entries back to .po file"""
    # Read original to preserve header
    with open(po_path, 'r', encoding='utf-8') as f:
        original_lines = f.readlines()

    # Find where the first real msgid starts (after header)
    header_lines = []
    for i, line in enumerate(original_lines):
        if line.strip().startswith('msgid') and i > 0:
            # Check if previous entries were header
            if i > 5:  # Header is usually first few lines
                break
        if not line.strip().startswith('msgid'):
            header_lines.append(line)
        else:
            break

    # Write new file
    with open(po_path, 'w', encoding='utf-8') as f:
        # Write header
        for line in header_lines:
            f.write(line)

        # Write entries
        for entry in entries:
            if not entry['msgid']:  # Skip empty msgid
                continue

            # Write comments
            for comment in entry['comments']:
                f.write(comment + '\n')

            # Write msgid
            f.write(f'msgid "{entry["msgid"]}"\n')

            # Write msgstr
            f.write(f'msgstr "{entry["msgstr"]}"\n')

            # Empty line between entries
            f.write('\n')


def main():
    dry_run = '--dry-run' in sys.argv

    # Get paths
    base_dir = Path(__file__).parent
    docs_languages_dir = base_dir / 'docs' / 'languages'
    locale_dir = base_dir / 'locale'

    # Read English .po file as template
    english_po_file = locale_dir / 'en' / 'LC_MESSAGES' / 'django.po'
    print(f"Reading English template from: {english_po_file}")

    if not english_po_file.exists():
        print(f"ERROR: English .po file not found at {english_po_file}")
        sys.exit(1)

    english_entries = parse_po_file(english_po_file)
    print(f"Found {len(english_entries)} English msgid entries\n")

    # Create a lookup by cleaned English text
    english_lookup = {}
    for entry in english_entries:
        cleaned = clean_text(entry['msgid'])
        if cleaned:
            english_lookup[cleaned] = entry

    print(f"Created lookup with {len(english_lookup)} unique cleaned strings\n")

    # Process each language
    total_updated = 0

    for md_file, locale_code in LANGUAGE_MAP.items():
        md_path = docs_languages_dir / md_file
        po_path = locale_dir / locale_code / 'LC_MESSAGES' / 'django.po'

        if not md_path.exists():
            print(f"⚠ Skipping {locale_code}: {md_path} not found")
            continue

        if not po_path.exists():
            print(f"⚠ Skipping {locale_code}: {po_path} not found")
            continue

        print(f"\n{'='*60}")
        print(f"Processing: {locale_code} ({md_file})")
        print(f"{'='*60}")

        # Parse markdown file to get translations
        translations = parse_markdown_file(md_path)
        print(f"Found {len(translations)} translations in {md_file}")

        # Read current .po file
        po_entries = parse_po_file(po_path)
        print(f"Found {len(po_entries)} entries in {po_path.name}")

        # Update translations
        updated_count, not_found = update_po_entries(po_entries, translations, english_lookup)

        if not_found and len(not_found) <= 10:
            print(f"  ⚠ Could not match {len(not_found)} strings:")
            for text in not_found[:5]:
                print(f"    - {text}...")
        elif not_found:
            print(f"  ⚠ Could not match {len(not_found)} strings")

        if not dry_run:
            # Write back to .po file
            write_po_file(po_path, po_entries)
            print(f"✓ Updated {updated_count} translations in {po_path.name}")
        else:
            print(f"[DRY RUN] Would update {updated_count} translations in {po_path.name}")

        total_updated += updated_count

    print(f"\n{'='*60}")
    if not dry_run:
        print(f"✓ Total: {total_updated} translations updated across all languages")
        print("\nNow run: docker compose exec web python manage.py compilemessages")
    else:
        print(f"[DRY RUN] Would update {total_updated} translations total")


if __name__ == '__main__':
    main()
