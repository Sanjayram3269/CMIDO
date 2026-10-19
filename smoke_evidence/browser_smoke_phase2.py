"""Phase 2B browser verification harness (Playwright/Chromium).

Drives the *live* Streamlit dashboard and records, per check, a
PASS / FAIL / BLOCKED / NOT TESTED outcome together with screenshots and a
machine-readable report.

What it verifies
----------------
1. Navigation — every destination in the live navigation registry is reached
   and its rendered page identity (``p.cmido-page-title``) matches the
   registry title.  The registry is read from the application's own
   navigation module (not hardcoded counts).
2. Provenance — the Provenance & Integrity workspace is opened through its
   real accessible navigation label and the corrected clauses are asserted
   against *that* page's rendered text (with an Overview-specific negative
   control so a wrong page can never satisfy the check).
3. External Data — both safe fixtures are uploaded, mapped, validated,
   executed, rendered and exported, and the displayed results are compared
   against the persisted on-disk run record, the input SHA-256 and the
   exported result table.

Evidence written under ``smoke_evidence/``:
  * ``browser_report_phase2.json``      machine-readable record
  * ``screenshots/*.png``               per-destination + step screenshots
  * ``provenance_workspace_text_full.txt``
  * ``external_data_concordance.json``  DOM-to-disk comparisons
  * stdout/stderr captured by the caller

Usage:  python smoke_evidence/browser_smoke_phase2.py [url]
"""

from __future__ import annotations

import datetime
import hashlib
import json
import pathlib
import platform
import re
import sys
import time

from playwright.sync_api import sync_playwright

# The live navigation labels contain emoji (and variation selectors); make sure
# stdout/stderr can write them instead of raising UnicodeEncodeError mid-run.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001 - reconfiguration is best effort
        pass

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8502/"
ROOT = pathlib.Path.cwd()
EV = ROOT / "smoke_evidence"
SC = EV / "screenshots"
SC.mkdir(parents=True, exist_ok=True)
REPORT = EV / "browser_report_phase2.json"
CONCORDANCE = EV / "external_data_concordance.json"
PROV_TEXT = EV / "provenance_workspace_text_full.txt"
RUN_ROOT = ROOT / "results" / "external_data_runs"

FIX_DESCRIPTIVE = EV / "safe_external_demo_deterministic_input.csv"
FIX_COVERAGE = EV / "safe_external_forecast_coverage_input.csv"

REC: dict = {
    "started_utc": datetime.datetime.now(datetime.UTC).isoformat(),
    "url": URL,
    "environment": {},
    "registry": {},
    "steps": [],
    "checks": [],
    "nav_results": [],
}
CONCORD: dict = {}


# ---------------------------------------------------------------------------
# Recording helpers
# ---------------------------------------------------------------------------

def log(step: str, status: str, detail: str) -> None:
    REC["steps"].append({"step": step, "status": status, "detail": detail})
    print(f"[{status}] {step}: {detail}", flush=True)


def check(name: str, status: str, detail: str = "") -> bool:
    """Record a named check with an explicit PASS/FAIL/BLOCKED/NOT TESTED."""
    assert status in {"PASS", "FAIL", "BLOCKED", "NOT TESTED"}
    REC["checks"].append({"check": name, "status": status, "detail": detail})
    print(f"[{status}] check::{name}: {detail}", flush=True)
    return status == "PASS"


def shot(page, name: str) -> None:
    try:
        page.mouse.move(1200, 40)
        page.wait_for_timeout(150)
        page.screenshot(path=str(SC / f"{name}.png"))
    except Exception as exc:  # noqa: BLE001 - screenshots are evidence, not gate
        log("screenshot", "BLOCKED", f"{name}: {exc}")


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def run_dirs() -> set[str]:
    if not RUN_ROOT.is_dir():
        return set()
    return {p.name for p in RUN_ROOT.iterdir() if p.is_dir()}


# ---------------------------------------------------------------------------
# UI primitives
# ---------------------------------------------------------------------------

def sidebar(page):
    return page.get_by_test_id("stSidebar")


def ext_input(page):
    region = page.get_by_role("region", name="Choose a CSV or JSON file").first
    region.wait_for(state="attached", timeout=30_000)
    return region.locator('input[type="file"]').first


