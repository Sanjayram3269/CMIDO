import asyncio, pathlib, sys, json, datetime
from playwright.async_api import async_playwright

URL = "http://127.0.0.1:8502/"
EV = pathlib.Path("smoke_evidence")
SC = EV / "screenshots"
SC.mkdir(parents=True, exist_ok=True)
LOG = EV / "browser_report.json"

# The live DOM in this Streamlit build emits nav labels with a leading emoji icon
# followed by a space, e.g. "📄 Overview". We match on the cleaned label.
NAV_WANTED = [
    "Overview",
    "3D Project Graph",
    "Schedule & Critical Path",
    "Materials & Resources",
    "RO1 · Forecasting",
    "RO2 · Uncertainty",
    "RO3 · Optimization",
    "Scenario Lab",
    "Procurement Decisions",
    "Research Evidence",
    "Experiments",
    "Real-World Data",
    "Ablation & Robustness",
    "Provenance & Integrity",
    "External Data",
]

NAV_SELECTORS = [
    'a[data-testid="nav-topmost"] a',
    'a[data-testid="nav-main-leaf"] a',
    'a[data-testid="nav-main"] a[data-testid]',
    'a[data-testid] a[data-testid]',
    'a.stAppNavBar_link',
    '.stAppNavBar a',
    'a[href]',
    'button',
]

def _clean(label: str) -> str:
    """Normalize a nav label the way the live DOM emits it: strip the leading
    emoji icon (non-ASCII printable) plus any immediately following spaces."""
    s = (label or "").strip()
    if not s:
        return s
    if ord(s[0]) > 0x20 and not s[0].isascii() and s[0].isprintable():
        idx = 1
        while idx < len(s) and s[idx] == " ":
            idx += 1
        return s[idx:]
    return s

def _safe(text: str) -> str:
    return ascii(text)

def _log(rec, step, status, detail):
    rec["steps"].append({"step": step, "status": status, "detail": detail})
    print(f"[{status}] {_safe(step)}: {_safe(detail)}")

def _erred(b):
    # best-effort browser shutdown
    try:
        b.close()
    except Exception:
        pass

