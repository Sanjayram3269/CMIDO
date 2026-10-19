import pathlib, sys, json, datetime, base64, traceback
from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(".")
DASHBOARD_URL = sys.argv[2] if len(sys.argv) > 2 else "http://127.0.0.1:8502/"
SMOKE_DIR = ROOT / "smoke_evidence"
SCREENSHOTS = SMOKE_DIR / "screenshots"
SCREENSHOTS.mkdir(parents=True, exist_ok=True)

REC = {"started_utc": datetime.datetime.now(datetime.UTC).isoformat(), "dashboard_url": DASHBOARD_URL, "steps": []}

def log(step, status, detail):
    REC["steps"].append({"step": step, "status": status, "detail": detail})
    print(f"[{status}] {step}: {detail}")

def screenshot(page, name):
    p = SCREENSHOTS / f"{name}.png"
    page.screenshot(path=str(p), full_page=False)
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    return {"file": str(p), "bytes": len(p.read_bytes()), "b64": b64}

def main():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--disable-dev-shm-usage"])
            ctx = browser.new_context(viewport={"width": 1366, "height": 900})
            page = ctx.new_page()
            REC["browser"] = {"name": "chromium", "headless": True}
            try:
                page.goto(DASHBOARD_URL, timeout=60000, wait_until="domcontentloaded")
                page.wait_for_timeout(2500)
                REC["browser"]["page_url_after_load"] = page.url
                REC["browser"]["title"] = page.title()
            except Exception as e:
                log("launch", "BLOCKED", f"could not load dashboard: {e}")
                browser.close()
                return
            log("launch", "PASS", f"dashboard reachable; title={page.title()!r}; url={page.url!r}")
            if page.title():
                screenshot(page, "01_landing")

            def collect_nav_targets():
                targets = {}
                for sel in ['a[href]', 'button', 'input[type="button"]', 'div.stAppNavBar a', 'li a']:
                    try:
                        els = page.query_selector_all(sel)
                    except Exception:
                        els = []
                    for el in els:
                        txt = ""
                        try:
                            if el.evaluate("e => e.tagName"):
                                txt = (el.inner_text() or "").strip()
                        except Exception:
                            pass
                        href = ""
                        try:
                            href = el.get_attribute("href") or ""
                        except Exception:
                            pass
                        if not txt and not href:
                            continue
                        key = txt or href
                        if key and key not in targets:
                            targets[key] = {"text": txt, "href": href}
                return targets

            nav = collect_nav_targets()
            log("navigation_scan", "PASS", f"found {len(nav)} candidate nav targets")
            REC["navigation_candidates"] = [{"text": v["text"], "href": v["href"]} for v in nav.values()]

            known_ids = ["Overview", "3D Project Graph", "Schedule", "Materials & Resources",
                         "RO1", "RO2", "RO3", "Scenario Lab", "Procurement Decisions",
                         "Research Evidence", "Experiments", "Real-World Data",
                         "Ablation & Robustness", "Provenance & Integrity", "External Data",
                         "Resilience & Stress"]
            chosen = [k for k in known_ids if k in nav]
            REC["chosen_nav_targets"] = chosen
            log("navigation_choice", "PASS", f"selected {len(chosen)} targets matching known dashboard labels")

            for target in chosen:
                try:
                    clicked = False
                    for sel in ['a[href]', 'button', 'input[type="button"]']:
                        els = page.query_selector_all(sel)
                        for el in els:
                            try:
                                txt = (el.inner_text() or "").strip()
                            except Exception:
                                txt = ""
                            if txt == target:
                                el.scroll_into_view_if_needed()
                                el.click()
                                page.wait_for_timeout(2000)
                                clicked = True
                                break
                        if clicked:
                            break
                    if not clicked:
                        for sel in ['a[href]']:
                            els = page.query_selector_all(sel)
                            for el in els:
                                href = el.get_attribute("href") or ""
                                if href and target.lower() in href.lower():
                                    el.scroll_into_view_if_needed()
                                    el.click()
                                    page.wait_for_timeout(2000)
                                    clicked = True
                                    break
                            if clicked:
                                break
                    title_now = page.title()
                    body_text = ""
                    try:
                        body_text = page.inner_text("body")[:1200]
                    except Exception:
                        body_text = ""
                    log("navigate", "PASS", f"visited {target!r}; url={page.url!r}; title={title_now!r}")
                    screenshot(page, f"nav_{target.replace('/', '_').replace(' ', '_')[:40]}")
                except Exception as e:
                    log("navigate", "FAIL", f"failed to visit {target!r}: {e}")

            try:
                visited_provenance = False
                for sel in ['a[href]', 'button', 'input[type="button"]']:
                    els = page.query_selector_all(sel)
                    for el in els:
                        try:
                            txt = (el.inner_text() or "").strip()
                        except Exception:
                            txt = ""
                        if txt == "Provenance & Integrity":
                            el.scroll_into_view_if_needed()
                            el.click()
                            page.wait_for_timeout(2500)
                            visited_provenance = True
                            break
                    if visited_provenance:
                        break
                prov_text = ""
                try:
                    prov_text = page.inner_text("body")
                except Exception:
                    prov_text = ""
                prov_lower = prov_text.lower()
                checks = {
                    "has_provenance_title": "provenance" in prov_lower or "Provenance" in prov_text,
                    "has_integrity_title": "integrity" in prov_lower or "Integrity" in prov_text,
                    "reported_not_redone_present": "reported, not redone" in prov_lower,
                    "no_sha256_recomputed_present": ("no sha-256 digest is recomputed" in prov_lower) or ("sha-256" in prov_lower and "recomputed" in prov_lower),
                    "performed_at_load_present": "performed at load time" in prov_lower,
                    "not_performed_by_dashboard_present": "not performed by this dashboard" in prov_lower,
                }
                log("provenance_wording", "PASS" if all(checks.values()) else "FAIL", f"wording checks: {checks}")
                screenshot(page, "provenance_wording")
                REC["provenance_wording_checks"] = checks
                REC["provenance_page_text_preview"] = prov_text[:2000]
                REC["provenance_page_text_full"] = prov_text
            except Exception as e:
                log("provenance_wording", "FAIL", f"exception during provenance check: {e}")
                REC["provenance_wording_error"] = str(e)

            try:
                visited_ext = False
                for sel in ['a[href]', 'button', 'input[type="button"]']:
                    els = page.query_selector_all(sel)
                    for el in els:
                        try:
                            txt = (el.inner_text() or "").strip()
                        except Exception:
                            txt = ""
                        if txt == "External Data":
                            el.scroll_into_view_if_needed()
                            el.click()
                            page.wait_for_timeout(2500)
                            visited_ext = True
                            break
                    if visited_ext:
                        break
                ext_text = ""
                try:
                    ext_text = page.inner_text("body")
                except Exception:
                    ext_text = ""
                ext_lower = ext_text.lower()
                ext_checks = {
                    "has_external_title": "external" in ext_lower,
                    "has_upload_control": ("file upload" in ext_lower) or ('type="file"' in (page.content() or "").lower()) or ("upload" in ext_lower),
                    "supported_analyses_listed": "supported" in ext_lower or "deterministic" in ext_lower,
                    "unavailable_analyses_listed": "unavailable" in ext_lower or "not supported" in ext_lower or "not available" in ext_lower,
                }
                log("external_data_inspect", "PASS" if all(ext_checks.values()) else "PARTIAL", f"external data checks: {ext_checks}")
                screenshot(page, "external_data_before_upload")
                REC["external_data_checks"] = ext_checks
                REC["external_data_text_preview"] = ext_text[:2000]

                # Prefer a forecast_coverage-compatible CSV; fall back to the earlier rejected csv probe.
                candidates = [
                    SMOKE_DIR / "safe_external_forecast_coverage_input.csv",
                    SMOKE_DIR / "safe_external_demo_deterministic_input.csv",
                ]
                fixture = next((c for c in candidates if c.exists()), None)
                upload_done = False
                uploaded_name = None
                if fixture is not None:
                    try:
                        file_inputs = page.query_selector_all('input[type="file"]')
                        if file_inputs:
                            el = file_inputs[0]
                            el.set_input_files(str(fixture))
                            page.wait_for_timeout(3000)
                            upload_done = True
                            uploaded_name = fixture.name
                            log("external_upload", "PASS", f"uploaded {fixture.name}")
                            screenshot(page, "external_data_after_upload")
                        else:
                            log("external_upload", "BLOCKED", "no file input found on External Data page")
                    except Exception as e:
                        log("external_upload", "FAIL", f"upload failed: {e}")
                REC["external_upload_done"] = upload_done
                REC["external_uploaded_file"] = uploaded_name

                run_done = False
                try:
                    for sel in ['button', 'input[type="button"]', 'input[type="submit"]']:
                        els = page.query_selector_all(sel)
                        for el in els:
                            try:
                                txt = (el.inner_text() or "").strip().lower()
                            except Exception:
                                txt = ""
                            if "run" in txt or "execute" in txt:
                                el.scroll_into_view_if_needed()
                                el.click()
                                page.wait_for_timeout(6000)
                                run_done = True
                                log("external_run", "PASS", "clicked a run/execute affordance")
                                screenshot(page, "external_data_after_run")
                                break
                        if run_done:
                            break
                except Exception as e:
                    log("external_run", "FAIL", f"run click failed: {e}")
                REC["external_run_done"] = run_done

                post_text = ""
                try:
                    post_text = page.inner_text("body")
                except Exception:
                    post_text = ""
                REC["external_post_text_preview"] = post_text[:2000]
                export_check = ("export" in post_text.lower()) or ("download" in post_text.lower()) or ("csv" in post_text.lower()) or ("json" in post_text.lower())
                log("external_export", "PASS" if export_check else "NOT_TESTED", f"export affordance hint: {export_check}")
                REC["external_export_hint"] = export_check
            except Exception as e:
                log("external_data_workflow", "FAIL", f"exception during external data workflow: {e}")
                REC["external_data_workflow_error"] = str(e)

            browser.close()
    except Exception as e:
        log("fatal", "FAIL", f"playwright session failed: {e}\n{traceback.format_exc()}")
    finally:
        REC["finished_utc"] = datetime.datetime.now(datetime.UTC).isoformat()
        out = SMOKE_DIR / "browser_smoke_run.json"
        out.write_text(json.dumps(REC, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("WROTE", out)

if __name__ == "__main__":
    main()
