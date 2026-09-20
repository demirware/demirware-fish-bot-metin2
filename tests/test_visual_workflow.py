from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from visual_workflow import WorkflowRunner, WorkflowError, validate_workflow, TemplateMatcher
from profile_validation import validate_profile


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.port = Mock()

    def sleep(self, seconds):
        self.now += seconds

    def runner(self, **kw):
        return WorkflowRunner(self.port, clock=lambda: self.now, sleep=self.sleep, **kw)

    def test_action_sent_once_then_postcondition_verified(self):
        recipe = {"steps": [{"action": "click", "template": "shop.png"},
                             {"action": "expect", "template": "stock.png"}]}
        self.port.attempt.side_effect = [False, True, False, True]
        self.runner().run(recipe)
        self.assertEqual([call.args[0]["action"] for call in self.port.attempt.call_args_list],
                         ["click", "click", "expect", "expect"])

    def test_timeout_never_advances_to_next_step(self):
        self.port.attempt.return_value = False
        recipe = {"steps": [{"action": "click", "template": "absent.png", "timeout": .2},
                             {"action": "expect", "template": "stock.png"}]}
        with self.assertRaises(WorkflowError):
            self.runner().run(recipe)
        self.assertTrue(all(c.args[0]["action"] == "click" for c in self.port.attempt.call_args_list))

    def test_cancel_prevents_all_input(self):
        with self.assertRaises(WorkflowError):
            self.runner(cancelled=lambda: True).run({"steps": [{"action": "expect", "template": "x.png"}]})
        self.port.attempt.assert_not_called()

    def test_pause_prevents_input_until_bounded_timeout(self):
        with self.assertRaises(WorkflowError):
            self.runner(paused=lambda: True).run({"steps": [{"action": "expect", "template": "x.png", "timeout": .2}]})
        self.port.attempt.assert_not_called()

    def test_unverified_mutation_and_nonfinite_timeout_rejected(self):
        for recipe in ({"steps": [{"action": "click", "template": "x"}]},
                       {"steps": [{"action": "expect", "template": "x", "timeout": float("nan")}]},
                       {"steps": [1]}, {"steps": [{"action": "shell", "template": "x"}]}):
            with self.assertRaises(ValueError):
                validate_workflow(recipe)

    def test_profile_rejects_unsafe_or_incomplete_settings(self):
        for profile in ({"operations": {"poll_interval": 0}},
                        {"bait_keys": ["1", "1"]},
                        {"bait_quantity": -1},
                        {"operations": {"jigsaw_every_rounds": 5}},
                        {"inv_page_1_pos": [1]},
                        {"operations": {"max_recoveries": 2.5}}):
            with self.assertRaises(ValueError):
                validate_profile(profile)


class ImageMatchingTests(unittest.TestCase):
    def test_unique_match_found_and_duplicate_rejected(self):
        import cv2
        import numpy as np
        rng = np.random.default_rng(1234)
        template = rng.integers(20, 250, (16, 16, 3), dtype=np.uint8)
        frame = np.zeros((100, 140, 3), dtype=np.uint8)
        frame[10:26, 20:36] = template
        with tempfile.TemporaryDirectory() as temp:
            path = str(Path(temp) / "template.png")
            cv2.imwrite(path, template)
            matcher = TemplateMatcher()
            self.assertEqual(matcher.locate(frame, path), (28, 18))
            frame[60:76, 90:106] = template
            self.assertIsNone(matcher.locate(frame, path))

    def test_missing_image_and_blank_template_fail(self):
        import cv2
        import numpy as np
        matcher = TemplateMatcher()
        with tempfile.TemporaryDirectory() as temp:
            path = str(Path(temp) / "blank.png")
            cv2.imwrite(path, np.zeros((20, 20, 3), dtype=np.uint8))
            with self.assertRaises(WorkflowError):
                matcher.load(path)
            with self.assertRaises(OSError):
                matcher.load(str(Path(temp) / "missing.png"))
