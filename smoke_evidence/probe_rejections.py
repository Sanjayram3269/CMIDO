"""Probe how the live External Data uploader rejects bad files.

Uploads an empty CSV, an unsupported .txt and a malformed JSON to the *scoped*
External Data input and dumps the main-region text for each, so the browser
smoke assertions match what the app actually renders.
"""

from __future__ import annotations

import json
import pathlib
import sys

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8502/"
EV = pathlib.Path("smoke_evidence")
OUT: dict = {}


def main() -> int:
    tmp = EV / "_probe_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    empty_csv = tmp / "empty_input.csv"
    empty_csv.write_bytes(b"")
    txt = tmp / "not_a_supported_table.txt"
    txt.write_text("month_index,observed_units\n1,120\n", encoding="utf-8")
    bad_json = tmp / "malformed_input.json"
    bad_json.write_text('{"observed": [120, 140', encoding="utf-8")
    good_json = tmp / "good_input.json"
    good_json.write_text(
        json.dumps([{"month_index": 1, "observed_units": 120}]),
        encoding="utf-8",
    )

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--disable-dev-shm-usage"])
        try:
            page = browser.new_context(viewport={"width": 1500, "height": 950}).new_page()
            page.set_default_timeout(30_000)
            page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
            page.get_by_test_id("stSidebar").wait_for(state="visible")
            page.get_by_role("button", name="External Data").first.click()
            page.wait_for_timeout(3000)

            def ext_input():
                region = page.get_by_role(
                    "region", name="Choose a CSV or JSON file"
                ).first
                region.wait_for(state="attached", timeout=30_000)
                return region.locator('input[type="file"]').first

            for label, path in (
                ("empty_csv", empty_csv),
                ("unsupported_txt", txt),
                ("malformed_json", bad_json),
                ("good_json", good_json),
            ):
                ext_input().set_input_files(str(path))
                page.wait_for_timeout(4000)
                main = page.get_by_test_id("stMain").inner_text()
                OUT[label] = {
                    "has_first_rows": "First rows" in main,
                    "has_error_headline": "Could not read the uploaded file" in main,
                    "snippet": main[:1200],
                }
                print(f"===== {label} =====", flush=True)
                print(json.dumps(OUT[label], indent=1)[:1600], flush=True)

            (EV / "rejection_probe.json").write_text(
                json.dumps(OUT, indent=1), encoding="utf-8"
            )
            return 0
        finally:
            browser.close()


if __name__ == "__main__":
    raise SystemExit(main())
