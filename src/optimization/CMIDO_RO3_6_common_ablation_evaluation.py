from pathlib import Path
import ast
import json
import re
import numpy as np
import pandas as pd

ROOT = Path(r"D:\CMIDO")
ABL = ROOT / "results" / "RO3" / "ablation"
O1O3 = ABL / "O1_O3"
O2 = ABL / "O2"
O4 = ABL / "O4_multi_origin"
OUT = ABL / "final_comparison"
OUT.mkdir(parents=True, exist_ok=True)

MATERIALS = ["Cement", "Granite", "Ready Mixed Concrete", "Steel Reinforcement Bars"]
ORIGINS = pd.to_datetime([
    "2022-07-01","2022-08-01","2022-09-01","2022-10-01","2022-11-01",
    "2022-12-01","2023-01-01","2023-02-01","2023-03-01","2023-04-01","2023-05-01"
])

def cvar_empirical(x, alpha=0.95):
    x = np.asarray(x, dtype=float)
    if len(x) == 0:
        return np.nan
    eta = np.unique(x)
    return float(np.min([
        e + np.mean(np.maximum(x-e, 0.0))/(1-alpha)
        for e in eta
    ]))

def parse_q(q):
    if pd.isna(q):
        return None
    s = str(q).strip()
    try:
        v = ast.literal_eval(s)
        if isinstance(v, (list, tuple, np.ndarray)):
            return np.asarray(v, dtype=float)
    except Exception:
        pass
    nums = re.findall(r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?", s)
    if len(nums) >= 12:
        return np.asarray([float(z) for z in nums[:12]])
    return None

def audit_o1o3():
    p = O1O3 / "RO3_step36_O1_O3_monthly_ledger.csv"
    df = pd.read_csv(p)
    df["forecast_origin"] = pd.to_datetime(df["forecast_origin"])
    df["period"] = pd.to_datetime(df["period"])
    required = {
        "controller","forecast_origin","material","period","month_ahead",
        "realized_demand","realized_price","ending_inventory",
        "shortage_quantity","procurement_cost","holding_cost","order_quantity"
    }
    assert required <= set(df.columns)
    assert set(df.controller) == {"O1","O3"}
    assert sorted(df.forecast_origin.unique()) == list(ORIGINS)
    assert set(df.material) == set(MATERIALS)
    assert len(df) == 1056
    return df

def audit_o2():
    p = O2 / "O2_realized_evaluation_ledger.csv"
    df = pd.read_csv(p)
    df["forecast_origin"] = pd.to_datetime(df["forecast_origin"])
    df["period"] = pd.to_datetime(df["period"])
    required = {
        "forecast_origin","material","period","demand","price",
        "order_qty","arrival_qty","shortage","ending_inventory",
        "procurement_cost","holding_cost"
    }
    assert required <= set(df.columns)
    assert sorted(df.forecast_origin.unique()) == list(ORIGINS)
    assert set(df.material) == set(MATERIALS)
    return df

def load_o4():
    rows = []
    for origin in ORIGINS:
        tag = origin.strftime("%Y-%m-%d")
        for mat in MATERIALS:
            fname = "O4_" + tag + "_" + mat.replace(" ", "_") + "_pareto.csv"
            p = O4 / fname
            assert p.exists(), f"Missing O4 file: {p}"
            d = pd.read_csv(p)
            sel = d[d["selected"].astype(bool)].copy()
            assert len(sel) == 1, f"O4 selection count != 1: {p}"
            q = parse_q(sel.iloc[0]["q"].iloc[0] if isinstance(sel.iloc[0]["q"], pd.Series) else sel.iloc[0]["q"])
            assert q is not None and len(q) == 12, f"Bad O4 q: {p}"
            rows.append({
                "controller":"O4",
                "forecast_origin":origin,
                "material":mat,
                "selected_candidate":sel.iloc[0]["candidate_id"],
                "selection_distance":float(sel.iloc[0]["selection_distance"]),
                "optimization_Z1":float(sel.iloc[0]["Z1"]),
                "optimization_Z2":float(sel.iloc[0]["Z2"]),
                "optimization_Z3":float(sel.iloc[0]["Z3"]),
                "q":q.tolist()
            })
    return pd.DataFrame(rows)

def build_o4_realized(o4_selected, realized):
    # Re-evaluate the selected O4 order vector against the same realized
    # demand/price paths used by O1/O2/O3. Arrival rule: first monthly
    # period whose month-start is on/after actual arrival (49-day duration
    # is material/scenario dependent in optimization; selected O4 q is
    # evaluated using its existing decision policy and the frozen RO2 median
    # duration only where a deterministic realized arrival is required).
    #
    # To avoid inventing a scenario realization for O4, use the selected
    # policy's q and the realized evaluation calendar with the frozen
    # deterministic median duration of 49 days, consistent with O1/O3.
    # This creates a common realized-policy evaluation, not an O4 stochastic
    # objective.
    duration_days = 49.0
    led = []
    for _, r in o4_selected.iterrows():
        origin = pd.Timestamp(r.forecast_origin)
        mat = r.material
        sub = realized[(realized.forecast_origin==origin)&(realized.material==mat)].sort_values("period").copy()
        assert len(sub) == 12
        q = np.asarray(r.q, dtype=float)
        inv = 0.0
        for j, (_, rr) in enumerate(sub.iterrows()):
            period = pd.Timestamp(rr.period)
            order = max(0.0, q[j])
            # Orders placed in month j arrive in first month-start on/after
            # actual arrival date. For 49 days, this is generally j+2.
            arrival_date = period + pd.to_timedelta(duration_days, unit="D")
            available = 0.0
            for s in range(j+1):
                order_period = pd.Timestamp(sub.iloc[s].period)
                arr = order_period + pd.to_timedelta(duration_days, unit="D")
                if period >= arr:
                    available += q[s]
            demand = float(rr.demand)
            price = float(rr.price)
            net = inv + available
            shortage = max(0.0, demand - max(0.0, net))
            ending = max(0.0, net - demand)
            procurement_cost = order * price
            holding_cost = 0.025 * price * ending
            led.append({
                "controller":"O4",
                "forecast_origin":origin,
                "material":mat,
                "period":period,
                "month_ahead":j+1,
                "realized_demand":demand,
                "realized_price":price,
                "order_quantity":order,
                "ending_inventory":ending,
                "shortage_quantity":shortage,
                "procurement_cost":procurement_cost,
                "holding_cost":holding_cost
            })
            inv = ending
    return pd.DataFrame(led)

def main():
    print("CMIDO RO3.6 — COMMON O1/O2/O3/O4 REALIZED EVALUATION")
    print("="*70)

    o1o3 = audit_o1o3()
    o2 = audit_o2()
    o4sel = load_o4()

    # O1/O3 realized ledger normalization
    a = o1o3.rename(columns={
        "realized_demand":"demand",
        "realized_price":"price",
        "order_quantity":"order_qty",
        "shortage_quantity":"shortage"
    })[["controller","forecast_origin","material","period","month_ahead",
        "demand","price","order_qty","ending_inventory","shortage",
        "procurement_cost","holding_cost"]].copy()

    b = o2.copy()
    b["controller"] = "O2"
    b = b.rename(columns={
        "demand":"demand","price":"price","order_qty":"order_qty",
        "shortage":"shortage"
    })[["controller","forecast_origin","material","period",
        "demand","price","order_qty","ending_inventory","shortage",
        "procurement_cost","holding_cost"]].copy()

    # Common realized paths for O1/O2/O3. We explicitly take realized
    # observations from O1 ledger because all controllers share the same
    # locked evaluation-realization matrix; verify against O2.
    key = ["forecast_origin","material","period"]
    chk = a.merge(b, on=key, suffixes=("_o1","_o2"))
    assert np.allclose(chk.demand_o1, chk.demand_o2)
    assert np.allclose(chk.price_o1, chk.price_o2)

    # O3/O1 already share realized fields; O4 evaluation uses same realized
    # demand/price matrix.
    realized = a[a.controller=="O1"].copy()
    assert {"forecast_origin","material","period","demand","price"} <= set(realized.columns)
    # Keep the O1 realized-ledger field names expected by build_o4_realized.
    # The previous version unnecessarily renamed demand while leaving price
    # unchanged, causing an AttributeError on realized_price.
    o4led = build_o4_realized(o4sel, realized)

    # Combine ledgers. O1/O3 have one row per month; O2 one row per month.
    common = pd.concat([a, b], ignore_index=True)
    o4norm = o4led.rename(columns={
        "realized_demand":"demand",
        "realized_price":"price",
        "order_quantity":"order_qty",
        "shortage_quantity":"shortage"
    })
    common = pd.concat([common, o4norm], ignore_index=True)

    # Ensure exactly 11*4*12 rows per controller.
    counts = common.groupby("controller").size().to_dict()
    print("Ledger rows by controller:", counts)
    assert counts == {"O1":528, "O2":528, "O3":528, "O4":528}

    # Origin-level aggregation is the inferential unit.
    rows = []
    for (ctrl, origin), g in common.groupby(["controller","forecast_origin"], sort=True):
        shortage_path = g.groupby("period")["shortage"].sum().sort_index().to_numpy()
        rows.append({
            "controller":ctrl,
            "forecast_origin":origin,
            "realized_procurement_holding_cost":g.procurement_cost.sum()+g.holding_cost.sum(),
            "realized_procurement_cost":g.procurement_cost.sum(),
            "realized_holding_cost":g.holding_cost.sum(),
            "realized_total_shortage":g.shortage.sum(),
            "realized_service_level":1.0-g.shortage.sum()/g.demand.sum(),
            "realized_total_procurement_quantity":g.order_qty.sum(),
            "realized_mean_ending_inventory":g.ending_inventory.mean(),
            "realized_procurement_events":int((g.order_qty>1e-9).sum()),
            "realized_shortage_cvar95_monthly":cvar_empirical(shortage_path, .95),
            "total_realized_demand":g.demand.sum()
        })
    origin = pd.DataFrame(rows)

    # Material-level summary.
    mat = common.groupby(["controller","forecast_origin","material"], as_index=False).agg(
        realized_procurement_cost=("procurement_cost","sum"),
        realized_holding_cost=("holding_cost","sum"),
        realized_total_shortage=("shortage","sum"),
        realized_total_procurement_quantity=("order_qty","sum"),
        realized_mean_ending_inventory=("ending_inventory","mean"),
        realized_procurement_events=("order_qty", lambda x: int((x>1e-9).sum())),
        total_realized_demand=("demand","sum")
    )
    mat["realized_procurement_holding_cost"] = mat.realized_procurement_cost + mat.realized_holding_cost
    mat["realized_service_level"] = 1 - mat.realized_total_shortage / mat.total_realized_demand

    # Controller descriptive statistics across 11 origins.
    desc = origin.groupby("controller").agg(
        origins=("forecast_origin","nunique"),
        mean_cost=("realized_procurement_holding_cost","mean"),
        median_cost=("realized_procurement_holding_cost","median"),
        mean_shortage=("realized_total_shortage","mean"),
        median_shortage=("realized_total_shortage","median"),
        mean_service=("realized_service_level","mean"),
        median_service=("realized_service_level","median"),
        mean_procurement_qty=("realized_total_procurement_quantity","mean"),
        mean_inventory=("realized_mean_ending_inventory","mean"),
        mean_events=("realized_procurement_events","mean"),
        mean_cvar95=("realized_shortage_cvar95_monthly","mean")
    ).reset_index()

    # Paired controller differences at origin level.
    wide = origin.pivot(index="forecast_origin", columns="controller")
    comparisons = []
    pairs = [("O2","O1"),("O3","O1"),("O4","O1"),("O4","O2"),("O4","O3")]
    metrics = [
        "realized_procurement_holding_cost",
        "realized_total_shortage",
        "realized_service_level",
        "realized_total_procurement_quantity",
        "realized_mean_ending_inventory",
        "realized_procurement_events",
        "realized_shortage_cvar95_monthly"
    ]
    for newer, base in pairs:
        for metric in metrics:
            x = origin[origin.controller==newer].set_index("forecast_origin")[metric]
            y = origin[origin.controller==base].set_index("forecast_origin")[metric]
            d = (x-y).dropna()
            comparisons.append({
                "comparison":f"{newer}_vs_{base}",
                "metric":metric,
                "n_origins":len(d),
                "mean_difference":d.mean(),
                "median_difference":d.median(),
                "mean_relative_difference":np.mean(
                    np.where(np.abs(y.loc[d.index].to_numpy())>1e-12,
                             d.to_numpy()/y.loc[d.index].to_numpy(), np.nan)
                ),
                "origins_improved_for_metric_direction_agnostic":np.nan
            })
    comp = pd.DataFrame(comparisons)

    # Bootstrap paired CI for mean difference.
    rng = np.random.default_rng(20260916)
    boot_rows = []
    for newer, base in pairs:
        for metric in metrics:
            x = origin[origin.controller==newer].set_index("forecast_origin")[metric]
            y = origin[origin.controller==base].set_index("forecast_origin")[metric]
            d = (x-y).dropna().to_numpy()
            if len(d)==0:
                continue
            boots = np.empty(10000)
            for i in range(10000):
                boots[i] = rng.choice(d, size=len(d), replace=True).mean()
            boot_rows.append({
                "comparison":f"{newer}_vs_{base}",
                "metric":metric,
                "n_origins":len(d),
                "mean_difference":float(d.mean()),
                "ci95_lower":float(np.quantile(boots,.025)),
                "ci95_upper":float(np.quantile(boots,.975)),
                "bootstrap_reps":10000
            })
    boot = pd.DataFrame(boot_rows)

    # Integrity checks.
    checks = []
    def check(name, cond, detail=""):
        checks.append({"check":name,"passed":bool(cond),"detail":detail})
        print("[PASS]" if cond else "[FAIL]", name, detail)

    check("O1/O3 ledger rows", len(a)==1056, str(len(a)))
    check("O2 ledger rows", len(b)==528, str(len(b)))
    check("O4 selected policies", len(o4sel)==44, str(len(o4sel)))
    check("Common controllers", set(common.controller)=={"O1","O2","O3","O4"})
    check("11 origins/controller", all(origin.groupby("controller").forecast_origin.nunique()==11))
    check("12 months/material-origin", len(common.groupby(["controller","forecast_origin","material"]).size())==44*4)
    check("Realized demand common O1/O2", np.allclose(chk.demand_o1, chk.demand_o2))
    check("Realized price common O1/O2", np.allclose(chk.price_o1, chk.price_o2))
    check("Finite primary metrics", np.isfinite(origin[metrics].to_numpy()).all())
    check("Service in [0,1]", ((origin.realized_service_level>=0)&(origin.realized_service_level<=1)).all())
    check("Nonnegative orders", (common.order_qty>=-1e-9).all())
    check("Nonnegative shortage", (common.shortage>=-1e-9).all())
    check("Nonnegative inventory", (common.ending_inventory>=-1e-9).all())

    audit = pd.DataFrame(checks)
    status = "PASS" if audit.passed.all() else "HOLD"

    # Save.
    common.to_csv(OUT/"RO3_step36_common_realized_ledger.csv", index=False)
    origin.to_csv(OUT/"RO3_step36_origin_level_results.csv", index=False)
    mat.to_csv(OUT/"RO3_step36_material_level_results.csv", index=False)
    desc.to_csv(OUT/"RO3_step36_controller_descriptive_summary.csv", index=False)
    comp.to_csv(OUT/"RO3_step36_paired_comparisons.csv", index=False)
    boot.to_csv(OUT/"RO3_step36_paired_bootstrap_ci.csv", index=False)
    audit.to_csv(OUT/"RO3_step36_common_evaluation_audit.csv", index=False)

    manifest = {
        "status":status,
        "controllers":["O1","O2","O3","O4"],
        "origins":[x.strftime("%Y-%m-%d") for x in ORIGINS],
        "materials":MATERIALS,
        "primary_inferential_unit":"forecast_origin",
        "bootstrap_reps":10000,
        "notes":[
            "O4 realized evaluation uses the selected O4 quantity vectors against the common realized demand/price paths.",
            "O4 realized arrival uses the frozen 49-day deterministic duration for common-policy evaluation; this is distinct from O4 stochastic optimization objectives.",
            "Monthly realized shortage CVaR95 is reported as a descriptive stress metric over the 12 realized months, not as an independent probabilistic forecast."
        ]
    }
    (OUT/"RO3_step36_common_evaluation_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")

    print("\nCHECKS PASSED:", int(audit.passed.sum()), "/", len(audit))
    print("STATUS:", status)
    print("OUTPUT:", OUT)

if __name__ == "__main__":
    main()
