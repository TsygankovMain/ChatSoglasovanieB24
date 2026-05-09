"""Unit tests for upload-file validation (B24-7 / SEC-P2-2).

These guard the entry point for user-supplied binaries. If the whitelist
or size cap regress, an attacker could push executables onto the portal
disk via a normal /api/approval/create request.
"""

import unittest

import tests.conftest  # noqa: F401 — Django bootstrap

from approvals.serializers import (
    MAX_FILE_SIZE_BYTES,
    MAX_FILES_PER_REQUEST,
    validate_uploaded_files,
)


class _FakeUpload:
    def __init__(self, name: str, size: int):
        self.name = name
        self.size = size


class ValidateUploadedFilesTests(unittest.TestCase):
    def test_no_files_is_allowed(self):
        self.assertIsNone(validate_uploaded_files(None))
        self.assertIsNone(validate_uploaded_files([]))

    def test_pdf_passes(self):
        self.assertIsNone(
            validate_uploaded_files([_FakeUpload("contract.pdf", 1024 * 1024)])
        )

    def test_oversized_file_rejected(self):
        resp = validate_uploaded_files(
            [_FakeUpload("huge.pdf", MAX_FILE_SIZE_BYTES + 1)]
        )
        self.assertIsNotNone(resp)
        self.assertEqual(resp.status_code, 413)

    def test_too_many_files_rejected(self):
        files = [_FakeUpload(f"f{i}.pdf", 1024) for i in range(MAX_FILES_PER_REQUEST + 1)]
        resp = validate_uploaded_files(files)
        self.assertIsNotNone(resp)
        self.assertEqual(resp.status_code, 400)

    def test_executable_extension_rejected(self):
        resp = validate_uploaded_files([_FakeUpload("payload.exe", 100)])
        self.assertIsNotNone(resp)
        self.assertEqual(resp.status_code, 415)

    def test_script_extension_rejected(self):
        for name in ("evil.sh", "evil.js", "evil.php", "evil.py"):
            with self.subTest(name=name):
                resp = validate_uploaded_files([_FakeUpload(name, 100)])
                self.assertIsNotNone(resp, name)
                self.assertEqual(resp.status_code, 415)

    def test_unknown_extension_rejected(self):
        resp = validate_uploaded_files([_FakeUpload("data.xyz", 100)])
        self.assertIsNotNone(resp)
        self.assertEqual(resp.status_code, 415)

    def test_empty_file_rejected(self):
        resp = validate_uploaded_files([_FakeUpload("zero.pdf", 0)])
        self.assertIsNotNone(resp)
        self.assertEqual(resp.status_code, 400)

    def test_double_extension_uses_last_segment(self):
        # The "real" extension is .exe — we must look at the last segment, not the first.
        resp = validate_uploaded_files([_FakeUpload("cv.pdf.exe", 100)])
        self.assertIsNotNone(resp)
        self.assertEqual(resp.status_code, 415)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
