from pathlib import Path

import os
from tempfile import TemporaryDirectory
from playwright.sync_api import sync_playwright

import struct
import zlib

ROOT = Path(__file__).resolve().parents[1]


def png():
    def chunk(tag, data):
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data))
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">2I5B", 4, 2, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress((b"\x00" + b"\xff\x00\x00" * 4) * 2))
        + chunk(b"IEND", b"")
    )


with sync_playwright() as p, TemporaryDirectory() as temp:
    browser = p.chromium.launch(executable_path=os.environ.get("CHROME_PATH"))
    page = browser.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto((ROOT / "index.html").as_uri())
    page.locator("#file").set_input_files(
        {"name": "original.png", "mimeType": "image/png", "buffer": png()}
    )
    page.locator("#width").fill("2")
    page.wait_for_function(
        "document.getElementById('preview').width === 2 && document.getElementById('preview').height === 1"
    )
    with page.expect_download() as download:
        page.locator("#save").click()
    assert download.value.suggested_filename == "original-resized.jpg"
    dest = Path(temp) / "export.jpg"
    download.value.save_as(dest)
    assert dest.read_bytes()[:2] == b"\xff\xd8"
    assert not errors, errors
    browser.close()
