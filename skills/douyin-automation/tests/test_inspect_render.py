import unittest

from scripts.inspect_render import inspect_probe


def payload(width=1080, height=1920, fps="30/1", duration="2.0", audio=True):
    streams = [
        {
            "codec_type": "video",
            "codec_name": "h264",
            "width": width,
            "height": height,
            "avg_frame_rate": fps,
        }
    ]
    if audio:
        streams.append({"codec_type": "audio", "codec_name": "aac"})
    return {"format": {"duration": duration}, "streams": streams}


class InspectRenderTests(unittest.TestCase):
    def test_expected_vertical_render_and_audio_pass(self):
        result = inspect_probe(payload(), expect_width=1080, expect_height=1920, expect_duration=2, require_audio=True)
        self.assertEqual(result["technical_status"], "passed")
        self.assertTrue(result["has_audio"])
        self.assertTrue(result["manual_review_required"])

    def test_wrong_size_fails_technical_check(self):
        result = inspect_probe(payload(width=1920, height=1080), expect_width=1080, expect_height=1920)
        self.assertEqual(result["technical_status"], "failed")

    def test_missing_required_audio_fails(self):
        result = inspect_probe(payload(audio=False), require_audio=True)
        self.assertEqual(result["technical_status"], "failed")

    def test_duration_tolerance_is_enforced(self):
        result = inspect_probe(payload(duration="2.5"), expect_duration=2)
        self.assertEqual(result["technical_status"], "failed")

    def test_missing_video_stream_fails(self):
        result = inspect_probe({"format": {"duration": "1"}, "streams": []})
        self.assertEqual(result["technical_status"], "failed")


if __name__ == "__main__":
    unittest.main()
