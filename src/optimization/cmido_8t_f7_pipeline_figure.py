"""CMIDO 8T — F7 integrated-pipeline diagram generator.

F7 is a conceptual/structural figure: it shows the implemented CMIDO
forecast → uncertainty → risk → decision pipeline and the provenance class of
each stage. It is generated entirely from the label/colour definitions in this
script — it contains no data-derived quantities, so it has no table source.

The generator writes the figure into the publication figure folder, records a
machine-readable manifest with the output SHA-256 and per-label checks, and
refuses to claim more than the implemented pipeline supports (the supplier
lead-time caveat is part of the figure itself).
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

STAGE = "8T"
OUTPUT_NAME = "F7_CMIDO_integrated_pipeline.png"

# Provenance classes (kept consistent with the dashboard provenance badges).
COLORS = {
    "OBS": "#0d5468",  # observed/eligible data
    "UNC": "#1a45d6",  # predictive uncertainty retained
    "RISK": "#7a2410",  # derived shortage/service risk
    "OP": "#12451e",  # optimization outputs
    "VAL": "#465062",  # validation/robustness evidence
    "SIM": "#b21f1f",  # simulated/scenario-derived (not observed)
}

LEGEND = [
    ("OBS", "OBS \u2014 observed/eligible data"),
    ("UNC", "UNC \u2014 predictive uncertainty retained"),
    ("RISK", "RISK \u2014 derived shortage/service risk"),
    ("OP", "OP \u2014 optimization outputs"),
    ("VAL", "VAL \u2014 validation/robustness evidence"),
    ("SIM", "SIM \u2014 simulated/scenario-derived (not observed)"),
]

LEFT_COLUMN = [
    ("OBS", "Observed/eligible input data"),
    ("UNC", "Probabilistic forecasting (price & demand)"),
    ("UNC", "Supply & lead-time uncertainty"),
    ("RISK", "Joint uncertainty propagation (demand \u00d7 supply/process duration)"),
    ("OP", "Multi-objective procurement optimization"),
    ("VAL", "Validation, ablation, and stress testing"),
]

RIGHT_COLUMN = [
    ("OBS", "Validated & mapped inputs (schema-mapped CSVs/JSON)"),
    ("UNC", "Predictive uncertainty retained (quantiles/distributions)"),
    ("SIM", "Validated duration representation; supplier-specific lead time NOT inferred"),
    ("RISK", "Shortage & service-risk distributions"),
    ("OP", "Cost / service / resilience trade-offs"),
    ("VAL", "Controlled O1/O2/O3/O4 contrasts + stress/robustness checks"),
]

TITLE = "CMIDO \u2014 uncertainty-preserving procurement pipeline"
SUBTITLE = "Flow of data, provenance, and uncertainty (empirical vs derived vs simulated)"
LEFT_HEADER = "INPUTS & UNCERTAINTY"
RIGHT_HEADER = "DECISION & VALIDATION"
CAVEAT = (
    "For the implemented CMIDO pipeline only; does not imply supplier-specific "
    "real lead-time evidence where unavailable."
)


def project_root() -> Path:
    override = os.getenv("CMIDO_ROOT")
    return Path(override).expanduser().resolve() if override else Path(__file__).resolve().parents[2]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _wrap(text: str, width: int = 34) -> str:
    words, lines, cur = text.split(), [], ""
    for word in words:
        if len(cur) + len(word) + 1 > width and cur:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    if cur:
        lines.append(cur)
    return "\n".join(lines)


def _box(ax, x: float, y: float, w: float, h: float, color: str, label: str) -> None:
    ax.add_patch(
        FancyBboxPatch(
            (x, y), w, h,
            boxstyle="round,pad=0.015,rounding_size=0.12",
            linewidth=0, facecolor=color, mutation_aspect=1.0,
        )
    )
    ax.text(
        x + w / 2, y + h / 2, _wrap(label),
        ha="center", va="center", color="white", fontsize=8.4, fontweight="bold",
        linespacing=1.25,
    )


def draw(path: Path) -> dict:
    """Render F7 to *path* and return the label inventory used."""
    fig, ax = plt.subplots(figsize=(11, 9.6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis("off")
    fig.suptitle(TITLE, fontsize=16, fontweight="bold", ha="left", x=0.03, y=0.985)
    fig.text(0.03, 0.952, SUBTITLE, fontsize=10.5, color="#334155", ha="left")

    left_x, right_x, box_w, box_h = 0.35, 5.35, 4.3, 0.95
    top = 8.55
    step = 1.18
    offset = step / 2  # right column staggers half a row after the propagation step

    header_y = top + box_h + 0.14
    ax.text(left_x + box_w / 2, header_y, LEFT_HEADER, ha="center", va="bottom",
            fontsize=10.5, fontweight="bold", color="#0d5468")
    ax.text(right_x + box_w / 2, header_y, RIGHT_HEADER, ha="center", va="bottom",
            fontsize=10.5, fontweight="bold", color="#12451e")

    labels = []
    for i, (cls, label) in enumerate(LEFT_COLUMN):
        y = top - i * step
        _box(ax, left_x, y, box_w, box_h, COLORS[cls], label)
        labels.append(label)
    for i, (cls, label) in enumerate(RIGHT_COLUMN):
        # rows 0-2 align; row 3 (shortage) staggers down; rows 4-5 realign
        shift = offset if i >= 3 else 0.0
        y = top - i * step - shift
        _box(ax, right_x, y, box_w, box_h, COLORS[cls], label)
        labels.append(label)

    # Flow arrow: joint propagation -> shortage & service-risk distributions.
    arrow_y = top - 3 * step + box_h / 2
    ax.annotate(
        "", xy=(right_x - 0.1, arrow_y - offset),
        xytext=(left_x + box_w + 0.1, arrow_y),
        arrowprops=dict(arrowstyle="->", color="#334155", lw=1.8),
    )

    # Provenance legend.
    ax.text(left_x, 1.62, "Provenance classes:", fontsize=10, fontweight="bold",
            color="#0f172a", va="top")
    for j, (cls, text) in enumerate(LEGEND):
        col, row = j // 3, j % 3
        lx = left_x + col * 4.9
        ly = 1.28 - row * 0.32
        ax.add_patch(FancyBboxPatch((lx, ly - 0.09), 0.26, 0.18,
                                    boxstyle="round,pad=0.01,rounding_size=0.04",
                                    linewidth=0, facecolor=COLORS[cls]))
        ax.text(lx + 0.36, ly, text, fontsize=9, color="#1f2937", va="center")
        labels.append(text)

    fig.text(0.03, 0.045, CAVEAT, fontsize=8.6, color="#475569", ha="left")
    fig.text(
        0.03, 0.018,
        f"Reproducible figure F7 \u2014 generated by code (matplotlib). "
        f"Not a scanned image. Stage {STAGE} generator: "
        f"src/optimization/cmido_8t_f7_pipeline_figure.py",
        fontsize=8.6, color="#475569", ha="left",
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return {"labels": labels}


def generate(root: Path | None = None) -> tuple[dict, list[dict]]:
    root = (root or project_root()).resolve()
    fig_dir = root / "deliverables/CMIDO_FINAL_RESEARCH_PACKAGE/02_FIGURES"
    out = root / "results/8T_f7_diagram"
    out.mkdir(parents=True, exist_ok=True)
    checks: list[dict] = []

    def ck(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"check": name, "passed": bool(ok), "detail": detail})

    target = fig_dir / OUTPUT_NAME
    inventory = draw(target)
    ck("F7_output_exists", target.exists(), str(target))
    ck("F7_eighteen_labels", len(inventory["labels"]) == 18, str(len(inventory["labels"])))
    ck("F7_twelve_stage_boxes", len(LEFT_COLUMN) + len(RIGHT_COLUMN) == 12)
    ck("F7_six_provenance_classes", set(COLORS) == {"OBS", "UNC", "RISK", "OP", "VAL", "SIM"})
    ck("F7_leadtime_caveat_present", "NOT inferred" in " ".join(inventory["labels"]))
    ck("F7_six_legend_entries", all(text in inventory["labels"] for _, text in LEGEND))
    # Conceptual diagram: no data-derived quantities (decimals, large counts) may
    # appear in its labels. Controller IDs like O1/O2 are names, not numbers.
    import re

    numeric_labels = [
        x for x in inventory["labels"]
        if re.search(r"\d+\.\d+|\b\d{3,}\b", x)
    ]
    ck("F7_no_data_derived_numbers", numeric_labels == [], ", ".join(numeric_labels[:3]))

    from PIL import Image

    with Image.open(target) as im:
        dpi = im.info.get("dpi", (None, None))
        ck("F7_saved_at_300dpi", dpi[0] is None or abs(dpi[0] - 300) <= 1, str(dpi))

    manifest = {
        "stage": STAGE,
        "status": "PASS" if checks and all(c["passed"] for c in checks) else "HOLD",
        "figure": OUTPUT_NAME,
        "figure_path": str(target.relative_to(root)),
        "sha256": sha256(target) if target.exists() else "",
        "source_kind": "conceptual diagram generated from this script's label definitions (no data table)",
        "generation_script": "src/optimization/cmido_8t_f7_pipeline_figure.py",
        "manuscript_section": ["1", "9.6"],
        "checks_passed": sum(c["passed"] for c in checks),
        "checks_total": len(checks),
    }
    (out / "CMIDO_8T_F7_MANIFEST.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    import csv

    with (out / "CMIDO_8T_F7_AUDIT.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["check", "passed", "detail"])
        writer.writeheader()
        writer.writerows(checks)
    return manifest, checks


def main() -> int:
    manifest, checks = generate()
    print("=" * 78)
    print("CMIDO 8T — F7 INTEGRATED-PIPELINE DIAGRAM GENERATOR")
    print("=" * 78)
    for row in checks:
        marker = "PASS" if row["passed"] else "FAIL"
        suffix = f" — {row['detail']}" if row["detail"] else ""
        print(f"[{marker}] {row['check']}{suffix}")
    print("=" * 78)
    print(f"STATUS: {manifest['status']} ({manifest['checks_passed']}/{manifest['checks_total']})")
    print(f"OUTPUT: {manifest['figure_path']} sha256={manifest['sha256'][:16]}…")
    print("=" * 78)
    return 0 if manifest["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
