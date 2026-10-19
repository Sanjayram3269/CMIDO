"""Live browser E2E for the CMIDO External Data workspace.

Drives the real Streamlit server with Playwright/Chromium end to end:

1. navigate to the External Data page via the sidebar navigation,
2. capture the honest landing state (empty state + unavailable stages),
3. upload the shipped example fixture (``examples/external_data/``),
4. map columns onto the ``forecast_coverage`` contract,
5. run the analysis and assert results, lineage and export controls render,
6. capture screenshots and write an E2E manifest under
   ``results/external_data_e2e/``.

Requirements: ``playwright`` installed with its Chromium browser
(``python -m playwright install chromium``). The test starts its own
Streamlit server on a free port and tears it down afterwards.
"""

from __future__ import annotations

import json
import pathlib
import re
import socket
import subprocess
import sys
import time
import urllib.request

import pytest

playwright_sync_api = pytest.importorskip(
    "playwright.sync_api", reason="playwright is required for live browser E2E"
)

from playwright.sync_api import Page, expect  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
APP = ROOT / "apps" / "cmido_dashboard.py"
FIXTURE = ROOT / "examples" / "external_data" / "forecast_intervals_fixture.csv"
OUT_DIR = ROOT / "results" / "external_data_e2e"

#: Ordered E2E checks recorded into the manifest.
CHECKS: list[dict[str, object]] = []


def _record(check: str, passed: bool, detail: str = "") -> None:
    CHECKS.append({"check": check, "passed": bool(passed), "detail": detail})


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_healthy(url: str, timeout_s: float = 120.0) -> None:
    deadline = time.time() + timeout_s
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status == 200:
                    return
        except Exception as exc:  # pragma: no cover - startup polling
            last_error = exc
        time.sleep(0.5)
    raise RuntimeError(f"streamlit did not become healthy at {url}: {last_error}")


