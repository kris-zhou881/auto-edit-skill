import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_project import validate_manifest


FIXTURE = Path(__file__).parent / "fixtures" / "mock_project.json"


def load_fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class ValidateProjectTests(unittest.TestCase):
    def test_mock_fixture_is_valid_without_claiming_real_research(self):
        data = load_fixture()
        self.assertEqual(validate_manifest(data), [])
        self.assertEqual(data["research"]["status"], "limited")

    def test_verified_research_requires_a_measured_metric(self):
        data = load_fixture()
        data["research"]["status"] = "verified"
        errors = validate_manifest(data)
        self.assertTrue(any("至少一项带时间的可见指标" in error for error in errors))

    def test_verified_research_passes_with_timestamped_raw_metric(self):
        data = load_fixture()
        data["research"]["status"] = "verified"
        data["research"]["sources"][0]["platform"] = "douyin"
        data["research"]["sources"][0]["metrics"] = [
            {"name": "likes", "raw_value": "123", "unit": "count", "observed_at": "2026-11-20T10:00:00+08:00"}
        ]
        data["script"]["claims"][0].update(status="verified", evidence_source_ids=["mock-1"])
        self.assertEqual(validate_manifest(data), [])

    def test_verified_news_only_source_does_not_prove_platform_trend(self):
        data = load_fixture()
        data["research"]["status"] = "verified"
        data["research"]["sources"][0]["metrics"] = [
            {"name": "article_likes", "raw_value": "123", "unit": "count", "observed_at": "2026-11-20T10:00:00+08:00"}
        ]
        errors = validate_manifest(data)
        self.assertTrue(any("需要目标平台来源" in error for error in errors))

    def test_douyin_video_uses_vertical_ratio(self):
        data = load_fixture()
        data["project"]["frame"].update(width=1920, height=1080, aspect_ratio="16:9")
        errors = validate_manifest(data)
        self.assertTrue(any("抖音竖版视频默认应为 9:16" in error for error in errors))

    def test_source_observation_requires_timezone(self):
        data = load_fixture()
        data["research"]["sources"][0]["observed_at"] = "2026-11-20T10:00:00"
        errors = validate_manifest(data)
        self.assertTrue(any("observed_at 必须是带时区" in error for error in errors))

    def test_verified_claim_must_reference_existing_source(self):
        data = load_fixture()
        data["script"]["claims"][0].update(status="verified", evidence_source_ids=["missing-source"])
        errors = validate_manifest(data)
        self.assertTrue(any("引用不存在的来源" in error for error in errors))

    def test_timeline_must_be_contiguous(self):
        data = load_fixture()
        data["director"]["shots"] = [
            {"start": 0, "end": 10, "asset": {"path": "a.mp4", "status": "missing"}, "claim_ids": []},
            {"start": 11, "end": 30, "asset": {"path": "b.mp4", "status": "missing"}, "claim_ids": []},
        ]
        errors = validate_manifest(data)
        self.assertTrue(any("与前一镜头不连续" in error for error in errors))

    def test_rendered_project_requires_ready_assets_and_both_outputs(self):
        data = load_fixture()
        data["editing"].update(status="rendered", render_path="out.mp4", editable_project_path="project/",)
        errors = validate_manifest(data)
        self.assertTrue(any("存在未就绪镜头素材" in error for error in errors))

    def test_qa_pass_requires_technical_and_human_review(self):
        data = load_fixture()
        data["director"]["shots"][0]["asset"].update(status="ready", path="assets/clip.mp4")
        data["editing"].update(status="qa_pass", render_path="out.mp4", editable_project_path="project/")
        errors = validate_manifest(data)
        self.assertTrue(any("技术 QA 通过" in error for error in errors))
        self.assertTrue(any("人工完整观看/听声通过" in error for error in errors))

    def test_check_files_detects_missing_ready_asset(self):
        data = load_fixture()
        data["director"]["shots"][0]["asset"].update(status="ready", path="assets/clip.mp4")
        with tempfile.TemporaryDirectory() as temporary:
            errors = validate_manifest(data, root=Path(temporary), check_files=True)
        self.assertTrue(any("声明素材就绪但文件不存在" in error for error in errors))

    def test_wrong_cover_dimensions_are_rejected(self):
        data = load_fixture()
        data["director"]["covers"][0]["width"] = 1080
        errors = validate_manifest(data)
        self.assertTrue(any("封面 horizontal 必须为 4:3 1440×1080" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