def wait_title(page, title: str, timeout_s: float = 45.0) -> tuple[bool, str]:
    deadline = time.time() + timeout_s
    last = ""
    while time.time() < deadline:
        try:
            last = page.locator("p.cmido-page-title").first.inner_text(timeout=2_000).strip()
        except Exception:  # noqa: BLE001 - rerun tears the node down
            last = ""
        if last == title:
            return True, last
        page.wait_for_timeout(300)
    return False, last


def click_nav(page, title: str) -> tuple[bool, str]:
    try:
        btn = sidebar(page).get_by_role("button", name=title, exact=False).first
        btn.scroll_into_view_if_needed(timeout=10_000)
        btn.click(timeout=10_000)
        return True, ""
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def select_option(page, label_text: str, option: str) -> bool:
    """Choose an option in the Streamlit selectbox labelled *label_text*."""
    box = page.get_by_test_id("stSelectbox").filter(has_text=label_text).first
    field = box.locator('input[role="combobox"]').first
    last_error: Exception | None = None
    for _attempt in range(4):
        try:
            field.click(timeout=10_000)
            field.press("ArrowDown")
            opt = page.get_by_role("option", name=option, exact=True).first
            opt.wait_for(state="visible", timeout=5_000)
            opt.click(timeout=10_000)
            page.wait_for_timeout(600)
            return True
        except Exception as exc:  # noqa: BLE001 - rerun races the popup
            last_error = exc
            page.wait_for_timeout(1_200)
    log("select_option", "FAIL", f"{label_text!r} -> {option!r}: {last_error}")
    return False


def wait_text(page, text: str, timeout_s: float = 40.0) -> bool:
    try:
        page.get_by_text(text, exact=False).first.wait_for(state="visible", timeout=int(timeout_s * 1000))
        return True
    except Exception:  # noqa: BLE001
        return False


