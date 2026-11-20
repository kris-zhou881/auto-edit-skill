import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PackageLayoutTests(unittest.TestCase):
    def test_one_user_facing_skill_entrypoint(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        metadata = (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("name: douyin-automation", skill)
        self.assertIn('display_name: "抖音自动化skill"', metadata)
        self.assertEqual(list(ROOT.glob("*/SKILL.md")), [])

    def test_director_and_remotion_modules_are_packaged(self):
        required = [
            "modules/douyin-style-director/SKILL.md",
            "modules/douyin-style-director/scripts/director.py",
            "modules/douyin-style-director/references/production.md",
            "modules/remotion-motion-graphics/SKILL.md",
            "modules/remotion-motion-graphics/assets/theme.ts",
            "modules/remotion-motion-graphics/references/design-rules.md",
        ]
        for relative_path in required:
            with self.subTest(path=relative_path):
                self.assertTrue((ROOT / relative_path).is_file())
        self.assertEqual(list((ROOT / "modules").rglob("agents/openai.yaml")), [])


if __name__ == "__main__":
    unittest.main()