@pytest.fixture(scope="module")
def dashboard_url():
    """Start a real Streamlit server on a free port for this module."""
    if not APP.exists():  # pragma: no cover - repo layout guard
        pytest.skip(f"dashboard app not found: {APP}")
    port = _free_port()
    log_path = OUT_DIR / "streamlit_e2e.log"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    log_handle = log_path.open("w", encoding="utf-8")
    proc = subprocess.Popen(
        [
            sys.executable,
            "-B",
            "-m",
            "streamlit",
            "run",
            str(APP),
            "--server.port",
            str(port),
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
        ],
        cwd=str(ROOT),
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        _wait_healthy(f"{url}/_stcore/health")
        yield url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:  # pragma: no cover - hard teardown
            proc.kill()
            proc.wait(timeout=20)
        log_handle.close()


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        try:
            br = pw.chromium.launch(headless=True)
        except Exception as exc:  # pragma: no cover - env-dependent
            pytest.skip(
                f"chromium unavailable (run: python -m playwright install chromium): {exc}"
            )
        yield br
        br.close()


def _shot(page: Page, name: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Park the mouse away from the sidebar so nav tooltips don't blur evidence.
    page.mouse.move(1000, 40)
    page.wait_for_timeout(250)
    page.screenshot(path=str(OUT_DIR / name), full_page=True)


def _select(page: Page, label_text: str, option: str) -> None:
    """Choose *option* in the Streamlit selectbox labelled *label_text*.

    Streamlit 1.65 renders selectboxes as react-aria comboboxes: the reliable
    path is focus the input, expand with ArrowDown, then click the option.
    A background Streamlit rerun can tear down the open popup between the
    expand and the click, so the open-and-pick sequence is retried.
    """
    box = page.get_by_test_id("stSelectbox").filter(has_text=label_text).first
    field = box.locator('input[role="combobox"]').first
    last_error: Exception | None = None
    for attempt in range(3):
        field.click()
        field.press("ArrowDown")
        option_loc = page.get_by_role("option", name=option, exact=True).first
        try:
            option_loc.wait_for(state="visible", timeout=5_000)
            option_loc.click()
            return
        except Exception as exc:  # noqa: BLE001 - retried UI race
            last_error = exc
            page.wait_for_timeout(1_000)
    raise AssertionError(f"could not select {option!r} in {label_text!r}: {last_error}")


def test_external_data_upload_map_run_in_browser(dashboard_url, browser) -> None:
    """Full upload → map → validate → run → results workflow in a real browser."""
    errors: list[str] = []
    context = browser.new_context(viewport={"width": 1600, "height": 1000})
    page = context.new_page()
    page.on(
        "console",
        lambda msg: errors.append(msg.text) if msg.type == "error" else None,
    )
    page.set_default_timeout(30_000)

    # 1. Load the app and navigate to the External Data page. ---------------
    page.goto(dashboard_url, wait_until="domcontentloaded")
    page.get_by_test_id("stSidebar").wait_for(state="visible")
    page.get_by_role("button", name="External Data").first.click()
    expect(
        page.locator("p.cmido-page-title", has_text="External Data").first
    ).to_be_visible(timeout=60_000)
    _record("navigates_to_external_data_page", True, "sidebar navigation click")

    # 2. Honest landing state: empty state + unavailable stages. ------------
    expect(page.get_by_text("No file selected").first).to_be_visible()
    expect(
        page.get_by_text("Research stages not run on uploaded data").first
    ).to_be_visible()
    expect(page.get_by_text("RO1 probabilistic model training").first).to_be_visible()
    # The Run control must not be offered before a file parses.
    run_btn = page.get_by_role("button", name="Run analysis")
    assert run_btn.count() == 0 or not run_btn.first.is_visible()
    _record("landing_state_is_honest", True, "empty state + unavailable stages + no run")
    _shot(page, "e2e_01_landing_empty_state.png")

    # 3. Upload the shipped fixture. ----------------------------------------
    # Scope to this page's uploader: the shell also renders a "Load project JSON"
    # uploader in the sidebar, which must not receive the CSV.
    uploader = page.get_by_role("region", name="Choose a CSV or JSON file").first
    uploader.locator('input[type="file"]').first.set_input_files(str(FIXTURE))
    expect(page.get_by_text("First rows").first).to_be_visible(timeout=60_000)
    expect(page.get_by_text("Column profile").first).to_be_visible()
    _record("upload_and_profile_renders", True, FIXTURE.name)
    _shot(page, "e2e_02_preview_profile.png")

    # 4. Choose the forecast-coverage contract and map columns. -------------
    _select(page, "Analysis", "Forecast interval coverage")
    expect(page.get_by_text("Observed column (numeric)").first).to_be_visible()
    _select(page, "Observed column (numeric)", "observed")
    expect(page.get_by_text("Interval lower bound column (numeric)").first).to_be_visible()
    _select(page, "Interval lower bound column (numeric)", "lower_80")
    expect(page.get_by_text("Interval upper bound column (numeric)").first).to_be_visible()
    _select(page, "Interval upper bound column (numeric)", "upper_80")
    # Wait for the rerun triggered by the last required mapping to settle
    # before touching the expander (its popup would otherwise race the rerun).
    expect(page.get_by_text("Mapping is valid. The analysis can run.").first).to_be_visible(
        timeout=30_000
    )

    # Optional quantile mapping lives inside the collapsed <details> expander.
    page.get_by_test_id("stExpander").filter(has_text="Optional fields").first.locator(
        "summary"
    ).first.click()
    expect(page.get_by_text("Quantile column (numeric)").first).to_be_visible()
    _select(page, "Quantile column (numeric)", "q50")

    expect(page.get_by_text("Mapping is valid. The analysis can run.").first).to_be_visible()
    _record("mapping_validates", True, "observed/lower_80/upper_80/q50")
    _shot(page, "e2e_03_mapping_validated.png")

    # 5. Run the analysis and assert the results surface. -------------------
    # Give the q50-triggered rerun a moment, and retry the click if a rerun
    # swallowed the trigger (known Streamlit headless behaviour).
    page.wait_for_timeout(1_500)
    run_root = ROOT / "results" / "external_data_runs"
    runs_before = {p.name for p in run_root.glob("run_*")} if run_root.exists() else set()
    run_button = page.get_by_role("button", name="Run analysis").first
    results_heading = page.get_by_text("Results (computed from your uploaded data)").first
    for attempt in range(3):
        run_button.click()
        try:
            expect(results_heading).to_be_visible(timeout=20_000)
            break
        except Exception:
            if attempt == 2:
                raise
            page.wait_for_timeout(2_000)
    for label in ("Rows scored", "Coverage rate", "Mean interval width"):
        expect(page.get_by_text(label).first).to_be_visible()
    coverage = page.get_by_test_id("stMetric").filter(has_text="Coverage rate").first.inner_text()
    _record("results_metrics_render", True, coverage.replace("\n", " "))

    # Lineage + exports. The lineage table is canvas-rendered inside a
    # dataframe grid, so assert the grid + export controls, then verify the
    # persisted run record on disk (stronger than canvas text).
    expect(page.get_by_text("Run lineage").first).to_be_visible()
    expect(page.get_by_test_id("stDataFrame").last).to_be_visible()
    for dl in ("Schema mapping (JSON)", "Run summary (JSON)", "Result table (CSV)"):
        expect(page.get_by_role("button", name=dl).first).to_be_visible()
    _record("lineage_and_exports_render", True, "3 download buttons")
    _shot(page, "e2e_04_results_lineage_export.png")

    # The run must have been genuinely persisted, and the DOM metric must
    # agree with the on-disk result artifact.
    new_runs = sorted({p.name for p in run_root.glob("run_*")} - runs_before)
    assert new_runs, "no persisted run directory was created by the browser run"
    run_dir = run_root / new_runs[-1]
    record = json.loads((run_dir / "run_record.json").read_text(encoding="utf-8"))
    stored = json.loads((run_dir / "analysis_result.json").read_text(encoding="utf-8"))
    assert record["status"] == "SUCCEEDED", record
    assert record["input_filename"] == FIXTURE.name, record
    # Uploaded-data runs must be classed as derived, never canonical.
    assert record["provenance_class"] == "DER", record
    assert stored["analysis"] == "forecast_coverage", stored
    dom_coverage = float(re.search(r"[0-9]+\.[0-9]+", coverage).group(0))
    assert abs(dom_coverage - float(stored["coverage_rate"])) < 1e-6, (
        dom_coverage,
        stored["coverage_rate"],
    )
    _record(
        "run_persisted_and_matches_dom",
        True,
        f"{new_runs[-1]} coverage={stored['coverage_rate']}",
    )

    # 6. The unavailable research stages stay unavailable after a run. ------
    expect(
        page.get_by_text("Research stages not run on uploaded data").first
    ).to_be_visible()
    for label in (
        "RO1 probabilistic model training",
        "RO2 joint uncertainty propagation",
        "RO3 multi-objective procurement optimization",
    ):
        expect(page.get_by_text(label).first).to_be_visible()
    _record("unavailable_stages_stay_unavailable", True, "3 expanders")
    _shot(page, "e2e_05_unavailable_stages.png")

    # 7. No console errors during the workflow. ----------------------------
    fatal = [e for e in errors if "Uncaught" in e or "ChunkLoadError" in e]
    _record("no_fatal_console_errors", not fatal, "; ".join(fatal[:3]))
    assert not fatal, f"fatal console errors: {fatal}"

    context.close()

    # 8. Persist the E2E manifest alongside the screenshots. ----------------
    manifest = _finalize_manifest()
    assert manifest["status"] == "PASS", manifest


# ---------------------------------------------------------------------------
# Helpers shared by the upload regression tests
# ---------------------------------------------------------------------------


def _ext_uploader_input(page: Page):
    """The External Data page's own file input.

    Scoped by the uploader's accessible label so the sidebar's JSON-only
    ``Load project JSON`` loader can never receive the file.
    """
    region = page.get_by_role("region", name="Choose a CSV or JSON file").first
    region.wait_for(state="attached", timeout=30_000)
    return region.locator('input[type="file"]').first


def _goto_external(page: Page) -> None:
    page.get_by_role("button", name="External Data").first.click()
    expect(page.locator("p.cmido-page-title", has_text="External Data").first).to_be_visible(
        timeout=60_000
    )
    page.wait_for_timeout(500)


def _finalize_manifest() -> dict:
    """Write the E2E manifest from every check recorded so far."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    passed = sum(1 for c in CHECKS if c["passed"])
    manifest = {
        "stage": "EXTERNAL_DATA_E2E",
        "status": "PASS" if passed == len(CHECKS) else "FAIL",
        "checks_passed": passed,
        "checks_total": len(CHECKS),
        "checks": CHECKS,
        "screenshots": sorted(p.name for p in OUT_DIR.glob("*.png")),
    }
    (OUT_DIR / "CMIDO_EXTERNAL_DATA_E2E_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    return manifest


# ---------------------------------------------------------------------------
# Regression: CSV upload failure (Phase 2B)
# ---------------------------------------------------------------------------


def test_regression_csv_reaches_the_external_uploader_not_the_json_loader(
    dashboard_url, browser
) -> None:
    """Reproduce the observed ``text/csv files are not allowed.`` failure.

    The failure came from feeding the CSV to the *first* ``input[type=file]``
    in the DOM — the sidebar ``Load project JSON`` loader declared with
    ``type=["json"]`` — rather than from the External Data uploader, which is
    declared with ``types=("csv", "json")``. This test pins both halves so the
    mis-targeting cannot come back silently.
    """
    context = browser.new_context(viewport={"width": 1600, "height": 1000})
    page = context.new_page()
    page.set_default_timeout(30_000)
    page.goto(dashboard_url, wait_until="domcontentloaded")
    page.get_by_test_id("stSidebar").wait_for(state="visible")
    page.locator('input[type="file"]').first.wait_for(state="attached", timeout=60_000)

    # The sidebar loader is the page's first file input (the exact target the
    # failed smoke run used) and accepts JSON only.
    first = page.locator('input[type="file"]').first
    assert first.evaluate("el => !!el.closest('[data-testid=\"stSidebar\"]')") is True
    accept_first = first.get_attribute("accept") or ""
    assert ".csv" not in accept_first and ".json" in accept_first, accept_first
    _record("first_dom_file_input_is_the_json_only_sidebar_loader", True, accept_first)

    # Feeding it a CSV reproduces the reported message exactly.
    first.set_input_files(str(FIXTURE))
    page.wait_for_timeout(3_000)
    body = page.inner_text("body")
    assert "Error: text/csv files are not allowed." in body, body[:1500]
    _record("sidebar_json_loader_rejects_csv_with_observed_message", True,
            "Error: text/csv files are not allowed.")
    _shot(page, "e2e_06_regression_sidebar_rejects_csv.png")

    # The External Data uploader is a distinct input that *does* accept CSV.
    _goto_external(page)
    ext = _ext_uploader_input(page)
    assert ext.evaluate("el => !!el.closest('[data-testid=\"stMain\"]')") is True
    accept_ext = ext.get_attribute("accept") or ""
    assert ".csv" in accept_ext and ".json" in accept_ext, accept_ext
    _record("external_uploader_is_distinct_and_declares_csv_and_json", True, accept_ext)

    ext.set_input_files(str(FIXTURE))
    expect(page.get_by_text("First rows").first).to_be_visible(timeout=60_000)
    # Scoped to the main region: the sidebar's own rejection chip persists
    # across navigation and must not be confused with this page's state.
    main_text = page.get_by_test_id("stMain").inner_text()
    assert "are not allowed" not in main_text, main_text[:1500]
    _record("csv_accepted_by_external_uploader", True, FIXTURE.name)
    _shot(page, "e2e_07_regression_external_accepts_csv.png")

    context.close()
    _finalize_manifest()


def test_external_uploader_accepts_csv_and_json_and_rejects_bad_files(
    dashboard_url, browser, tmp_path
) -> None:
    """CSV and JSON parse; unsupported and malformed uploads fail honestly."""
    import csv as _csv

    context = browser.new_context(viewport={"width": 1600, "height": 1000})
    page = context.new_page()
    page.set_default_timeout(30_000)
    page.goto(dashboard_url, wait_until="domcontentloaded")
    page.get_by_test_id("stSidebar").wait_for(state="visible")
    _goto_external(page)

    # --- CSV -------------------------------------------------------------
    ext = _ext_uploader_input(page)
    ext.set_input_files(str(FIXTURE))
    expect(page.get_by_text("First rows").first).to_be_visible(timeout=60_000)
    expect(page.get_by_text("Column profile").first).to_be_visible()
    rows_metric = page.get_by_test_id("stMetric").filter(has_text="Rows").first
    csv_rows = len(list(_csv.DictReader(FIXTURE.open(encoding="utf-8"))))
    assert str(csv_rows) in rows_metric.inner_text(), rows_metric.inner_text()
    _record("csv_parses_and_profiles", True, f"rows={csv_rows}")

    # --- JSON (same data, one extra record, distinct row count) ----------
    records = [
        {k: (float(v) if "." in v else int(v)) if v.replace(".", "", 1).lstrip("-").isdigit() else v
         for k, v in row.items()}
        for row in _csv.DictReader(FIXTURE.open(encoding="utf-8"))
    ]
    records.append(dict(records[-1]))
    json_fixture = tmp_path / "forecast_intervals_fixture.json"
    json_fixture.write_text(json.dumps(records), encoding="utf-8")

    _ext_uploader_input(page).set_input_files(str(json_fixture))
    expect(page.get_by_text("First rows").first).to_be_visible(timeout=60_000)
    expect(page.get_by_text("Column profile").first).to_be_visible()
    json_rows = len(records)
    page.wait_for_timeout(1_500)
    assert str(json_rows) in rows_metric.inner_text(), rows_metric.inner_text()
    assert ".json" in page.inner_text("body")
    _record("json_parses_and_profiles", True, f"rows={json_rows}")
    _shot(page, "e2e_08_json_upload_profile.png")

    # --- Unsupported extension -------------------------------------------
    txt = tmp_path / "not_a_supported_table.txt"
    txt.write_text("month_index,observed_units\n1,120\n", encoding="utf-8")
    _ext_uploader_input(page).set_input_files(str(txt))
    page.wait_for_timeout(3_500)
    main_text = page.get_by_test_id("stMain").inner_text()
    rejected = "are not allowed" in main_text or "Unsupported file type" in main_text
    assert rejected, main_text[:2000]
    _record("unsupported_extension_rejected_honestly", True, txt.name)
    _shot(page, "e2e_09_unsupported_type_rejected.png")

    # --- Malformed JSON ---------------------------------------------------
    bad_json = tmp_path / "malformed_input.json"
    bad_json.write_text('{"observed": [120, 140', encoding="utf-8")
    _ext_uploader_input(page).set_input_files(str(bad_json))
    expect(page.get_by_text("Could not parse the JSON file", exact=False).first).to_be_visible(
        timeout=30_000
    )
    _record("malformed_json_rejected_honestly", True, bad_json.name)
    _shot(page, "e2e_10_malformed_json_rejected.png")

    # --- Empty CSV --------------------------------------------------------
    empty_csv = tmp_path / "empty_input.csv"
    empty_csv.write_bytes(b"")
    _ext_uploader_input(page).set_input_files(str(empty_csv))
    expect(page.get_by_text("The uploaded file is empty.").first).to_be_visible(
        timeout=30_000
    )
    assert "First rows" not in page.get_by_test_id("stMain").inner_text()
    _record("empty_csv_rejected_honestly", True, empty_csv.name)

    context.close()
    _finalize_manifest()


def test_e2e_manifest_records_every_check() -> None:
    """The persisted manifest must account for every check that ran."""
    manifest = _finalize_manifest()
    assert manifest["checks_total"] == len(CHECKS), manifest
    assert manifest["status"] == "PASS", manifest
