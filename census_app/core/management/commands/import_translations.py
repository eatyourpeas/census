#!/usr/bin/env python3
"""
Django management command to import translations from markdown files in docs/languages/
into the corresponding .po files, preserving HTML tags and newlines from the English template.
"""

from pathlib import Path
import re

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Import translations from docs/languages/*.md files into locale/.../django.po files"

    # Map markdown filenames to locale folder names
    LANGUAGE_MAP = {
        "arabic.md": "ar",
        "chinese.md": "zh_Hans",
        "french.md": "fr",
        "german.md": "de",
        "hindi.md": "hi",
        "italian.md": "it",
        "polish.md": "pl",
        "portuguese.md": "pt",
        "spanish.md": "es",
        "urdu.md": "ur",
        "welsh.md": "cy",
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without making changes",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # Get paths
        base_dir = Path(settings.BASE_DIR)
        docs_languages_dir = base_dir / "docs" / "languages"
        locale_dir = base_dir / "locale"

        # Read COMPLETE_STRINGS_LIST.md to get number->English mapping
        complete_strings_file = docs_languages_dir / "COMPLETE_STRINGS_LIST.md"
        self.stdout.write(f"Reading master string list from: {complete_strings_file}")

        if not complete_strings_file.exists():
            self.stdout.write(
                self.style.ERROR(f"ERROR: {complete_strings_file} not found")
            )
            return

        master_strings = self.parse_markdown_file(complete_strings_file)
        self.stdout.write(
            f"Found {len(master_strings)} numbered strings in master list\n"
        )

        # Read English .po file as template
        english_po_file = locale_dir / "en" / "LC_MESSAGES" / "django.po"
        self.stdout.write(f"Reading English template from: {english_po_file}")

        english_entries = self.parse_po_file(english_po_file)
        self.stdout.write(f"Found {len(english_entries)} English msgid entries\n")

        # Create a lookup: number -> po_entry
        # This maps the numbered master list to the .po file entries
        english_lookup = {}
        unmatched_numbers = []

        for number, item in master_strings.items():
            master_cleaned = self.clean_text(item["english"])
            if not master_cleaned:
                continue

            # Debug first few
            if number <= 3:
                self.stdout.write(
                    f"DEBUG #{number}: Master='{item['english'][:40]}' Cleaned='{master_cleaned[:40]}'"
                )

            # Find this cleaned text in the English .po entries
            found = False
            for entry in english_entries:
                entry_cleaned = self.clean_text(entry["msgid"])
                if master_cleaned == entry_cleaned:
                    english_lookup[number] = entry
                    found = True
                    if number <= 3:
                        self.stdout.write(
                            f"  ✓ Matched to msgid='{entry['msgid'][:40]}'"
                        )
                    break

            if not found:
                unmatched_numbers.append(f"#{number}: {item['english'][:50]}")
                if number <= 3:
                    self.stdout.write("  ✗ No match found")

        self.stdout.write(
            f"Matched {len(english_lookup)} strings between .po and master list"
        )
        if unmatched_numbers and len(unmatched_numbers) <= 10:
            self.stdout.write(
                self.style.WARNING(
                    f"Could not match {len(unmatched_numbers)} master list entries:"
                )
            )
            for item in unmatched_numbers[:5]:
                self.stdout.write(f"  - {item}")
        elif unmatched_numbers:
            self.stdout.write(
                self.style.WARNING(
                    f"Could not match {len(unmatched_numbers)} master list entries"
                )
            )
        self.stdout.write("")

        # Process each language
        total_updated = 0
        for md_file, locale_code in self.LANGUAGE_MAP.items():
            md_path = docs_languages_dir / md_file
            po_path = locale_dir / locale_code / "LC_MESSAGES" / "django.po"

            if not md_path.exists():
                self.stdout.write(
                    self.style.WARNING(f"⚠ Skipping {locale_code}: {md_path} not found")
                )
                continue

            if not po_path.exists():
                self.stdout.write(
                    self.style.WARNING(f"⚠ Skipping {locale_code}: {po_path} not found")
                )
                continue

            self.stdout.write(f"\n{'='*60}")
            self.stdout.write(f"Processing: {locale_code} ({md_file})")
            self.stdout.write(f"{'='*60}")

            # Parse markdown file to get translations
            translations = self.parse_markdown_file(md_path)
            self.stdout.write(f"Found {len(translations)} translations in {md_file}")

            # Read current .po file
            po_entries = self.parse_po_file(po_path)
            self.stdout.write(f"Found {len(po_entries)} entries in {po_path.name}")

            # Update translations using the number-based lookup
            updated_count, not_found = self.update_po_entries(
                po_entries, translations, english_lookup
            )

            if not_found:
                self.stdout.write(
                    self.style.WARNING(
                        f"  ⚠ Could not match {len(not_found)} translations"
                    )
                )

            if not dry_run:
                # Write back to .po file
                self.write_po_file(po_path, po_entries)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Updated {updated_count} translations in {po_path.name}"
                    )
                )
            else:
                self.stdout.write(
                    f"[DRY RUN] Would update {updated_count} translations in {po_path.name}"
                )

            total_updated += updated_count

        self.stdout.write(f"\n{'='*60}")
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Total: {total_updated} translations updated across all languages"
                )
            )
            self.stdout.write(
                "\nNow run: docker compose exec web python manage.py compilemessages"
            )
        else:
            self.stdout.write(
                f"[DRY RUN] Would update {total_updated} translations total"
            )

    def clean_text(self, text):
        """Remove HTML tags and normalize whitespace/newlines from text"""
        # Remove HTML tags
        text = re.sub(r"<[^>]+>", "", text)
        # Replace \n with space
        text = text.replace("\\n", " ")
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def parse_markdown_file(self, md_path):
        """Parse markdown file and extract number->Translation mappings

        For COMPLETE_STRINGS_LIST.md: Parses simple numbered list (1. Text)
        For language files: Parses table format (| number | English | Translation |)
        """
        translations = {}

        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check if this is the master list (simple numbered list) or a language file (table)
        if "| # |" in content or "|---|" in content:
            # Language file with table format: | number | English | Translation |
            pattern = r"\|\s*(\d+)\.\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|"

            for match in re.finditer(pattern, content, re.MULTILINE):
                number = int(match.group(1))
                english = match.group(2).strip()
                translation = match.group(3).strip()

                if number and translation:
                    translations[number] = {
                        "english": english,
                        "translation": translation,
                    }
        else:
            # Master list with simple numbered format: 1. Text
            pattern = r"^(\d+)\.\s+(.+)$"

            for match in re.finditer(pattern, content, re.MULTILINE):
                number = int(match.group(1))
                english = match.group(2).strip()

                if number and english:
                    translations[number] = {
                        "english": english,
                        "translation": "",  # No translation in master list
                    }

        return translations

    def parse_po_file(self, po_path):
        """Parse .po file and return list of entry dictionaries"""
        entries = []

        with open(po_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        current_entry = None
        in_msgid = False
        in_msgstr = False

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("#"):
                # Comment line - start of new entry
                if current_entry and current_entry.get("msgid"):
                    entries.append(current_entry)
                current_entry = {
                    "comments": [stripped],
                    "msgid": "",
                    "msgstr": "",
                }
                in_msgid = False
                in_msgstr = False

            elif stripped.startswith("msgid "):
                # Start of msgid
                in_msgid = True
                in_msgstr = False
                # Extract the quoted string
                match = re.match(r'msgid\s+"(.*)"', stripped)
                if match:
                    current_entry["msgid"] = match.group(1)

            elif stripped.startswith("msgstr "):
                # Start of msgstr
                in_msgid = False
                in_msgstr = True
                # Extract the quoted string
                match = re.match(r'msgstr\s+"(.*)"', stripped)
                if match:
                    current_entry["msgstr"] = match.group(1)

            elif stripped.startswith('"') and (in_msgid or in_msgstr):
                # Continuation line for multiline strings
                match = re.match(r'"(.*)"', stripped)
                if match:
                    if in_msgid:
                        current_entry["msgid"] += match.group(1)
                    elif in_msgstr:
                        current_entry["msgstr"] += match.group(1)

            elif not stripped:
                # Empty line - end of entry
                if current_entry and current_entry.get("msgid"):
                    entries.append(current_entry)
                current_entry = None
                in_msgid = False
                in_msgstr = False

            elif current_entry and not in_msgid and not in_msgstr:
                # Additional comment lines
                if stripped.startswith("#"):
                    current_entry["comments"].append(stripped)

        # Don't forget the last entry
        if current_entry and current_entry.get("msgid"):
            entries.append(current_entry)

        return entries

    def restore_formatting(self, original_text, translation_text):
        """Restore HTML tags and \\n from original_text into translation_text

        Args:
            original_text: The English msgid with HTML tags and \\n
            translation_text: The clean translation without formatting

        Returns:
            The translation with HTML tags and \\n restored in the same positions
        """
        # If original has no special formatting, return translation as-is
        if "<" not in original_text and "\\n" not in original_text:
            return translation_text

        # Extract HTML tags and their positions from original
        import re

        # Find all HTML tags in original
        tag_pattern = r"<[^>]+>"
        list(re.finditer(tag_pattern, original_text))

        # Clean both texts for alignment
        clean_original = self.clean_text(original_text)
        clean_translation = translation_text.strip()

        # If cleaned texts don't match, we can't safely map formatting
        if clean_original != clean_translation:
            # Try word-by-word mapping
            original_words = clean_original.split()
            translation_words = clean_translation.split()

            if len(original_words) != len(translation_words):
                # Can't map reliably, return translation as-is
                return translation_text

        # Build result by replacing words in original with translation words

        # Replace text content while preserving tags and \\n
        # Split original into parts (tags and text)
        parts = re.split(r"(<[^>]+>)", original_text)

        # Get translation words
        translation_words = clean_translation.split()
        word_idx = 0

        new_parts = []
        for part in parts:
            if part.startswith("<") and part.endswith(">"):
                # Keep HTML tag as-is
                new_parts.append(part)
            else:
                # Replace text content with translation words
                # Preserve \\n positions
                text_parts = part.split("\\n")
                new_text_parts = []

                for i, text_part in enumerate(text_parts):
                    words = text_part.split()
                    new_words = []

                    for _ in words:
                        if word_idx < len(translation_words):
                            new_words.append(translation_words[word_idx])
                            word_idx += 1

                    new_text_parts.append(
                        " ".join(new_words) if new_words else text_part.strip()
                    )

                new_parts.append("\\n".join(new_text_parts))

        return "".join(new_parts)

    def update_po_entries(self, po_entries, translations, english_lookup):
        """Update po_entries with translations using number-based english_lookup

        Args:
            po_entries: List of entries from the target language .po file
            translations: Dict mapping number -> {english, translation}
            english_lookup: Dict mapping number -> English .po entry

        Returns:
            Tuple of (updated_count, not_found_list)
        """
        updated_count = 0
        not_found = []

        for number, translation_data in translations.items():
            clean_translation = translation_data["translation"]

            # Find the corresponding English entry by number
            if number in english_lookup:
                english_entry = english_lookup[number]
                original_msgid = english_entry["msgid"]

                # Restore formatting from English msgid to translation
                formatted_translation = self.restore_formatting(
                    original_msgid, clean_translation
                )

                # Find this msgid in the po_entries and update it
                for entry in po_entries:
                    if entry["msgid"] == original_msgid:
                        # Update msgstr if it's different
                        if entry["msgstr"] != formatted_translation:
                            entry["msgstr"] = formatted_translation
                            updated_count += 1
                        break
            else:
                not_found.append(f"#{number}: {translation_data['english'][:50]}")

        return updated_count, not_found

    def write_po_file(self, po_path, entries):
        """Write updated entries back to .po file"""
        with open(po_path, "r", encoding="utf-8") as f:
            original_content = f.read()

        # Preserve the header
        # Find end of header (first location comment)
        header_match = re.search(r"\n\n#:", original_content)
        header_end = (
            header_match.start() + 1
            if header_match
            else original_content.find("\nmsgid")
        )
        if header_end == -1:
            header = ""
        else:
            header = original_content[: header_end + 1]

        # Build new content
        new_content = header

        for entry in entries:
            if not entry["msgid"]:  # Skip empty msgid (header entry)
                continue

            # Write comments
            for comment in entry["comments"]:
                new_content += comment + "\n"

            # Write msgid and msgstr
            new_content += f'msgid "{entry["msgid"]}"\n'
            new_content += f'msgstr "{entry["msgstr"]}"\n'
            new_content += "\n"

        # Write to file
        with open(po_path, "w", encoding="utf-8") as f:
            f.write(new_content)
