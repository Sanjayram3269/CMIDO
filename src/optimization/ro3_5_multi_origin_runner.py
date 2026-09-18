from pathlib import Path
import argparse, json, subprocess, sys, time
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OPT = ROOT / "src" / "optimization" / "ro3_epsilon_pareto_optimizer.py"
SCEN_DIR = ROOT / "results" / "RO3" / "scenario_generation"
OUT = ROOT / "results" / "RO3" / "multi_origin"
OUT.mkdir(parents=True, exist_ok=True)

ORIGINS = [
    "2022-07-01","2022-08-01","2022-09-01","2022-10-01",
    "2022-11-01","2022-12-01","2023-01-01","2023-02-01",
    "2023-03-01","2023-04-01","2023-05-01"
]
MATERIALS = ["Cement","Granite","Ready Mixed Concrete","Steel Reinforcement Bars"]

def validate_scenarios(n, origin):
    path = SCEN_DIR / f"RO3_step32_scenarios_{n}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing scenario file: {path}")
    df = pd.read_csv(path, usecols=["forecast_origin","material","scenario_id","month_ahead"])
    df["forecast_origin"] = pd.to_datetime(df["forecast_origin"])
    o = pd.Timestamp(origin)
    d = df[df["forecast_origin"] == o]
    if d.empty:
        raise ValueError(f"No scenario rows for {origin}")
    counts = d.groupby("material")["scenario_id"].nunique().to_dict()
    for m in MATERIALS:
        if counts.get(m) != n:
            raise ValueError(f"{origin}: {m} has {counts.get(m)} scenarios; expected {n}")
        hs = sorted(d.loc[d.material == m, "month_ahead"].unique())
        if hs != list(range(1,13)):
            raise ValueError(f"{origin}: {m} horizon is {hs}")
    return len(d)

def completed_valid_origin(n, origin):
    tag = pd.Timestamp(origin).strftime("%Y%m%d")
    pareto_dir = ROOT / "results" / "RO3" / "pareto"
    p = pareto_dir / f"RO3_pareto_N{n}_{tag}.csv"
    d = pareto_dir / f"RO3_pareto_N{n}_{tag}_decisions.csv"
    m = pareto_dir / f"RO3_pareto_N{n}_{tag}_manifest.json"
    if not (p.exists() and d.exists() and m.exists()):
        return False
    try:
        pf = pd.read_csv(p)
        df = pd.read_csv(d)
        manifest = json.loads(m.read_text(encoding="utf-8"))
        if pf.empty or df.empty:
            return False
        required_p = {"pareto_id", "Z1", "Z2", "Z3"}
        if not required_p.issubset(pf.columns):
            return False
        if not {"pareto_id", "material", "month_ahead", "q"}.issubset(df.columns):
            return False
        if not np.isfinite(pf[["Z1","Z2","Z3"]].to_numpy(dtype=float)).all():
            return False
        return manifest.get("origin") == origin and manifest.get("n_scenarios") == n
    except Exception:
        return False

def run_origin(n, origin, levels):
    cmd = [sys.executable, str(OPT), "--n", str(n), "--origin", origin,
           "--epsilon-levels", str(levels)]
    t0 = time.perf_counter()
    p = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)
    elapsed = time.perf_counter() - t0
    record = {
        "scenario_count": n, "forecast_origin": origin,
        "return_code": p.returncode, "runtime_sec": elapsed,
        "stdout": p.stdout, "stderr": p.stderr
    }
    (OUT / f"execution_{pd.Timestamp(origin):%Y%m%d}.json").write_text(
        json.dumps(record, indent=2), encoding="utf-8")
    if p.returncode != 0:
        raise RuntimeError(f"Optimizer failed at {origin}. See execution log.")
    return record

