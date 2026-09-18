import unittest

from discount import apply_coupon


class CouponTest(unittest.TestCase):
    def test_percent(self):
        self.assertEqual(apply_coupon(1000, {"kind": "percent", "value": 10}), 900)

    def test_fixed(self):
        self.assertEqual(apply_coupon(1000, {"kind": "fixed", "value": 250}), 750)


if __name__ == "__main__":
    unittest.main()
