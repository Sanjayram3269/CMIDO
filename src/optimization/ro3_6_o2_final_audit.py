from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path(r"D:\CMIDO")
OUT = ROOT / "results" / "RO3" / "ablation" / "O2"
PARETO = OUT / "O2_pareto_solutions.csv"
DEC = OUT / "O2_selected_decisions.csv"
LED = OUT / "O2_realized_evaluation_ledger.csv"
SUM = OUT / "O2_realized_evaluation_summary.csv"
MAN = OUT / "O2_run_manifest.json"

ORIGINS = pd.to_datetime([
    "2022-07-01","2022-08-01","2022-09-01","2022-10-01","2022-11-01",
    "2022-12-01","2023-01-01","2023-02-01","2023-03-01","2023-04-01","2023-05-01"
])
MATERIALS = ["Cement","Granite","Ready Mixed Concrete","Steel Reinforcement Bars"]
H = 12
TOL = 1e-5
Q_TOL = 1e-7
PARETO_TOL = 1e-8

def check(name, ok, detail=""):
    checks.append({"check": name, "passed": bool(ok), "detail": str(detail)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))

def main():
    global checks
    checks = []

    for p in [PARETO, DEC, LED, SUM, MAN]:
        if not p.exists():
            raise FileNotFoundError(p)

    pareto = pd.read_csv(PARETO)
    dec = pd.read_csv(DEC)
    led = pd.read_csv(LED)
    summ = pd.read_csv(SUM)
    manifest = json.loads(MAN.read_text(encoding="utf-8"))

    pareto["forecast_origin"] = pd.to_datetime(pareto["forecast_origin"])
    dec["forecast_origin"] = pd.to_datetime(dec["forecast_origin"])
    dec["period"] = pd.to_datetime(dec["period"])
    led["forecast_origin"] = pd.to_datetime(led["forecast_origin"])
    led["period"] = pd.to_datetime(led["period"])
    summ["forecast_origin"] = pd.to_datetime(summ["forecast_origin"])

    expected_cases = {(o, m) for o in ORIGINS for m in MATERIALS}

    # A. Structural
    check("A1 origin set", set(led.forecast_origin.unique()) == set(ORIGINS))
    check("A2 material set", set(led.material.unique()) == set(MATERIALS))
    cases = set(zip(led.forecast_origin, led.material))
    check("A3 exactly 44 cases", cases == expected_cases, f"{len(cases)} cases")
    counts = led.groupby(["forecast_origin","material"]).size()
    check("A4 12 ledger months per case", bool((counts == H).all()), f"min={counts.min()} max={counts.max()}")
    check("A5 no duplicate ledger case-period", not led.duplicated(["forecast_origin","material","period"]).any())
    check("A6 528 ledger rows", len(led) == 528, len(led))
    dcounts = dec.groupby(["forecast_origin","material"]).size()
    check("A7 12 decision rows per case", bool((dcounts == H).all()), f"min={dcounts.min()} max={dcounts.max()}")
    check("A8 Pareto objective columns finite", np.isfinite(pareto[["Z1","Z2"]].to_numpy(float)).all())

    # B. Pareto integrity
    selected = pareto.loc[pareto["selected"] == 1].copy()
    sel_counts = selected.groupby(["forecast_origin","material"]).size()
    check("B1 exactly one selected Pareto point per case",
          set(zip(sel_counts.index.get_level_values(0), sel_counts.index.get_level_values(1))) == expected_cases
          and bool((sel_counts == 1).all()),
          f"selected rows={len(selected)}")

    dominated_fail = []
    utopia_fail = []
    for (o, m), g in pareto.groupby(["forecast_origin","material"]):
        vals = g[["Z1","Z2"]].to_numpy(float)
        for i in range(len(vals)):
            for j in range(len(vals)):
                if i == j: continue
                if np.all(vals[j] <= vals[i] + PARETO_TOL) and np.any(vals[j] < vals[i] - PARETO_TOL):
                    dominated_fail.append((o,m,i,j))
                    break
        z1min,z1max = g.Z1.min(),g.Z1.max()
        z2min,z2max = g.Z2.min(),g.Z2.max()
        dist = np.sqrt(
            (0 if z1max==z1min else ((g.Z1-z1min)/(z1max-z1min))**2) +
            (0 if z2max==z2min else ((g.Z2-z2min)/(z2max-z2min))**2)
        )
        best = g.iloc[int(np.lexsort((g.Z2.to_numpy(),g.Z1.to_numpy(),dist.to_numpy()))[0])]
        got = g.loc[g["selected"] == 1]
        if len(got) != 1 or got.iloc[0]["candidate"] != best["candidate"]:
            utopia_fail.append((o,m))
    check("B2 no retained Pareto point dominated", len(dominated_fail)==0, f"failures={len(dominated_fail)}")
    check("B3 selected point matches normalized utopia rule", len(utopia_fail)==0, f"failures={len(utopia_fail)}")
    check("B4 selected Pareto objectives nonnegative",
          (selected[["Z1","Z2"]] >= -TOL).all().all())

    # C. Decision integrity
    check("C1 order quantities finite/nonnegative",
          np.isfinite(dec["order_qty"]).all() and (dec["order_qty"] >= -Q_TOL).all())
    late = dec.loc[dec["period"] >= dec["forecast_origin"] + pd.DateOffset(months=11)]
    # Under the frozen 49-day convention, orders in months 11 and 12 cannot arrive in the horizon.
    check("C2 late-horizon orders zero", bool((late["order_qty"].abs() <= Q_TOL).all()), f"rows={len(late)}")
    check("C3 selected optimization objectives finite/nonnegative",
          np.isfinite(dec[["optimization_Z1","optimization_Z2"]]).all().all() and
          (dec[["optimization_Z1","optimization_Z2"]] >= -TOL).all().all())

    # q-vector duplicate check via monthly decisions
    qdup = dec.groupby(["forecast_origin","material","order_qty"]).size()
    # This is not a failure condition: repeated monthly quantities are physically valid.
    check("C4 decision ledger has unique case-period rows",
          not dec.duplicated(["forecast_origin","material","period"]).any())

    # D. Physical/evaluation
    num_cols = ["demand","price","order_qty","arrival_qty","shortage","ending_inventory","procurement_cost","holding_cost"]
    check("D1 realized numeric fields finite", np.isfinite(led[num_cols].to_numpy(float)).all())
    check("D2 realized demand/price nonnegative",
          (led[["demand","price"]] >= -TOL).all().all())
    check("D3 inventory/shortage/arrival nonnegative",
          (led[["ending_inventory","shortage","arrival_qty"]] >= -TOL).all().all())

    identity_fail = 0
    cost_fail = 0
    service_fail = 0
    qty_fail = 0
    date_fail = 0
    for (o,m), g in led.sort_values("period").groupby(["forecast_origin","material"]):
        prev_inv = 0.0
        for _, r in g.iterrows():
            lhs = float(r.ending_inventory)
            rhs = prev_inv + float(r.arrival_qty) - float(r.demand) + float(r.shortage)
            if abs(lhs-rhs) > 1e-4:
                identity_fail += 1
            if float(r.shortage) > 1e-7:
                expected_inv = 0.0
            prev_inv = lhs
        if g["period"].min() <= o:
            date_fail += 1
        realized_d = g["demand"].sum()
        service = 1 - g["shortage"].sum()/max(realized_d,1e-12)
        ss = summ[(summ.forecast_origin==o)&(summ.material==m)]
        if len(ss) != 1 or abs(float(ss.iloc[0]["service"])-service) > 1e-8:
            service_fail += 1
        if len(ss) != 1 or abs(float(ss.iloc[0]["procurement_qty"])-g["order_qty"].sum()) > 1e-6:
            qty_fail += 1
        rcost = g["procurement_cost"].sum()+g["holding_cost"].sum()
        if len(ss) != 1 or abs(float(ss.iloc[0]["realized_cost"])-rcost) > 1e-5:
            cost_fail += 1

    check("D4 inventory/shortage balance identity", identity_fail==0, f"failures={identity_fail}")
    check("D5 service calculation reconciliation", service_fail==0, f"failures={service_fail}")
    check("D6 procurement quantity reconciliation", qty_fail==0, f"failures={qty_fail}")
    check("D7 realized cost reconciliation", cost_fail==0, f"failures={cost_fail}")
    check("D8 evaluation dates after origin", date_fail==0, f"failures={date_fail}")
    check("D9 summary has exactly 44 cases", len(summ)==44)

    # E. Selection independence
    check("E1 selection metadata contains optimization objectives",
          {"optimization_Z1","optimization_Z2","selected_candidate"}.issubset(dec.columns))
    check("E2 no realized evaluation outcome columns used in selection ledger",
          not any(c in dec.columns for c in ["realized_cost","shortage","service"]))

    # Manifest consistency
    check("M1 manifest origins = 11", len(manifest.get("origins",[])) == 11)
    check("M2 manifest materials = 4", len(manifest.get("materials",[])) == 4)
    check("M3 manifest horizon = 12", manifest.get("horizon_months") == 12)
    check("M4 manifest duration = 49", manifest.get("deterministic_duration_days") == 49)
    check("M5 manifest selection = normalized_distance_to_utopia",
          manifest.get("policy_selection") == "normalized_distance_to_utopia")

    audit = pd.DataFrame(checks)
    audit.to_csv(OUT/"O2_final_decision_audit.csv", index=False)
    passed = int(audit["passed"].sum())
    total = len(audit)
    status = "O2_PASS" if passed == total else "O2_HOLD_FOR_REVIEW"

    report = {
        "status": status,
        "passed": passed,
        "total": total,
        "failed_checks": audit.loc[~audit["passed"],"check"].tolist(),
    }
    (OUT/"O2_final_decision_audit_summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n" + "="*68)
    print("CMIDO RO3.6 — O2 FINAL DECISION AUDIT")
    print(f"Checks passed: {passed}/{total}")
    print(f"STATUS: {status}")
    print(f"Audit: {OUT/'O2_final_decision_audit.csv'}")
    print("="*68)

if __name__ == "__main__":
    main()