def wait_for_button(page, name: str, timeout_s: float = 30.0) -> bool:
    """Streamlit flushes a rerun in deltas, so a control can lag its heading."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            if page.get_by_role("button", name=name).count() > 0:
                return True
        except Exception:  # noqa: BLE001 - mid-rerun teardown
            pass
        page.wait_for_timeout(300)
    return False


def read_selectbox_options(page, label_text: str) -> list[str]:
    """Open a selectbox and read its rendered option labels."""
    box = page.get_by_test_id("stSelectbox").filter(has_text=label_text).first
    field = box.locator('input[role="combobox"]').first
    try:
        field.click(timeout=10_000)
        field.press("ArrowDown")
        page.wait_for_timeout(700)
        texts = page.get_by_role("option").all_inner_texts()
        field.press("Escape")
        page.wait_for_timeout(300)
        return [t.strip() for t in texts if t.strip()]
    except Exception as exc:  # noqa: BLE001
        try:
            field.press("Escape")
        except Exception:  # noqa: BLE001
            pass
        log("read_selectbox_options", "FAIL", f"{label_text!r}: {exc}")
        return []


def download_text(page, button_name: str, timeout_ms: int = 25_000) -> tuple[str | None, str]:
    try:
        with page.expect_download(timeout=timeout_ms) as info:
            page.get_by_role("button", name=button_name).first.click(timeout=15_000)
        dl = info.value
        path = dl.path()
        if path is None:
            return None, "download had no path"
        return pathlib.Path(path).read_text(encoding="utf-8"), ""
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def metric_value(page, label: str) -> str:
    node = page.get_by_test_id("stMetric").filter(has_text=label).first
    return node.inner_text()


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

def step_environment() -> None:
    import streamlit

    REC["environment"] = {
        "python": sys.version.split()[0],
        "streamlit": streamlit.__version__,
        "playwright": _playwright_version(),
        "platform": platform.platform(),
        "node_platform": platform.node(),
    }
    for cmd, key in (
        ("git branch --show-current", "git_branch"),
        ("git rev-parse --short HEAD", "git_head"),
    ):
        try:
            import subprocess

            out = subprocess.run(
                cmd.split(), capture_output=True, text=True, cwd=str(ROOT), check=False
            )
            REC["environment"][key] = (out.stdout or "").strip()
        except Exception as exc:  # noqa: BLE001
            REC["environment"][key] = f"unavailable: {exc}"
    log("environment", "PASS", json.dumps(REC["environment"]))


def _playwright_version() -> str:
    try:
        import playwright

        return getattr(playwright, "__version__", "unknown")
    except Exception:  # noqa: BLE001
        return "unknown"


def step_registry() -> list:
    sys.path.insert(0, str(ROOT))
    from src.construction.dashboard_ui import navigation as nav

    pages = nav.pages()
    rows = []
    for p in pages:
        rows.append(
            {
                "id": p.id,
                "title": p.title,
                "group": p.group,
                "available": bool(nav.page_is_available(p.id)),
                "planned": bool(nav.page_is_planned(p.id)),
            }
        )
    REC["registry"] = {
        "total": len(rows),
        "available": sum(1 for r in rows if r["available"]),
        "planned": sum(1 for r in rows if r["planned"]),
        "pages": rows,
    }
    log("registry", "PASS", json.dumps(REC["registry"], ensure_ascii=False))
    return pages


def step_nav_inventory(page) -> list[str]:
    labels = page.evaluate(
        """() => Array.from(
             document.querySelectorAll('[data-testid="stSidebar"] button')
           ).map(b => (b.innerText || '').trim()).filter(Boolean)"""
    )
    REC["nav_inventory"] = labels
    cleaned = []
    for raw in labels:
        s = raw.strip()
        # Strip every leading non-ASCII glyph (emoji, variation selectors) and
        # the space that follows so "\u26a0\ufe0f Scenario Lab" -> "Scenario Lab".
        while s and (not s[0].isascii() or s[0].isspace()):
            s = s[1:]
        cleaned.append(s)
    REC["nav_inventory_cleaned"] = cleaned
    log("nav_inventory", "PASS", json.dumps(cleaned, ensure_ascii=False))
    return cleaned


def visit_pages(page, registry_rows: list[dict]) -> None:
    for idx, row in enumerate(registry_rows, start=1):
        title = row["title"]
        clicked, cerr = click_nav(page, title)
        if not clicked:
            log("navigate", "FAIL", f"{title!r}: {cerr}")
            check(f"navigate::{row['id']}", "FAIL", cerr)
            REC["nav_results"].append({**row, "status": "FAIL", "detail": cerr})
            continue
        ok, seen = wait_title(page, title)
        main_text = ""
        try:
            main_text = page.get_by_test_id("stMain").inner_text(timeout=5_000)
        except Exception:  # noqa: BLE001
            main_text = ""
        planned_ok = True
        if row["planned"]:
            planned_ok = "planned workspace" in norm(main_text)
        status = "PASS" if (ok and planned_ok) else "FAIL"
        detail = f"rendered_title={seen!r} url={page.url}"
        if row["planned"]:
            detail += f" planned_panel={planned_ok}"
        log("navigate", status, f"{title!r} -> {detail}")
        check(f"navigate::{row['id']}", status, detail)
        REC["nav_results"].append({**row, "status": status, "rendered_title": seen, "detail": detail})
        shot(page, f"nav_{idx:02d}_{row['id']}")


def step_provenance(page) -> None:
    title = "Provenance & Integrity"
    clicked, cerr = click_nav(page, title)
    if not clicked:
        check("provenance_navigation", "FAIL", cerr)
        return
    ok, seen = wait_title(page, title)
    if not ok:
        check("provenance_navigation", "FAIL", f"rendered title={seen!r}")
        return
    check("provenance_navigation", "PASS", f"rendered title={seen!r}")

    # Let the rerun settle and the workspace render its clauses.
    wait_text(page, "Checks performed by this dashboard", 40)
    page.wait_for_timeout(1_500)

    main_text = page.get_by_test_id("stMain").inner_text()
    body_lower = norm(page.inner_text("body"))
    main_lower = norm(main_text)
    PROV_TEXT.write_text(main_text, encoding="utf-8")

    clauses = {
        "page_identity": seen == title,
        "section_performed_by_dashboard": "checks performed by this dashboard" in main_lower,
        "label_performed_at_load_time": "performed at load time" in main_lower,
        "label_not_performed_by_dashboard": "not performed by this dashboard" in main_lower,
        "no_sha256_recomputed": "no sha-256 digest is recomputed" in main_lower,
        "no_gate_redone": "no recorded gate, audit or reconciliation is redone" in main_lower,
        "reported_not_redone_label": "reported, not redone" in main_lower,
        "records_displayed_as_recorded": "as recorded, never re-derived" in main_lower,
        # Negative control: these Overview markers must NOT be present, which is
        # what made the previous run's capture wrong.
        "not_overview_page": "project duration" not in main_lower,
    }
    missing = [k for k, v in clauses.items() if not v]
    REC["provenance_clauses"] = clauses
    REC["provenance_text_chars"] = len(main_text)
    status = "PASS" if not missing else "FAIL"
    check("provenance_clauses", status, f"missing={missing}")
    shot(page, "provenance_workspace")

    # The body (not only main) must not carry the Overview title either.
    check(
        "provenance_body_title",
        "PASS" if "provenance & integrity" in body_lower else "FAIL",
        f"body contains provenance title: {'provenance & integrity' in body_lower}",
    )


def _open_external(page) -> str:
    clicked, cerr = click_nav(page, "External Data")
    if not clicked:
        return cerr
    ok, seen = wait_title(page, "External Data")
    return "" if ok else f"rendered title={seen!r}"


def step_external_landing(page) -> dict:
    err = _open_external(page)
    if err:
        check("external_landing", "FAIL", err)
        return {}
    wait_text(page, "No file selected", 30)
    main = page.get_by_test_id("stMain").inner_text()
    m = norm(main)
    probes = {
        "empty_state": "no file selected" in m,
        "accepted_caption": "accepted: csv, json" in m,
        "size_caption": "10 mib" in m,
        "supported_analyses_caption": "genuinely supported analysis" in m,
        "stages_not_run_section": "research stages not run on uploaded data" in m,
        "ro1_unavailable": "ro1 probabilistic model training — not available" in m,
        "ro2_unavailable": "ro2 joint uncertainty propagation — not available" in m,
        "ro3_unavailable": "ro3 multi-objective procurement optimization — not available" in m,
        "no_run_button": page.get_by_role("button", name="Run analysis").count() == 0,
    }
    missing = [k for k, v in probes.items() if not v]
    REC["external_landing"] = probes
    check("external_landing", "PASS" if not missing else "FAIL", f"missing={missing}")
    shot(page, "external_landing")
    return probes


def _compare_downloads(
    prefix: str,
    summary_txt: str | None,
    summary_err: str,
    table_txt: str | None,
    table_err: str,
    disk_record: dict,
    disk_csv: str,
) -> dict:
    """Compare the *downloaded* exports with the persisted run artifacts.

    The downloaded run summary is rendered from the in-memory record, which
    also carries the ``outputs["run_record"]`` entry written after the file
    was serialised, so the disk record is compared as a field-for-field
    subset rather than by identity.
    """
    out: dict = {
        "run_summary_error": summary_err,
        "result_table_error": table_err,
        "run_summary_download_matches_disk": None,
        "run_summary_field_mismatches": [],
        "run_summary_extra_keys": [],
        "result_table_download_matches_disk_csv": None,
    }
    if summary_txt:
        try:
            dl = json.loads(summary_txt)
        except json.JSONDecodeError:
            dl = None
        if dl is None:
            out["run_summary_download_matches_disk"] = False
            out["run_summary_field_mismatches"] = ["download was not valid JSON"]
        else:
            for key, disk_value in disk_record.items():
                dl_value = dl.get(key)
                if key == "outputs" and isinstance(disk_value, dict) and isinstance(dl_value, dict):
                    # The in-memory record also carries the "run_record" entry
                    # written after the file was serialised, so compare the
                    # persisted entries as a subset.
                    mismatched = [
                        k for k, v in disk_value.items() if dl_value.get(k) != v
                    ]
                    if mismatched:
                        out["run_summary_field_mismatches"].append(f"outputs.{mismatched}")
                elif dl_value != disk_value:
                    out["run_summary_field_mismatches"].append(key)
            out["run_summary_extra_keys"] = sorted(set(dl) - set(disk_record))
            out["run_summary_download_matches_disk"] = not out[
                "run_summary_field_mismatches"
            ]
    if table_txt:
        out["result_table_download_matches_disk_csv"] = table_txt == disk_csv
        out["download_result_table_head"] = table_txt[:400]

    status = (
        "PASS"
        if out["run_summary_download_matches_disk"] is True
        else (
            "BLOCKED"
            if out["run_summary_download_matches_disk"] is None
            else "FAIL"
        )
    )
    check(f"{prefix}_run_summary_export_matches_disk", status,
          f"mismatches={out['run_summary_field_mismatches']} extra={out['run_summary_extra_keys']}")

    status = (
        "PASS"
        if out["result_table_download_matches_disk_csv"] is True
        else (
            "BLOCKED"
            if out["result_table_download_matches_disk_csv"] is None
            else "FAIL"
        )
    )
    check(f"{prefix}_result_table_export_matches_disk", status, table_err or "byte-identical")
    return out


def _run_descriptive(page) -> dict:
    """Upload the demo fixture and run descriptive_statistics end to end."""
    out: dict = {"analysis": "descriptive_statistics", "fixture": FIX_DESCRIPTIVE.name}
    if not FIX_DESCRIPTIVE.exists():
        check("run_descriptive_statistics", "BLOCKED", f"missing fixture {FIX_DESCRIPTIVE}")
        return out

    before = run_dirs()
    ext_input(page).set_input_files(str(FIX_DESCRIPTIVE))
    if not wait_text(page, "First rows", 40):
        check("descriptive_upload", "FAIL", "preview never rendered")
        return out
    check("descriptive_upload", "PASS", FIX_DESCRIPTIVE.name)
    shot(page, "external_descriptive_uploaded")

    # The supported analyses must be offered by the live Analysis control and
    # the unavailable research stages must NOT be offered.
    options = read_selectbox_options(page, "Analysis")
    REC["supported_analysis_options"] = options
    expected = {
        "Descriptive statistics + bootstrap interval",
        "Forecast interval coverage",
    }
    missing = sorted(expected - set(options))
    check(
        "supported_analyses_listed",
        "PASS" if not missing else "FAIL",
        f"options={options} missing={missing}",
    )
    offered_unavailable = [
        o
        for o in options
        if o.startswith(("RO1 probabilistic", "RO2 joint", "RO3 multi"))
    ]
    check(
        "unavailable_analyses_not_offered",
        "PASS" if not offered_unavailable else "FAIL",
        f"offered={offered_unavailable}",
    )

    if not select_option(page, "Analysis", "Descriptive statistics + bootstrap interval"):
        check("descriptive_analysis_selected", "FAIL", "selectbox")
        return out
    if not select_option(page, "Measure column (numeric)", "forecast_demand_units"):
        check("descriptive_mapping", "FAIL", "measure selectbox")
        return out

    if not wait_text(page, "Mapping is valid. The analysis can run.", 30):
        check("descriptive_validation", "FAIL", "validation success never rendered")
        return out
    check("descriptive_validation", "PASS", "measure=forecast_demand_units")
    shot(page, "external_descriptive_mapping")

    run_btn = page.get_by_role("button", name="Run analysis").first
    try:
        run_btn.click(timeout=15_000)
    except Exception as exc:  # noqa: BLE001
        check("descriptive_run", "FAIL", str(exc))
        return out
    if not wait_text(page, "5. Results (computed from your uploaded data)", 40):
        check("descriptive_run", "FAIL", "results section never rendered")
        return out
    check("descriptive_run", "PASS", "results section rendered")
    check("descriptive_lineage", "PASS" if wait_text(page, "Run lineage", 20) else "FAIL",
          "Run lineage heading")
    shot(page, "external_descriptive_results")

    exports = {}
    for label in ("Schema mapping (JSON)", "Run summary (JSON)", "Result table (CSV)"):
        exports[label] = wait_for_button(page, label, 30)
    check(
        "descriptive_exports",
        "PASS" if all(exports.values()) else "FAIL",
        json.dumps(exports),
    )

    summary_txt, s_err = download_text(page, "Run summary (JSON)")
    table_txt, t_err = download_text(page, "Result table (CSV)")
    out["download_run_summary_error"] = s_err
    out["download_result_table_error"] = t_err

    new = sorted(run_dirs() - before)
    if not new:
        check("descriptive_run_persisted", "FAIL", "no new run directory")
        return out
    run_dir = RUN_ROOT / new[-1]
    record = json.loads((run_dir / "run_record.json").read_text(encoding="utf-8"))
    result = json.loads((run_dir / "analysis_result.json").read_text(encoding="utf-8"))
    disk_csv = (run_dir / "analysis_result.csv").read_text(encoding="utf-8")
    digest = hashlib.sha256(FIX_DESCRIPTIVE.read_bytes()).hexdigest()

    conc = {
        "run_dir": run_dir.name,
        "input_sha256_computed": digest,
        "input_sha256_record": record.get("input_sha256"),
        "input_hash_matches": digest == record.get("input_sha256"),
        "input_filename_matches": record.get("input_filename") == FIX_DESCRIPTIVE.name,
        "analysis_matches": result.get("analysis") == "descriptive_statistics",
        "status": record.get("status"),
        "provenance_class": record.get("provenance_class"),
        "mapping": record.get("mapping"),
        "disk_row_count": len(result.get("rows") or []),
        "run_summary_download_matches_disk": None,
        "result_table_download_matches_disk_csv": None,
    }
    if summary_txt or table_txt:
        conc.update(
            _compare_downloads(
                "descriptive", summary_txt, s_err, table_txt, t_err, record, disk_csv
            )
        )
    CONCORD["descriptive_statistics"] = conc

    ok = all(
        [
            conc["input_hash_matches"],
            conc["input_filename_matches"],
            conc["analysis_matches"],
            conc["status"] == "SUCCEEDED",
            conc["provenance_class"] == "DER",
            (conc["run_summary_download_matches_disk"] is not False),
            (conc["result_table_download_matches_disk_csv"] is not False),
            conc["disk_row_count"] > 0,
        ]
    )
    check(
        "descriptive_dom_to_disk",
        "PASS" if ok else "FAIL",
        json.dumps(conc, ensure_ascii=False)[:600],
    )
    out.update(conc)
    return out


def _set_forecast_mapping(page) -> bool:
    if not select_option(page, "Analysis", "Forecast interval coverage"):
        return False
    if not select_option(page, "Observed column (numeric)", "observed_units"):
        return False
    if not select_option(page, "Interval lower bound column (numeric)", "lower_p10"):
        return False
    if not select_option(page, "Interval upper bound column (numeric)", "upper_p90"):
        return False
    return True


def _run_coverage(page) -> dict:
    """Upload the forecast-coverage fixture and run forecast_coverage end to end."""
    out: dict = {"analysis": "forecast_coverage", "fixture": FIX_COVERAGE.name}
    if not FIX_COVERAGE.exists():
        check("run_forecast_coverage", "BLOCKED", f"missing fixture {FIX_COVERAGE}")
        return out

    before = run_dirs()
    ext_input(page).set_input_files(str(FIX_COVERAGE))
    if not wait_text(page, "First rows", 40):
        check("coverage_upload", "FAIL", "preview never rendered")
        return out
    check("coverage_upload", "PASS", FIX_COVERAGE.name)

    # --- honest rejection of a malformed (incomplete) mapping -------------
    if not select_option(page, "Analysis", "Forecast interval coverage"):
        check("coverage_analysis_selected", "FAIL", "selectbox")
        return out
    select_option(page, "Observed column (numeric)", "observed_units")
    select_option(page, "Interval lower bound column (numeric)", "lower_p10")
    # Leave the required upper-bound field at its empty default on purpose.
    bad_ok = wait_text(page, "Mapping has blocking problems. Fix them before running.", 30)
    run_btn = page.get_by_role("button", name="Run analysis")
    run_enabled = run_btn.count() > 0 and run_btn.first.is_enabled()
    check(
        "malformed_mapping_rejected",
        "PASS" if (bad_ok and not run_enabled) else "FAIL",
        f"error_shown={bad_ok} run_enabled={run_enabled}",
    )
    shot(page, "external_malformed_mapping_rejected")

    # --- complete the mapping --------------------------------------------
    if not _set_forecast_mapping(page):
        check("coverage_mapping", "FAIL", "mapping selectbox")
        return out
    if not wait_text(page, "Mapping is valid. The analysis can run.", 30):
        check("coverage_validation", "FAIL", "validation success never rendered")
        return out
    check("coverage_validation", "PASS", "observed=observed_units lower=lower_p10 upper=upper_p90")
    shot(page, "external_coverage_mapping")

    run_btn = page.get_by_role("button", name="Run analysis").first
    try:
        run_btn.click(timeout=15_000)
    except Exception as exc:  # noqa: BLE001
        check("coverage_run", "FAIL", str(exc))
        return out
    if not wait_text(page, "5. Results (computed from your uploaded data)", 40):
        check("coverage_run", "FAIL", "results section never rendered")
        return out
    check("coverage_run", "PASS", "results section rendered")
    shot(page, "external_coverage_results")

    dom: dict = {}
    try:
        for label in ("Rows scored", "Coverage rate", "Mean interval width"):
            dom[label] = metric_value(page, label)
    except Exception as exc:  # noqa: BLE001
        check("coverage_metrics_render", "FAIL", str(exc))
        return out
    check("coverage_metrics_render", "PASS", json.dumps(dom, ensure_ascii=False))

    check("coverage_lineage", "PASS" if wait_text(page, "Run lineage", 20) else "FAIL",
          "Run lineage heading")
    exports = {
        label: wait_for_button(page, label, 30)
        for label in ("Schema mapping (JSON)", "Run summary (JSON)", "Result table (CSV)")
    }
    check("coverage_exports", "PASS" if all(exports.values()) else "FAIL", json.dumps(exports))

    summary_txt, s_err = download_text(page, "Run summary (JSON)")
    table_txt, t_err = download_text(page, "Result table (CSV)")
    out["download_run_summary_error"] = s_err
    out["download_result_table_error"] = t_err

    new = sorted(run_dirs() - before)
    if not new:
        check("coverage_run_persisted", "FAIL", "no new run directory")
        return out
    run_dir = RUN_ROOT / new[-1]
    record = json.loads((run_dir / "run_record.json").read_text(encoding="utf-8"))
    result = json.loads((run_dir / "analysis_result.json").read_text(encoding="utf-8"))
    disk_csv = (run_dir / "analysis_result.csv").read_text(encoding="utf-8")
    digest = hashlib.sha256(FIX_COVERAGE.read_bytes()).hexdigest()

    def num(text: str) -> float:
        m = re.search(r"-?\d+(?:\.\d+)?", (text or "").replace(",", ""))
        return float(m.group(0)) if m else float("nan")

    dom_rows = num(dom.get("Rows scored", ""))
    dom_cov = num(dom.get("Coverage rate", ""))
    dom_width = num(dom.get("Mean interval width", ""))
    disk_cov = float(result.get("coverage_rate"))
    disk_width = float(result.get("mean_interval_width"))
    disk_rows = float(result.get("n_scored"))

    conc = {
        "run_dir": run_dir.name,
        "dom_metrics": dom,
        "disk_analysis_result": {
            "n_scored": result.get("n_scored"),
            "coverage_rate": disk_cov,
            "mean_interval_width": disk_width,
            "pinball_loss_mean": result.get("pinball_loss_mean"),
        },
        "rows_scored_matches": dom_rows == disk_rows,
        "coverage_rate_matches_rounded": abs(dom_cov - disk_cov) <= 5e-4,
        "mean_interval_width_matches_rounded": abs(dom_width - disk_width) <= 5e-4,
        "input_sha256_computed": digest,
        "input_sha256_record": record.get("input_sha256"),
        "input_hash_matches": digest == record.get("input_sha256"),
        "input_filename_matches": record.get("input_filename") == FIX_COVERAGE.name,
        "analysis_matches": result.get("analysis") == "forecast_coverage",
        "status": record.get("status"),
        "provenance_class": record.get("provenance_class"),
        "mapping": record.get("mapping"),
        "run_summary_download_matches_disk": None,
        "result_table_download_matches_disk_csv": None,
    }
    if summary_txt or table_txt:
        conc.update(
            _compare_downloads(
                "coverage", summary_txt, s_err, table_txt, t_err, record, disk_csv
            )
        )
    CONCORD["forecast_coverage"] = conc

    ok = all(
        [
            conc["rows_scored_matches"],
            conc["coverage_rate_matches_rounded"],
            conc["mean_interval_width_matches_rounded"],
            conc["input_hash_matches"],
            conc["input_filename_matches"],
            conc["analysis_matches"],
            conc["status"] == "SUCCEEDED",
            conc["provenance_class"] == "DER",
            (conc["run_summary_download_matches_disk"] is not False),
            (conc["result_table_download_matches_disk_csv"] is not False),
        ]
    )
    check(
        "coverage_dom_to_disk",
        "PASS" if ok else "FAIL",
        json.dumps(conc, ensure_ascii=False)[:600],
    )
    out.update(conc)
    return out


def step_unavailable_stages(page) -> None:
    main = norm(page.get_by_test_id("stMain").inner_text())
    probes = {
        "section_present": "research stages not run on uploaded data" in main,
        "ro1": "ro1 probabilistic model training — not available" in main,
        "ro2": "ro2 joint uncertainty propagation — not available" in main,
        "ro3": "ro3 multi-objective procurement optimization — not available" in main,
        "no_simulation_claim": "never simulated" in main,
    }
    missing = [k for k, v in probes.items() if not v]
    check("unavailable_stages", "PASS" if not missing else "FAIL", f"missing={missing}")
    shot(page, "external_unavailable_stages")


def step_unsupported_file(page) -> None:
    bad = EV / "_probe_tmp" / "not_a_supported_table.txt"
    if not bad.exists():
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_text("month_index,observed_units\n1,120\n", encoding="utf-8")
    ext_input(page).set_input_files(str(bad))
    page.wait_for_timeout(4_000)
    main = page.get_by_test_id("stMain").inner_text()
    m = norm(main)
    rejected = "are not allowed" in m or "unsupported file type" in m
    check(
        "unsupported_file_rejected",
        "PASS" if rejected else "FAIL",
        f"rejected={rejected}",
    )
    shot(page, "external_unsupported_file_rejected")


def _run() -> None:
    step_environment()
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, args=["--disable-dev-shm-usage"])
        console_errors: list[str] = []
        try:
            ctx = browser.new_context(
                viewport={"width": 1600, "height": 1000}, accept_downloads=True
            )
            page = ctx.new_page()
            page.set_default_timeout(30_000)
            page.on(
                "console",
                lambda m: console_errors.append(m.text) if m.type == "error" else None,
            )

            try:
                page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
                page.get_by_test_id("stSidebar").wait_for(state="visible", timeout=60_000)
                page.wait_for_timeout(3_000)
                log("launch", "PASS", f"title={page.title()!r} url={page.url!r}")
                shot(page, "00_landing")
            except Exception as exc:  # noqa: BLE001
                check("launch", "FAIL", str(exc))
                raise

            inventory = step_nav_inventory(page)
            step_registry()
            rows = REC["registry"]["pages"]

            # Every registry title must exist as a live navigation target.
            titles = {r["title"] for r in rows}
            seen_labels: list[str] = []
            for lab in inventory:
                if lab and lab not in seen_labels:
                    seen_labels.append(lab)
            missing_nav = [r["title"] for r in rows if r["title"] not in seen_labels]
            extra_nav = [
                lab
                for lab in seen_labels
                if lab not in titles
                and lab.split("\n")[0].strip().lower() not in {"deploy", "upload"}
            ]
            REC["nav_labels_unique"] = seen_labels
            check(
                "nav_targets_match_registry",
                "PASS" if not missing_nav else "FAIL",
                f"missing={missing_nav} extra={extra_nav}",
            )

            visit_pages(page, rows)

            reached = [r for r in REC["nav_results"] if r["status"] == "PASS"]
            unreached = [r for r in REC["nav_results"] if r["status"] != "PASS"]
            check(
                "navigation_coverage",
                "PASS" if len(reached) == len(rows) else "FAIL",
                f"reached {len(reached)}/{len(rows)}; unreached={[r['id'] for r in unreached]}",
            )

            step_provenance(page)

            step_external_landing(page)
            REC["external_descriptive"] = _run_descriptive(page)
            REC["external_coverage"] = _run_coverage(page)
            step_unavailable_stages(page)
            step_unsupported_file(page)

            fatal = [e for e in console_errors if "Uncaught" in e or "ChunkLoadError" in e]
            REC["console_errors"] = console_errors[-40:]
            check(
                "no_fatal_console_errors",
                "PASS" if not fatal else "FAIL",
                "; ".join(fatal[:3]),
            )

            ctx.close()
        finally:
            browser.close()

    REC["finished_utc"] = datetime.datetime.now(datetime.UTC).isoformat()


def main() -> int:
    try:
        _run()
    except Exception as exc:  # noqa: BLE001 - the report must always be written
        REC["fatal_error"] = f"{type(exc).__name__}: {exc}"
        check("harness_completed", "FAIL", REC["fatal_error"])
    else:
        check("harness_completed", "PASS", "all steps executed")

    counts: dict[str, int] = {}
    for c in REC["checks"]:
        counts[c["status"]] = counts.get(c["status"], 0) + 1
    REC["summary"] = counts
    REPORT.write_text(json.dumps(REC, indent=1, ensure_ascii=False), encoding="utf-8")
    CONCORDANCE.write_text(json.dumps(CONCORD, indent=1), encoding="utf-8")
    print("\nSUMMARY:", json.dumps(counts))
    print("WROTE", REPORT)
    return 0 if counts.get("FAIL", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
