import unittest

from money import to_cents


class ToCentsTest(unittest.TestCase):
    def test_rounds_down(self):
        self.assertEqual(to_cents(1.234), 123)

    def test_rounds_up(self):
        self.assertEqual(to_cents(1.236), 124)

    def test_tie_rounds_up(self):
        self.assertEqual(to_cents(0.125), 13)

    def test_whole_cents_unchanged(self):
        self.assertEqual(to_cents(2.50), 250)


if __name__ == "__main__":
    unittest.main()
