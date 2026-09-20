import unittest

from pager import page_count


class PageCountTest(unittest.TestCase):
    def test_exact_pages(self):
        self.assertEqual(page_count(20, 10), 2)

    def test_rejects_zero_size(self):
        with self.assertRaises(ValueError):
            page_count(5, 0)


if __name__ == "__main__":
    unittest.main()
