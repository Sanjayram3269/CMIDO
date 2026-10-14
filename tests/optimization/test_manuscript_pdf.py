"""Regression test for the manuscript PDF deliverable.

Rebuilds the PDF from the authoritative Markdown + publication figures into a
temporary location and verifies the invariants that a silent regression would
break: page count, embedded figures, figure aspect ratios, absence of clipped
text, absence of blank pages, and presence of expected text markers.

Uses pymupdf (already a project dependency for figure generation); skips with a
clear reason if it is unavailable rather than passing vacuously.
"""

from __future__ import annotations

import importlib.util
import pathlib
import tempfile

import pytest

pymupdf = pytest.importorskip("pymupdf", reason="pymupdf not installed")

ROOT = pathlib.Path(__file__).resolve().parents[2]
RENDERER = (
    ROOT
    / "deliverables"
    / "CMIDO_FINAL_RESEARCH_PACKAGE"
    / "01_MANUSCRIPT"
    / "build_manuscript_pdf.py"
)
SOURCE_MD = (
    ROOT
    / "deliverables"
    / "CMIDO_FINAL_RESEARCH_PACKAGE"
    / "01_MANUSCRIPT"
    / "CMIDO_DRAFT_MANUSCRIPT.md"
)
FIGURE_DIR = (
    ROOT / "deliverables" / "CMIDO_FINAL_RESEARCH_PACKAGE" / "02_FIGURES"
)
EXPECTED_FIGURES = [
    "F1_RO1_calibration_coverage.png",
    "F2_RO2_tail_comparison.png",
    "F3_RO2_propagation_tail.png",
    "F4_RO2_joint_independent_sensitivity.png",
    "F5_RO3_controller_descriptives.png",
    "F6_RO3_ablation_effects.png",
]
EXPECTED_MARKERS = [
    "CMIDO",
    "Abstract",
    "Introduction",
    "References",
    "quantile",
    "Figure 1",
    "Figure 6",
    "procurement",
]


def _load_renderer():
    spec = importlib.util.spec_from_file_location("build_manuscript_pdf", RENDERER)
    assert spec and spec.loader, "could not load manuscript renderer spec"
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _build(tmp_path: pathlib.Path):
    mod = _load_renderer()
    out = tmp_path / "manuscript_test.pdf"
    manifest = mod.build_pdf(SOURCE_MD, out, FIGURE_DIR)
    return mod, out, manifest


def test_renderer_source_inputs_exist():
    assert RENDERER.is_file(), f"missing renderer: {RENDERER}"
    assert SOURCE_MD.is_file(), f"missing manuscript source: {SOURCE_MD}"
    assert FIGURE_DIR.is_dir(), f"missing figure dir: {FIGURE_DIR}"
    missing = [f for f in EXPECTED_FIGURES if not (FIGURE_DIR / f).is_file()]
    assert not missing, f"missing publication figures: {missing}"


def test_pdf_builds_and_embeds_all_figures(tmp_path):
    _, out, manifest = _build(tmp_path)
    assert out.is_file() and out.stat().st_size > 0
    assert manifest["figures_missing"] == [], (
        f"figures failed to embed: {manifest['figures_missing']}"
    )
    embedded = set(manifest["figures_locally_matched"].values())
    assert set(EXPECTED_FIGURES) <= embedded, (
        f"not all figures embedded: got {sorted(embedded)}"
    )


def test_pdf_page_count_and_text_markers(tmp_path):
    _, out, _ = _build(tmp_path)
    doc = pymupdf.open(str(out))
    try:
        assert doc.page_count >= 5, f"too few pages: {doc.page_count}"
        text = "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()
    assert len(text) > 5000, f"extracted text suspiciously short: {len(text)}"
    missing = [m for m in EXPECTED_MARKERS if m.lower() not in text.lower()]
    assert not missing, f"missing expected text markers: {missing}"


def test_pdf_embedded_images_preserve_source_aspect_ratio(tmp_path):
    _, out, _ = _build(tmp_path)
    source_ar = {}
    for name in EXPECTED_FIGURES:
        with pymupdf.open(str(FIGURE_DIR / name)) as _:
            pass
        from PIL import Image

        with Image.open(FIGURE_DIR / name) as im:
            source_ar[name] = im.size[0] / im.size[1]

    doc = pymupdf.open(str(out))
    try:
        placed = []
        for page in doc:
            for img in page.get_images(full=True):
                for r in page.get_image_rects(img[0]):
                    placed.append((img[2], img[3], r.width / r.height))
    finally:
        doc.close()

    assert len(placed) >= len(EXPECTED_FIGURES), (
        f"expected >= {len(EXPECTED_FIGURES)} embedded images, got {len(placed)}"
    )
    # every placed image must match some source figure's aspect ratio closely
    for pw, ph, ar in placed:
        src_ar = pw / ph  # native pixel aspect
        assert abs(ar - src_ar) < 0.01, (
            f"placed image {pw}x{ph} distorted: placed ar={ar:.4f} vs native {src_ar:.4f}"
        )


def test_pdf_has_no_clipped_text_or_blank_pages(tmp_path):
    _, out, _ = _build(tmp_path)
    doc = pymupdf.open(str(out))
    try:
        pw, ph = doc[0].rect.width, doc[0].rect.height
        for i, page in enumerate(doc):
            for b in page.get_text("blocks"):
                x0, y0, x1, y1 = b[:4]
                assert x1 <= pw - 20, f"p{i+1}: text clipped right (x1={x1:.1f} > {pw-20:.1f})"
                assert x0 >= 20, f"p{i+1}: text clipped left (x0={x0:.1f})"
                assert y1 <= ph - 20, f"p{i+1}: text clipped bottom (y1={y1:.1f} > {ph-20:.1f})"
            # blank-page check: ink coverage
            pix = page.get_pixmap(dpi=40)
            samples = pix.samples
            n = pix.width * pix.height
            nonwhite = sum(
                1
                for j in range(0, len(samples), pix.n)
                if samples[j] < 245 or samples[j + 1] < 245 or samples[j + 2] < 245
            )
            assert nonwhite / n > 0.002, f"p{i+1}: appears blank (ink={nonwhite/n:.5f})"
    finally:
        doc.close()


def test_verify_pdf_helper_reports_clean(tmp_path):
    mod, out, _ = _build(tmp_path)
    v = mod.verify_pdf(out)
    assert v["pages"] >= 5
    assert v["image_objects"] >= len(EXPECTED_FIGURES)
    assert v["text_length"] > 5000
    false_markers = [k for k, ok in v["text_presence_markers"].items() if not ok]
    assert not false_markers, f"verify_pdf markers missing: {false_markers}"
