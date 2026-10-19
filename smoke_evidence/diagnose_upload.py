"""Phase A runtime diagnosis of the CSV upload rejection.

Enumerates every ``input[type=file]`` in the live dashboard DOM together with
its owning widget (test id + nearest visible label), then drives real uploads
against each candidate and records exactly what the browser reports.

This establishes *which layer* rejects the CSV:
  * the sidebar ``Load project JSON`` uploader (declared ``type=["json"]``), or
  * the External Data ``Choose a CSV or JSON file`` uploader
    (declared ``types=("csv", "json")``).

Evidence is written to ``smoke_evidence/upload_diagnosis.json``.
"""

from __future__ import annotations

import datetime
import json
import pathlib
import sys
import time

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8502/"
EV = pathlib.Path("smoke_evidence")
SC = EV / "screenshots"
SC.mkdir(parents=True, exist_ok=True)
FIX_CSV = EV / "safe_external_demo_deterministic_input.csv"
FIX_JSON = EV / "safe_external_demo_deterministic_input.json"

REC: dict = {
    "started_utc": datetime.datetime.now(datetime.UTC).isoformat(),
    "url": URL,
    "streamlit": None,
    "steps": [],
}


def log(step: str, status: str, detail: str) -> None:
    REC["steps"].append({"step": step, "status": status, "detail": detail})
    print(f"[{status}] {step}: {detail}", flush=True)


INVENTORY_JS = """() => {
  const out = [];
  document.querySelectorAll('input[type="file"]').forEach((el, i) => {
    const chain = [];
    let node = el;
    for (let d = 0; d < 8 && node; d++) {
      const tid = node.getAttribute ? (node.getAttribute('data-testid') || '') : '';
      const role = node.getAttribute ? (node.getAttribute('role') || '') : '';
      if (tid || role) chain.push({tag: node.tagName.toLowerCase(), tid, role});
      node = node.parentElement;
    }
    let label = '';
    const lbl = el.closest('[data-testid="stFileUploader"]');
    if (lbl) { const h = lbl.querySelector('p, label, [data-testid="stFileUploaderDropzone"]'); if (h) label = (h.innerText||'').trim(); }
    out.push({
      index: i,
      label,
      accept: el.getAttribute('accept') || '',
      in_sidebar: !!el.closest('[data-testid="stSidebar"]'),
      in_main: !!el.closest('[data-testid="stMain"]'),
      chain,
    });
  });
  return out;
}"""


def upload(page, input_locator, path: pathlib.Path, wait_ms: int = 3500) -> dict:
    input_locator.set_input_files(str(path))
    page.wait_for_timeout(wait_ms)
    body = page.inner_text("body")
    return {
        "file": path.name,
        "body_contains_not_allowed": "are not allowed" in body,
        "error_excerpt": (
            body[max(0, body.find("are not allowed") - 160): body.find("are not allowed") + 60]
            if "are not allowed" in body
            else ""
        ),
        "has_first_rows": "First rows" in body,
        "has_column_profile": "Column profile" in body,
        "has_preview_rows_heading": "Preview and profile" in body,
    }


def main() -> int:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--disable-dev-shm-usage"])
        try:
            ctx = browser.new_context(viewport={"width": 1500, "height": 950})
            page = ctx.new_page()
            console: list[str] = []
            page.on(
                "console",
                lambda m: console.append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None,
            )

            page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_selector('[data-testid="stSidebar"]', timeout=60_000)
            try:
                page.wait_for_selector('input[type="file"]', timeout=30_000)
            except Exception as exc:  # noqa: BLE001
                log("wait_file_input", "INFO", f"no file input appeared: {exc}")
            page.wait_for_timeout(3000)
            REC["streamlit"] = page.evaluate(
                "() => (window.streamlitVersion || null)"
            )
            log("launch", "PASS", f"url={page.url!r} title={page.title()!r}")

            inv = page.evaluate(INVENTORY_JS)
            REC["file_input_inventory_initial"] = inv
            log("inventory_initial", "PASS", json.dumps(inv, indent=1)[:1500])

            # --- 1. Reproduce the reported failure on the sidebar JSON loader ---
            sidebar_inputs = page.locator('[data-testid="stSidebar"] input[type="file"]')
            try:
                sidebar_inputs.first.wait_for(state="attached", timeout=30_000)
            except Exception as exc:  # noqa: BLE001
                log("sidebar_wait", "INFO", f"sidebar file input never attached: {exc}")
            n_side = sidebar_inputs.count()
            REC["sidebar_input_count"] = n_side
            if n_side and FIX_CSV.exists():
                res = upload(page, sidebar_inputs.first, FIX_CSV)
                REC["sidebar_csv_upload"] = res
                page.screenshot(path=str(SC / "diag_sidebar_csv_upload.png"))
                log(
                    "sidebar_csv_upload",
                    "INFO",
                    json.dumps(res, indent=1),
                )
                # clear it so later steps start clean
                page.reload(wait_until="domcontentloaded")
                page.wait_for_selector('[data-testid="stSidebar"]', timeout=60_000)
                page.wait_for_timeout(2500)
            else:
                log("sidebar_csv_upload", "BLOCKED", f"sidebar inputs={n_side} fixture={FIX_CSV.exists()}")

            # --- 2. Navigate to External Data ---
            nav_btn = page.get_by_role("button", name="External Data").first
            nav_btn.click()
            page.wait_for_timeout(3500)
            title_visible = page.locator("p.cmido-page-title", has_text="External Data").count() > 0
            REC["external_nav_ok"] = bool(title_visible)
            log("navigate_external", "PASS" if title_visible else "FAIL", f"url={page.url!r}")

            inv2 = page.evaluate(INVENTORY_JS)
            REC["file_input_inventory_external_page"] = inv2
            log("inventory_external", "PASS", json.dumps(inv2, indent=1)[:1500])

            # --- 3. Upload CSV to the External Data uploader, scoped correctly ---
            regions = page.get_by_role("region", name="Choose a CSV or JSON file")
            n_region = regions.count()
            REC["external_region_count"] = n_region
            log("external_region", "INFO", f"regions matching label = {n_region}")

            if n_region:
                target = regions.first.locator('input[type="file"]').first
            else:
                target = page.locator('[data-testid="stMain"] input[type="file"]').first
            if FIX_CSV.exists():
                res = upload(page, target, FIX_CSV, wait_ms=6000)
                REC["external_csv_upload"] = res
                page.screenshot(path=str(SC / "diag_external_csv_upload.png"))
                log("external_csv_upload", "PASS" if res["has_first_rows"] else "FAIL", json.dumps(res, indent=1))
            else:
                log("external_csv_upload", "BLOCKED", f"missing fixture {FIX_CSV}")

            REC["console_tail"] = console[-25:]
            (EV / "upload_diagnosis.json").write_text(
                json.dumps(REC, indent=1), encoding="utf-8"
            )
            return 0
        finally:
            browser.close()


if __name__ == "__main__":
    raise SystemExit(main())