async def main():
    rec = {
        "started_utc": datetime.datetime.now(datetime.UTC).isoformat(),
        "url": URL,
        "steps": [],
    }

    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True, args=["--disable-dev-shm-usage"])
        try:
            ctx = await b.new_context(viewport={"width": 1366, "height": 900})
            page = await ctx.new_page()

            try:
                await page.goto(URL, timeout=60000, wait_until="domcontentloaded")
                await page.wait_for_timeout(2500)
                t = await page.title()
                _log(rec, "launch", "PASS", f"title={t!r} url={page.url!r}")
                await page.screenshot(path=str(SC / "00_landing.png"))
            except Exception as e:
                _log(rec, "launch", "BLOCKED", str(e))
                return _erred(b), rec

            nav_raw = await page.evaluate("""() => {
              const out = new Map();
              const seen = new Set();
              const walkers = [
                () => Array.from(document.querySelectorAll('a[data-testid="nav-topmost"] a')),
                () => Array.from(document.querySelectorAll('a[data-testid="nav-main-leaf"] a')),
                () => Array.from(document.querySelectorAll('a[data-testid="nav-main"] a[data-testid]')),
                () => Array.from(document.querySelectorAll('a[data-testid] a[data-testid]')),
                () => Array.from(document.querySelectorAll('a.stAppNavBar_link')),
                () => Array.from(document.querySelectorAll('.stAppNavBar a')),
                () => Array.from(document.querySelectorAll('a[href]')),
                () => Array.from(document.querySelectorAll('button')),
              ];
              for (const walk of walkers) {
                for (const el of walk()) {
                  const tag = (el.tagName || '').toLowerCase();
                  let label = '';
                  try { label = (el.innerText || '').trim(); } catch (e) {}
                  let href = '';
                  try { href = el.getAttribute('href') || ''; } catch (e) {}
                  if (!label && !href) continue;
                  const key = label || href;
                  if (!key || seen.has(key)) continue;
                  seen.add(key);
                  out.set(key, { tag, label, href });
                }
              }
              return Array.from(out.entries()).map(([k, v]) => ({ key: k, ...v }));
            }""")
            (EV / "nav_candidates.json").write_text(json.dumps(nav_raw, indent=1), encoding="utf-8")
            _log(rec, "navigation_scan", "PASS", f"found {len(nav_raw)} candidates")
            print("CANDIDATES:")
            for n in nav_raw:
                print("  ", n.get("tag"), "|", _safe(n.get("label"))[:90], "|", _safe(n.get("href"))[:90])

            navset_exact: set[str] = set()
            _nav_by_raw: dict[str, dict] = {}
            for n in nav_raw:
                nl = n.get("label") or ""
                if not nl.strip():
                    continue
                raw = nl.strip()
                navset_exact.add(raw)
                _nav_by_raw[raw] = n

            clean_map = {k: _clean(k) for k in navset_exact}
            navset_clean = set(clean_map.values())
            matching = {k for k, c in clean_map.items() if c in NAV_WANTED}
            chosen = [k for k in matching]
            chosen_clean = {clean_map[k] for k in chosen}

            _log(
                rec,
                "navigation_choice",
                "PASS" if chosen else "FAIL",
                f"selected {len(chosen)}/{len(NAV_WANTED)} from {len(navset_exact)} candidates; clean_keys={sorted(navset_clean)}",
            )
            print("CHOSEN:", sorted(chosen_clean))
            if not chosen:
                _log(
                    rec,
                    "navigation_choice_debug",
                    "INFO",
                    f"raw_keys={sorted(navset_exact)}; clean_keys={sorted(navset_clean)}",
                )

            _nav_by_clean = {clean_map[k]: v for k, v in _nav_by_raw.items()}
            navset = navset_clean
            print("DEBUG navset:", [ascii(x) for x in sorted(navset)])

            nav_ok = []
            nav_fail = []
            for target in chosen_clean:
                clicked = False
                for sel in NAV_SELECTORS:
                    els = await page.query_selector_all(sel)
                    for el in els:
                        try:
                            raw_txt = (await el.inner_text()).strip()
                            txt = _clean(raw_txt)
                        except Exception:
                            txt = ""
                        if txt == target:
                            await el.scroll_into_view_if_needed()
                            await el.click()
                            await page.wait_for_timeout(2200)
                            clicked = True
                            break
                    if clicked:
                        break
                if not clicked:
                    for sel in ['a[href]']:
                        els = await page.query_selector_all(sel)
                        for el in els:
                            href = await el.get_attribute("href") or ""
                            needle = target.lower().replace(" ", "")
                            if href and needle in href.lower().replace(" ", ""):
                                await el.scroll_into_view_if_needed()
                                await el.click()
                                await page.wait_for_timeout(2200)
                                clicked = True
                                break
                        if clicked:
                            break
                if not clicked:
                    nav_fail.append(target)
                    _log(rec, "navigate", "FAIL", f"no click target for {target!r}")
                    continue
                title = await page.title()
                nav_ok.append({"target": target, "url": page.url, "title": title})
                _log(rec, "navigate", "PASS", f"{target!r} -> {page.url!r} title={title!r}")
                await page.screenshot(path=str(SC / f"nav_{target.replace('/', '_').replace(' ', '_')[:40]}.png"))

            _log(
                rec,
                "navigation_coverage",
                "PASS" if len(nav_fail) == 0 else "PARTIAL",
                f"visited {len(nav_ok)}/{len(chosen_clean)}; failed/no-click: {nav_fail}",
            )
            rec["nav_ok"] = nav_ok
            rec["nav_fail"] = nav_fail

            # Provenance & Integrity explicit
            target = "Provenance & Integrity"
            if target in navset:
                clicked = False
                for sel in NAV_SELECTORS:
                    els = await page.query_selector_all(sel)
                    for el in els:
                        try:
                            raw_txt = (await el.inner_text()).strip()
                            txt = _clean(raw_txt)
                        except Exception:
                            txt = ""
                        if txt == target:
                            await el.scroll_into_view_if_needed()
                            await el.click()
                            await page.wait_for_timeout(3000)
                            clicked = True
                            break
                    if clicked:
                        break
                if clicked:
                    prov_text = (await page.inner_text("body")).lower()
                    checks = {
                        "has_provenance_title": "provenance" in prov_text,
                        "has_integrity_title": "integrity" in prov_text,
                        "reported_not_redone_present": ("reported, not redone" in prov_text) or ("reported, not re-run" in prov_text),
                        "no_sha256_recomputed_present": ("no sha-256 digest is recomputed" in prov_text),
                        "performed_at_load_present": "performed at load time" in prov_text,
                        "not_performed_by_dashboard_present": "not performed by this dashboard" in prov_text,
                    }
                    allok = all(checks.values())
                    _log(
                        rec,
                        "provenance_wording",
                        "PASS" if allok else "FAIL",
                        f"checks={checks}; text_preview={prov_text[:400]!r}",
                    )
                    rec["provenance_checks"] = checks
                    rec["provenance_text_preview"] = (await page.inner_text("body"))[:2000]
                    await page.screenshot(path=str(SC / "provenance_wording.png"))
                else:
                    _log(rec, "provenance_nav", "FAIL", "could not click Provenance & Integrity")
            else:
                _log(rec, "provenance_nav", "BLOCKED", "Provenance & Integrity not in nav candidates")

            # External Data inspect
            target = "External Data"
            if target in navset:
                clicked = False
                for sel in NAV_SELECTORS:
                    els = await page.query_selector_all(sel)
                    for el in els:
                        try:
                            raw_txt = (await el.inner_text()).strip()
                            txt = _clean(raw_txt)
                        except Exception:
                            txt = ""
                        if txt == target:
                            await el.scroll_into_view_if_needed()
                            await el.click()
                            await page.wait_for_timeout(2500)
                            clicked = True
                            break
                    if clicked:
                        break
                if clicked:
                    ext_text = (await page.inner_text("body")).lower()
                    page_html = (await page.content()).lower()
                    extchecks = {
                        "has_external_title": "external" in ext_text,
                        "has_upload_control": ('type="file"' in page_html) or ("upload" in ext_text),
                        "supported_analyses_listed": ("supported" in ext_text) or ("deterministic" in ext_text),
                        "unavailable_analyses_listed": (
                            "unavailable" in ext_text
                            or "not available" in ext_text
                            or "not supported" in ext_text
                        ),
                    }
                    _log(
                        rec,
                        "external_inspect",
                        "PASS" if all(extchecks.values()) else "PARTIAL",
                        f"checks={extchecks}; text_preview={ext_text[:400]!r}",
                    )
                    rec["external_checks"] = extchecks
                    rec["external_text_preview"] = (await page.inner_text("body"))[:2000]
                    await page.screenshot(path=str(SC / "external_before.png"))
                    for phrase in ("not run on uploaded data", "ro1", "ro2", "ro3"):
                        _log(
                            rec,
                            "external_inspect_detail",
                            "INFO",
                            f"phrase {phrase!r} present={phrase in ext_text}",
                        )
                    if not all(extchecks.values()):
                        _log(
                            rec,
                            "external_inspect_detail",
                            "INFO",
                            f"missing={sorted([k for k,v in extchecks.items() if not v])}",
                        )
                else:
                    _log(rec, "external_nav", "FAIL", "could not click External Data")
            else:
                _log(rec, "external_nav", "BLOCKED", "External Data not in nav candidates")

            await b.close()
        except Exception as e:
            _log(rec, "browser_error", "FAIL", str(e))
            _erred(b)

    LOG.write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print("\nWROTE", LOG)
    return rec

if __name__ == "__main__":
    asyncio.run(main())