def aggregate(n, origins):
    pareto_dir = ROOT / "results" / "RO3" / "pareto"
    pareto_frames, decision_frames, records = [], [], []
    for o in origins:
        tag = pd.Timestamp(o).strftime("%Y%m%d")
        p = pareto_dir / f"RO3_pareto_N{n}_{tag}.csv"
        d = pareto_dir / f"RO3_pareto_N{n}_{tag}_decisions.csv"
        m = pareto_dir / f"RO3_pareto_N{n}_{tag}_manifest.json"
        if not (p.exists() and d.exists() and m.exists()):
            raise FileNotFoundError(f"Missing output set for {o}")
        pf = pd.read_csv(p); df = pd.read_csv(d)
        pf["forecast_origin"] = o
        df["forecast_origin"] = o
        pareto_frames.append(pf); decision_frames.append(df)
        records.append(json.loads(m.read_text(encoding="utf-8")))
    pa = pd.concat(pareto_frames, ignore_index=True)
    de = pd.concat(decision_frames, ignore_index=True)
    pa.to_csv(OUT / f"RO3_step35_pareto_all_origins_N{n}.csv", index=False)
    de.to_csv(OUT / f"RO3_step35_decisions_all_origins_N{n}.csv", index=False)

    summary = (pa.groupby("forecast_origin")
               .agg(pareto_count=("pareto_id","count"),
                    Z1_min=("Z1","min"), Z1_median=("Z1","median"), Z1_max=("Z1","max"),
                    Z2_min=("Z2","min"), Z2_median=("Z2","median"), Z2_max=("Z2","max"),
                    Z3_min=("Z3","min"), Z3_median=("Z3","median"), Z3_max=("Z3","max"),
                    runtime_total_sec=("runtime_sec","sum"))
               .reset_index())
    summary.to_csv(OUT / f"RO3_step35_origin_summary_N{n}.csv", index=False)

    manifest = {
        "scenario_count": n, "origin_count": len(origins),
        "origins": origins, "materials": MATERIALS,
        "pareto_rows": len(pa), "decision_rows": len(de),
        "pareto_cardinality": {o:int(summary.loc[summary.forecast_origin==o,"pareto_count"].iloc[0]) for o in origins},
        "successful_manifests": records
    }
    (OUT / f"RO3_step35_manifest_N{n}.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8")
    return summary

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=2500)
    ap.add_argument("--epsilon-levels", type=int, default=3)
    ap.add_argument("--origins", nargs="*", default=ORIGINS)
    args = ap.parse_args()

    if args.origins != ORIGINS:
        raise ValueError("For the primary RO3.5 run, use the exact locked 11-origin set.")

    print("="*78)
    print("CMIDO RO3.5 — MULTI-ORIGIN PROCUREMENT OPTIMIZATION")
    print("="*78)
    print(f"Scenario count: {args.n}")
    print(f"Epsilon grid: {args.epsilon_levels} x {args.epsilon_levels}")
    print(f"Origins: {len(args.origins)}")
    print()

    for i, o in enumerate(args.origins, 1):
        print(f"[{i:02d}/11] Validating {o} ...", flush=True)
        rows = validate_scenarios(args.n, o)
        print(f"       scenario rows: {rows} PASS", flush=True)
        if completed_valid_origin(args.n, o):
            print(f"       existing valid N={args.n} result found — SKIPPING OPTIMIZATION", flush=True)
            continue
        print(f"       optimizing {o} ...", flush=True)
        run_origin(args.n, o, args.epsilon_levels)
        print(f"       {o}: OPTIMIZATION PASS", flush=True)

    summary = aggregate(args.n, args.origins)
    print()
    print("="*78)
    print("RO3.5 AGGREGATE SUMMARY")
    print("="*78)
    print(summary.to_string(index=False))
    print()
    if summary["pareto_count"].min() <= 0:
        raise RuntimeError("RO3.5 integrity failure: empty Pareto set.")
    print("DECISION: RO3.5_MULTI_ORIGIN_RUN_COMPLETE")
    print(f"Outputs: {OUT}")

if __name__ == "__main__":
    main()
