from __future__ import annotations

import unittest

from nsealr_vault.st7789_layout import (
    SEEDSIGNER_ST7789_HEIGHT,
    SEEDSIGNER_ST7789_WIDTH,
    layout_seed_signer_st7789_review_frame,
)


class SeedSignerSt7789LayoutTests(unittest.TestCase):
    def test_review_frame_layout_stays_inside_240_square_display(self) -> None:
        frame = {
            "title": "Event",
            "page_indicator": "Page 1/4",
            "body_lines": ["Kind 1", "Created 1710000000", "Author", "abc123"],
            "body_line_styles": ["meta", "meta", "meta", "value"],
            "action_hint": "Next",
        }

        commands = layout_seed_signer_st7789_review_frame(frame)

        self.assertEqual(commands[0]["role"], "background")
        self.assertTrue(any(command["role"] == "title" for command in commands))
        self.assertTrue(any(command["role"] == "page_indicator" for command in commands))
        self.assertTrue(any(command["role"] == "action_hint" for command in commands))
        for command in commands:
            with self.subTest(command=command["role"]):
                self.assertGreaterEqual(command["x"], 0)
                self.assertGreaterEqual(command["y"], 0)
                self.assertLessEqual(command["x"] + command["width"], SEEDSIGNER_ST7789_WIDTH)
                self.assertLessEqual(command["y"] + command["height"], SEEDSIGNER_ST7789_HEIGHT)

    def test_review_frame_layout_preserves_body_line_styles(self) -> None:
        frame = {
            "title": "Tags",
            "page_indicator": "Page 3/4 Lines 1-9/29",
            "body_lines": ["Tag 1/2", "abcdef", "  continuation", "plain"],
            "body_line_styles": ["meta", "value", "value", "normal"],
            "action_hint": "Next/Scroll",
        }

        body = [
            command
            for command in layout_seed_signer_st7789_review_frame(frame)
            if command["role"] == "body_line"
        ]

        self.assertEqual([command["style"] for command in body], ["meta", "value", "value", "normal"])
        self.assertEqual([command["color"] for command in body], ["green", "yellow", "yellow", "white"])
        self.assertLess(body[-1]["y"] + body[-1]["height"], 208)

    def test_review_frame_layout_rejects_body_that_cannot_fit(self) -> None:
        frame = {
            "title": "Overflow",
            "page_indicator": "Page 1/1",
            "body_lines": [f"line {index}" for index in range(20)],
            "body_line_styles": ["normal"] * 20,
            "action_hint": "Next",
        }

        with self.assertRaisesRegex(ValueError, "body lines exceed display body area"):
            layout_seed_signer_st7789_review_frame(frame)


if __name__ == "__main__":
    unittest.main()
