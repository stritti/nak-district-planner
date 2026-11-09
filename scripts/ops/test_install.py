# SPDX-FileCopyrightText: 2026 Stephan Strittmatter
# SPDX-License-Identifier: AGPL-3.0-only

"""Behaviour tests for scripts/ops/build-bundle.sh and scripts/ops/install.sh.

Releases are served from a local directory through NAK_INSTALL_BASE_URL=file://.
"""

from __future__ import annotations

import hashlib
import io
import os
import shutil
import stat
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

OPS_DIR = Path(__file__).resolve().parent
BUILD = OPS_DIR / "build-bundle.sh"
INSTALL = OPS_DIR / "install.sh"
VERSION = "1.8.0"
BUNDLE = f"nak-district-planner-deploy-{VERSION}.tar.gz"


@unittest.skipUnless(shutil.which("tar") and shutil.which("curl"), "tar and curl needed")
class InstallTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.release = self.tmp / "rel" / f"v{VERSION}"
        self.target = self.tmp / "opt" / "nak"
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.build(self.release)

    def build(self, out: Path) -> None:
        env = {**os.environ, "SOURCE_DATE_EPOCH": "1700000000"}
        result = subprocess.run(
            [str(BUILD), VERSION, str(out)], capture_output=True, text=True, env=env, check=False
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def install(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = {**os.environ, "NAK_INSTALL_BASE_URL": f"file://{self.tmp / 'rel'}"}
        return subprocess.run(
            ["bash", str(INSTALL), "--version", VERSION, "--dir", str(self.target),
             "--bin-dir", str(self.bin), *args],
            capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL, check=False,
        )  # fmt: skip

    def sha(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def test_bundle_is_reproducible_and_holds_no_operator_data(self) -> None:
        other = self.tmp / "again"
        self.build(other)
        self.assertEqual(self.sha(self.release / BUNDLE), self.sha(other / BUNDLE))
        sums = (self.release / "SHA256SUMS").read_text()
        self.assertIn(f"{self.sha(self.release / BUNDLE)}  {BUNDLE}", sums)
        self.assertIn(f"{self.sha(self.release / 'install.sh')}  install.sh", sums)
        with tarfile.open(self.release / BUNDLE) as archive:
            names = archive.getnames()
        prefix = f"nak-district-planner-{VERSION}/"
        self.assertIn(prefix + "docker-compose.prod.yml", names)
        self.assertIn(prefix + "scripts/ops/nakctl", names)
        for forbidden in (".env", ".env.db", ".env.keycloak", ".env.keycloak-db"):
            self.assertNotIn(prefix + forbidden, names)
        self.assertFalse(any("/services/" in n or "/.git" in n for n in names))

    def test_fresh_install(self) -> None:
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.target / "VERSION").read_text().strip(), VERSION)
        nakctl = self.target / "scripts/ops/nakctl"
        self.assertTrue(stat.S_IMODE(nakctl.stat().st_mode) & stat.S_IXUSR)
        self.assertTrue((self.target / ".env.example").is_file())
        self.assertIn("setup init", result.stdout)
        wrapper = self.bin / "nakctl"
        self.assertIn(str(nakctl), wrapper.read_text())
        help_out = subprocess.run([str(wrapper), "--help"], capture_output=True, text=True)
        self.assertEqual(help_out.returncode, 0, help_out.stderr)

    def test_update_keeps_operator_data_and_needs_confirmation(self) -> None:
        self.assertEqual(self.install().returncode, 0)
        (self.target / ".env").write_text("SECRET_KEY=keep\n")
        (self.target / "backups").mkdir()
        (self.target / "backups/db.dump").write_text("data")
        compose = self.target / "docker-compose.prod.yml"
        compose.write_text("stale\n")
        self.assertEqual(self.install().returncode, 4)
        self.assertEqual(compose.read_text(), "stale\n")
        result = self.install("--yes")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotEqual(compose.read_text(), "stale\n")
        self.assertEqual((self.target / ".env").read_text(), "SECRET_KEY=keep\n")
        self.assertEqual((self.target / "backups/db.dump").read_text(), "data")
        self.assertIn("deploy update", result.stdout)

    def test_checksum_mismatch_installs_nothing(self) -> None:
        sums = self.release / "SHA256SUMS"
        sums.write_text(sums.read_text().replace(self.sha(self.release / BUNDLE), "0" * 64))
        result = self.install()
        self.assertEqual(result.returncode, 3)
        self.assertIn("Prüfsumme", result.stderr)
        self.assertFalse(self.target.exists())

    def test_pinned_checksum_must_match(self) -> None:
        result = self.install("--sha256", "a" * 64)
        self.assertEqual(result.returncode, 3)
        self.assertFalse(self.target.exists())
        good = self.install("--sha256", self.sha(self.release / BUNDLE).upper())
        self.assertEqual(good.returncode, 0, good.stderr)

    def test_rejects_paths_outside_the_release_prefix(self) -> None:
        payload = io.BytesIO()
        with tarfile.open(fileobj=payload, mode="w:gz") as archive:
            data = b"evil\n"
            info = tarfile.TarInfo(f"nak-district-planner-{VERSION}/../../evil")
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))
        (self.release / BUNDLE).write_bytes(payload.getvalue())
        digest = self.sha(self.release / BUNDLE)
        (self.release / "SHA256SUMS").write_text(f"{digest}  {BUNDLE}\n")
        result = self.install()
        self.assertEqual(result.returncode, 3)
        self.assertFalse((self.tmp / "evil").exists())
        self.assertFalse(self.target.exists())

    def test_rejects_symlinks_in_the_bundle(self) -> None:
        payload = io.BytesIO()
        with tarfile.open(fileobj=payload, mode="w:gz") as archive:
            info = tarfile.TarInfo(f"nak-district-planner-{VERSION}/link")
            info.type = tarfile.SYMTYPE
            info.linkname = "/etc/passwd"
            archive.addfile(info)
        (self.release / BUNDLE).write_bytes(payload.getvalue())
        digest = self.sha(self.release / BUNDLE)
        (self.release / "SHA256SUMS").write_text(f"{digest}  {BUNDLE}\n")
        self.assertEqual(self.install().returncode, 3)
        self.assertFalse(self.target.exists())

    def rebuild_with_manifest(self, extra: str) -> None:
        """Repack the bundle with an extra MANIFEST line and a matching SHA256SUMS."""
        prefix = f"nak-district-planner-{VERSION}"
        stage = self.tmp / "stage"
        with tarfile.open(self.release / BUNDLE) as archive:
            archive.extractall(stage, filter="data")
        manifest = stage / prefix / "MANIFEST"
        manifest.write_text(manifest.read_text() + extra + "\n")
        (stage / prefix / ".env").write_text("SECRET_KEY=from-bundle\n")
        with tarfile.open(self.release / BUNDLE, "w:gz") as archive:
            archive.add(stage / prefix, arcname=prefix)
        digest = self.sha(self.release / BUNDLE)
        (self.release / "SHA256SUMS").write_text(f"{digest}  {BUNDLE}\n")

    def test_rejects_aliased_operator_paths(self) -> None:
        self.assertEqual(self.install().returncode, 0)
        (self.target / ".env").write_text("SECRET_KEY=keep\n")
        for alias in ("./.env", ".//.env", "scripts/../.env"):
            with self.subTest(alias=alias):
                self.rebuild_with_manifest(alias)
                result = self.install("--yes")
                self.assertEqual(result.returncode, 3, result.stdout)
                self.assertIn("MANIFEST", result.stderr)
                self.assertEqual((self.target / ".env").read_text(), "SECRET_KEY=keep\n")
                shutil.rmtree(self.tmp / "stage")
                self.build(self.release)

    @unittest.skipUnless(os.geteuid() == 0, "chown needs root")
    def test_owner_gets_the_installation(self) -> None:
        import pwd

        nobody = pwd.getpwnam("nobody")
        result = self.install("--owner", "nobody")
        self.assertEqual(result.returncode, 0, result.stderr)
        for path in (self.target, self.target / "scripts/ops", self.target / "scripts/ops/nakctl"):
            self.assertEqual(path.stat().st_uid, nobody.pw_uid, path)
        self.assertIn("als nobody", result.stdout)

    def test_refuses_git_checkouts_and_foreign_directories(self) -> None:
        (self.target / ".git").mkdir(parents=True)
        result = self.install()
        self.assertEqual(result.returncode, 3)
        self.assertIn("git checkout", result.stderr)
        shutil.rmtree(self.target / ".git")
        (self.target / "notes.txt").write_text("x")
        self.assertEqual(self.install().returncode, 3)

    def test_dry_run_writes_nothing(self) -> None:
        result = self.install("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--dry-run", result.stdout)
        self.assertFalse(self.target.exists())
        self.assertFalse((self.bin / "nakctl").exists())

    def test_foreign_nakctl_in_bin_dir_is_kept(self) -> None:
        (self.bin / "nakctl").write_text("#!/bin/sh\necho mine\n")
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.bin / "nakctl").read_text(), "#!/bin/sh\necho mine\n")
        self.assertIn("bleibt unverändert", result.stderr)

    def test_invalid_input_is_a_usage_error(self) -> None:
        for args in (
            ("--version", "latest"),
            ("--sha256", "xyz"),
            ("--dir", "relative/path"),
            ("--owner", "no such user"),
            ("--owner", "nak-missing-user"),
        ):
            result = subprocess.run(
                ["bash", str(INSTALL), "--version", VERSION, *args],
                capture_output=True, text=True, check=False,
            )  # fmt: skip
            self.assertEqual(result.returncode, 2, args)
        env = {**os.environ, "NAK_INSTALL_BASE_URL": "http://example.org"}
        plain = subprocess.run(
            ["bash", str(INSTALL), "--version", VERSION],
            capture_output=True, text=True, env=env, check=False,
        )  # fmt: skip
        self.assertEqual(plain.returncode, 2)
        self.assertEqual(
            subprocess.run(["bash", str(INSTALL), "--help"], capture_output=True).returncode, 0
        )


if __name__ == "__main__":
    unittest.main()
