import unittest

from slugify import slugify


class SlugifyTest(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(slugify("Hello, World!"), "hello-world")

    def test_collapses_runs(self):
        self.assertEqual(slugify("a  --  b"), "a-b")

    def test_max_length_truncates(self):
        self.assertEqual(slugify("abcdef", max_length=4), "abcd")

    def test_max_length_no_trailing_hyphen(self):
        self.assertEqual(slugify("ab cd", max_length=3), "ab")

    def test_max_length_none_is_unchanged(self):
        self.assertEqual(slugify("Hello, World!", max_length=None), "hello-world")


if __name__ == "__main__":
    unittest.main()
