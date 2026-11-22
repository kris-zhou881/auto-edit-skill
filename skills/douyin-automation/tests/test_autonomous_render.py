"""Deterministic checks for autonomous Remotion plan provenance."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from scripts.render_autonomous import GateError, check_timeline


class AutonomousRenderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.plan = {
            "fps": 30, "duration": 180,
            "shots": [
                {"from": 0, "to": 120, "type": "video", "file": "capture.mp4",
                 "source": "real local recording", "rights": "owned",
                 "source_identity": "real-capture-1", "origin": "capture"},
                {"from": 120, "to": 180, "type": "code", "source": "verified demonstration",
                 "lines": [{"at": 120, "text": "return x"}]}],
            "captions": [],
            "audio": [{"role": "voice", "file": "voice.wav",
                       "gain": 1, "from": 0, "to": 180}]
        }

    def check(self, plan=None):
        (self.work / "motion-timeline.json").write_text(json.dumps(plan or self.plan))
        return check_timeline(self.work)

    def test_valid_plan(self):
        self.assertAlmostEqual(self.check()["real_ratio"], 2/3)

    def test_voice_required(self):
        case = copy.deepcopy(self.plan)
        case["audio"] = []
        with self.assertRaisesRegex(GateError, "voice"):
            self.check(case)

    def test_real_share_above_half(self):
        case = copy.deepcopy(self.plan)
        case["shots"][0]["to"] = 90
        case["shots"][1]["from"] = 90
        with self.assertRaisesRegex(GateError, "50%"):
            self.check(case)

    def test_provenance_required(self):
        case = copy.deepcopy(self.plan)
        del case["shots"][0]["rights"]
        with self.assertRaisesRegex(GateError, "rights"):
            self.check(case)

    def test_duplicate_photo_blocked(self):
        case = copy.deepcopy(self.plan)
        case["shots"] = [
            dict(case["shots"][0], type="image", to=75),
            dict(case["shots"][0], type="image", to=150, **{"from": 75}),
            dict(case["shots"][1], **{"from": 150})]
        with self.assertRaisesRegex(GateError, "重复"):
            self.check(case)

    def test_gap_blocked(self):
        case = copy.deepcopy(self.plan)
        case["shots"][1]["from"] = 121
        with self.assertRaisesRegex(GateError, "断帧"):
            self.check(case)


if __name__ == "__main__":
    unittest.main()
