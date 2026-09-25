"""The credit-to-market cascade must require all three transmission legs."""

import unittest

from core.factor_registry import FACTOR_NAMES, aggregate_factor_results


def readings(state5="WARNING", state6="WARNING", state7="WATCH"):
    states = {
        "straw1": "CRITICAL",
        "straw2": "WARNING",
        "straw3": "WATCH",
        "straw4": "WATCH",
        "straw5": state5,
        "straw6": state6,
        "straw7": state7,
    }
    score = {"SAFE": 10, "WATCH": 35, "WARNING": 60, "CRITICAL": 85}
    return {key: {"state": state, "score": score[state], "available": True} for key, state in states.items()}


class CascadeTests(unittest.TestCase):
    def test_factor_07_uses_confirmation_name(self):
        self.assertEqual(FACTOR_NAMES["straw7"], "宏观与跨市场传导确认")

    def test_requires_05_and_06_warning_plus_07_watch(self):
        self.assertTrue(aggregate_factor_results(readings())["cascade"])
        self.assertFalse(aggregate_factor_results(readings(state5="WATCH"))["cascade"])
        self.assertFalse(aggregate_factor_results(readings(state6="WATCH"))["cascade"])
        self.assertFalse(aggregate_factor_results(readings(state7="SAFE"))["cascade"])


if __name__ == "__main__":
    unittest.main()
