"""Regression guards for owner-only manual UI preview signing workflow."""
import unittest
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "android-ci.yml"
PREVIEW_REF = "refs/heads/ux/editor-caption-beta7-preview"
EXISTING_BETA310_CERT = "295b1bbcebb8419c8361b077e41b913410207ee3ecb3bc0da3acf150c8e1c325"


class PreviewWorkflowGuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        cls.preview = workflow.split("\n  ui-beta-preview:\n", 1)[1]

    def test_preview_signs_only_on_explicit_owner_manual_branch(self):
        self.assertIn(
            f"if: github.event_name == 'workflow_dispatch' && github.ref == '{PREVIEW_REF}'",
            self.preview,
        )
        self.assertIn("test \"$GITHUB_EVENT_NAME\" = \"workflow_dispatch\"", self.preview)
        self.assertIn(f'test "$GITHUB_REF" = "{PREVIEW_REF}"', self.preview)
        self.assertIn("needs: [build, media-device, modern-services]", self.preview)

    def test_signing_fingerprint_and_upgrade_checks_are_required(self):
        self.assertIn("SUBLOKA_PROTOTYPE_SIGNING: ${{ secrets.SUBLOKA_PROTOTYPE_SIGNING }}", self.preview)
        self.assertIn(
            "python3 tools/verify_beta_package.py preview-apk/package-info.txt preview-apk/subloka-ui-beta.apk",
            self.preview,
        )
        self.assertIn(EXISTING_BETA310_CERT, self.preview)
        self.assertIn("apksigner\" verify", self.preview)
        self.assertIn(
            "python3 tools/check_beta_launch.py preview-apk/subloka-ui-beta.apk",
            self.preview,
        )

    def test_normal_pr_jobs_never_run_owner_signing(self):
        self.assertIn("on:\n  push:", WORKFLOW.read_text(encoding="utf-8"))
        self.assertIn("  pull_request:\n  workflow_dispatch:", WORKFLOW.read_text(encoding="utf-8"))
        self.assertIn("name: subloka-ui-beta-preview-apk", self.preview)


if __name__ == "__main__":
    unittest.main()
