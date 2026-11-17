import json
from pathlib import Path
import tempfile
import unittest

from rex_keybind import load, pages, record, render


def entry(id="find-file", **changes):
    return dict(id=id, category="Files", action="Find/open a file", keys="Space f f",
                context="Normal", notes="", **changes)


class ReferenceTests(unittest.TestCase):
    def test_descriptions_align_across_categories_with_different_key_lengths(self):
        short = entry()
        short.update(keys="q", action="Close", category="Explorer")
        long = entry("split")
        long.update(keys="Ctrl+W then h/j/k/l", action="Move", category="Splits")
        for width in (50, 80, 188):
            layout = pages([short, long], width, 16)
            col_width = (width - 6) // max(1, min(3, width // 60))
            positions = [(x - 3) % col_width for page in layout
                         for x, y, text, color in page if text in ("Close", "Move")]
            self.assertEqual(len(positions), 2)
            self.assertEqual(positions[0], positions[1])

    def test_renders_native_text_with_readable_keys_and_colors(self):
        layout = pages([entry()], 80, 24)
        output = render(layout[0], 80, 24, 0, len(layout), 1)
        self.assertIn("SPC f f", output)
        self.assertIn("Find/open a file", output)
        self.assertIn("FILES", output)
        self.assertIn("\033[38;2;", output)
        self.assertNotIn("\033_G", output)

    def test_record_updates_without_duplicates_or_losing_other_entries(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "keybinds.json"
            record(path, entry())
            other = entry("save")
            other.update(action="Save", keys=":w")
            record(path, other)
            updated = entry("different-name")
            updated["keys"] = "Ctrl+P or Space f f"
            record(path, updated)
            entries = load(path)
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0]["id"], "find-file")
            self.assertEqual(entries[0]["keys"], updated["keys"])
            self.assertEqual(entries[1], other)

    def test_invalid_update_preserves_saved_data(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "keybinds.json"
            record(path, entry())
            saved = path.read_bytes()
            bad = entry()
            bad["keys"] = "\033[2J"
            with self.assertRaises(ValueError):
                record(path, bad)
            self.assertEqual(path.read_bytes(), saved)

    def test_corrupt_state_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "keybinds.json"
            path.write_text('{"bad": true}')
            with self.assertRaises(ValueError):
                record(path, entry())
            self.assertEqual(json.loads(path.read_text()), {"bad": True})

    def test_overflow_pages_without_clipping_or_losing_entries(self):
        entries = []
        for i in range(100):
            item = entry(str(i))
            item.update(keys=f"Key-{i:03d}", category=f"Group {i // 10}")
            entries.append(item)
        for width, height in [(50, 16), (100, 30), (188, 42)]:
            layout = pages(entries, width, height)
            self.assertGreater(len(layout), 1)
            texts = [line[2] for page in layout for line in page]
            for item in entries:
                self.assertEqual(texts.count(item["keys"]), 1)
            for page in layout:
                for x, y, text, color in page:
                    self.assertLess(y, height - 2)
                    self.assertLess(x + len(text), width)


if __name__ == "__main__":
    unittest.main()
