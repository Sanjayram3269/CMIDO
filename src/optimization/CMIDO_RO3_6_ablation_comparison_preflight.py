from pathlib import Path
import pandas as pd
import json

ROOT = Path(r"D:\CMIDO")
R = ROOT / "results" / "RO3" / "ablation"

print("CMIDO RO3.6 — O1/O2/O3/O4 COMPARISON PREFLIGHT")
print("=" * 60)

targets = {
    "O1": R / "O1",
    "O2": R / "O2",
    "O3": R / "O3",
    "O4": R / "O4_multi_origin",
}

for name, path in targets.items():
    print(f"\n{name}: {path}")
    print("  exists:", path.exists())
    if path.exists():
        files = sorted(path.glob("*"))
        print("  files:", len(files))
        for f in files[:15]:
            print("   -", f.name)
        if len(files) > 15:
            print("   ...")

print("\nKnown O4 production outputs:")
o4 = targets["O4"]
if o4.exists():
    for f in sorted(o4.glob("*.csv")):
        try:
            df = pd.read_csv(f, nrows=3)
            print(f"  {f.name}: columns={list(df.columns)}")
        except Exception as e:
            print(f"  {f.name}: READ ERROR {e}")

print("\nKnown O2 outputs:")
o2 = targets["O2"]
if o2.exists():
    for f in sorted(o2.glob("*.csv")):
        try:
            df = pd.read_csv(f, nrows=3)
            print(f"  {f.name}: columns={list(df.columns)}")
        except Exception as e:
            print(f"  {f.name}: READ ERROR {e}")

print("\nKnown O1/O3 outputs:")
for name in ["O1","O3"]:
    p = targets[name]
    if p.exists():
        for f in sorted(p.glob("*.csv")):
            try:
                df = pd.read_csv(f, nrows=3)
                print(f"  {name}/{f.name}: columns={list(df.columns)}")
            except Exception as e:
                print(f"  {name}/{f.name}: READ ERROR {e}")

print("\nIMPORTANT:")
print("This is a PREFLIGHT ONLY.")
print("It does not run optimization and does not modify any files.")
print("Send the complete terminal output so the comparison assembler can use")
print("the actual frozen O1/O2/O3/O4 output schemas rather than guessing them.")
