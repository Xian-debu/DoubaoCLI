"""Tests for doubao.file_upload."""

import sys
from pathlib import Path
from unittest.mock import MagicMock
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from doubaocli.file_upload import (
    is_file_supported, upload_file, upload_multiple,
    get_uploaded_files, clear_files,
)


def make_page():
    page = MagicMock()
    page.locator.return_value.first.count.return_value = 1
    return page


def test_is_file_supported_pdf():
    assert is_file_supported("test.pdf") is True


def test_is_file_supported_png():
    assert is_file_supported("test.png") is True


def test_is_file_supported_unsupported():
    assert is_file_supported("test.xyz") is False


def test_is_file_supported_code():
    assert is_file_supported("test.py") is True
    assert is_file_supported("test.js") is True


def test_upload_file_not_found():
    page = make_page()
    ok = upload_file(page, "/nonexistent/file.pdf")
    assert ok is False


def test_upload_file_unsupported_type():
    page = make_page()
    # Create temp file
    p = Path("/tmp/test_unsupported.xyz")
    p.write_text("test")
    ok = upload_file(page, p)
    p.unlink()
    assert ok is False


def test_get_uploaded_files_empty():
    page = make_page()
    page.evaluate.return_value = []
    files = get_uploaded_files(page)
    assert files == []


def test_get_uploaded_files_with_data():
    page = make_page()
    page.evaluate.return_value = ["test.pdf", "image.png"]
    files = get_uploaded_files(page)
    assert len(files) == 2


def run_all():
    test_is_file_supported_pdf()
    test_is_file_supported_png()
    test_is_file_supported_unsupported()
    test_is_file_supported_code()
    test_upload_file_not_found()
    test_upload_file_unsupported_type()
    test_get_uploaded_files_empty()
    test_get_uploaded_files_with_data()
    print(f"  [file_upload] 8 tests passed")


if __name__ == "__main__":
    run_all()
