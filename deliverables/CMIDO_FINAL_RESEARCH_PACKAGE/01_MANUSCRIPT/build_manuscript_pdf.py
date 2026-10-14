# -*- coding: utf-8 -*-
"""
Build the CMIDO draft manuscript PDF from the Markdown source and final figures.

This renderer is intentionally narrow and explicit. It does not try to be a
general-purpose Markdown engine or a substitute for the authoritative Markdown
source. It preserves manuscript text, renders declared figures at publication
scale, keeps the layout readable, and emits a clear marker whenever a figure or
image cannot be located or embedded.

Authoritative inputs
  - Source text : deliverables/CMIDO_FINAL_RESEARCH_PACKAGE/01_MANUSCRIPT/CMIDO_DRAFT_MANUSCRIPT.md
  - Figures     : deliverables/CMIDO_FINAL_RESEARCH_PACKAGE/02_FIGURES/<figure files>
  - Output      : deliverables/CMIDO_FINAL_RESEARCH_PACKAGE/01_MANUSCRIPT/CMIDO_DRAFT_MANUSCRIPT.pdf

Run from the repository root with:

    python -B <<'PY'
import pathlib, sys, importlib.util
spec = importlib.util.spec_from_file_location(
    "build_manuscript_pdf",
    pathlib.Path("deliverables/CMIDO_FINAL_RESEARCH_PACKAGE/01_MANUSCRIPT/build_manuscript_pdf.py"),
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
raise SystemExit(mod.main())
PY

Or, alternatively:

    python -B deliverables/CMIDO_FINAL_RESEARCH_PACKAGE/01_MANUSCRIPT/build_manuscript_pdf.py
"""

from __future__ import annotations

import hashlib
import pathlib
import re
import struct
import zlib
import sys
from typing import Any, Dict, List, Tuple, Optional

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent.parent
WORKSPACE_ROOT = ROOT

# Fall back to a known workspace root so the renderer stays usable when
# __file__ resolves under an unusual layout (shallow copies, zip runs, CI).
if not (WORKSPACE_ROOT / "deliverables/CMIDO_FINAL_RESEARCH_PACKAGE").is_dir():
    for _candidate in (pathlib.Path("d:/CMIDO"), pathlib.Path("/d/CMIDO")):
        if (_candidate / "deliverables/CMIDO_FINAL_RESEARCH_PACKAGE").is_dir():
            WORKSPACE_ROOT = _candidate.resolve()
            break

MANUSCRIPT_DIR = WORKSPACE_ROOT / "deliverables/CMIDO_FINAL_RESEARCH_PACKAGE/01_MANUSCRIPT"
FIGURE_DIR = WORKSPACE_ROOT / "deliverables/CMIDO_FINAL_RESEARCH_PACKAGE/02_FIGURES"

SOURCE_MD = MANUSCRIPT_DIR / "CMIDO_DRAFT_MANUSCRIPT.md"
OUTPUT_PDF = WORKSPACE_ROOT / "deliverables/CMIDO_FINAL_RESEARCH_PACKAGE/04_PDF/CMIDO_PUBLICATION_MANUSCRIPT_DRAFT_V1.pdf"

FIGURE_FILENAMES: Dict[str, str] = {
    "F1": "F1_RO1_calibration_coverage.png",
    "F2": "F2_RO2_tail_comparison.png",
    "F3": "F3_RO2_propagation_tail.png",
    "F4": "F4_RO2_joint_independent_sensitivity.png",
    "F5": "F5_RO3_controller_descriptives.png",
    "F6": "F6_RO3_ablation_effects.png",
    "F7": "F7_CMIDO_integrated_pipeline.png",
}

FIGURE_CLASSIFICATION: Dict[str, str] = {
    "F1": "RO1 / observational forecast calibration against observed failure counts",
    "F2": "RO2 / tail comparison of propagated frontier vs reference distributions",
    "F3": "RO2 / joint uncertainty propagation tail, service shortfall events",
    "F4": "RO2 / joint vs independent sensitivity illustration",
    "F5": "RO3 / controller ensemble descriptives (means with variabilities)",
    "F6": "RO3 / ablation/robustness sensitivity effects across controllers",
    "F7": "CMIDO integrated pipeline: empirical inputs -> forecasts -> uncertainty -> joint simulation -> optimization -> validation",
}

PW, PH = A4
MARGIN_L = 56
MARGIN_R = PW - 56
TOP_AREA = PH - 56 - 44
BOTTOM = 56
# MARGIN_L / MARGIN_R are x-coordinates, so the usable text width is their
# difference (not PW minus both, which would be zero).
USABLE_WIDTH = MARGIN_R - MARGIN_L

if sys.version_info < (3, 8):
    raise SystemExit("This renderer requires Python 3.8+")


def _bytes(path: pathlib.Path) -> bytes:
    with path.open("rb") as fh:
        return fh.read()


def _rel_root(path: pathlib.Path) -> str:
    """Workspace-relative path for manifests, with an absolute-path fallback."""
    try:
        return str(path.resolve().relative_to(WORKSPACE_ROOT))
    except ValueError:
        return str(path)


def _escape_bracket_text(raw: str) -> str:
    """Escape text with unbalanced PDF brackets so drawString does not break."""

    out: List[str] = []
    for ch in raw:
        if ch == "(":
            out.append("\\(")
        elif ch == ")":
            out.append("\\)")
        elif ch == "\\":
            out.append("\\\\")
        else:
            out.append(ch)
    return "".join(out)


def _clip_to_width(
    c: canvas.Canvas, text: str, font: str, size: float, width: float
) -> str:
    """Longest prefix of `text` that fits `width` when drawn in `font`/`size`."""
    if c.stringWidth(text, font, size) <= width:
        return text
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if c.stringWidth(text[:mid], font, size) <= width:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo]


def _wrap_text(
    c: canvas.Canvas, text: str, font: str, size: float, width: float
) -> List[str]:
    """Wrap text to `width`, hard-splitting tokens that cannot fit on a line."""
    lines: List[str] = []
    line = ""
    for word in text.split():
        while c.stringWidth(word, font, size) > width:
            piece = _clip_to_width(c, word, font, size, width)
            if not piece:  # single glyph wider than the line; make progress
                piece = word[:1]
            if line:
                lines.append(line)
                line = ""
            lines.append(piece)
            word = word[len(piece):]
        trial = f"{line} {word}".strip() if line else word
        if line and c.stringWidth(trial, font, size) > width:
            lines.append(line)
            line = word
        else:
            line = trial
    if line:
        lines.append(line)
    return lines or [""]


def _render_heading(c: canvas.Canvas, text: str, level: int, top: float) -> float:
    sizes = {1: 22, 2: 15, 3: 12}
    size = sizes.get(level, 12)
    c.setFont("Helvetica-Bold", size)
    c.setFillColorRGB(0.12, 0.12, 0.12)
    for line in _wrap_text(c, text.strip(), "Helvetica-Bold", size, USABLE_WIDTH):
        if top < BOTTOM + size + 6:
            top = _new_page(c)
            c.setFont("Helvetica-Bold", size)
            c.setFillColorRGB(0.12, 0.12, 0.12)
        c.drawString(MARGIN_L, top, line)
        top -= (size + 4)
    return top - 3


def _new_page(c: canvas.Canvas) -> float:
    c.showPage()
    return TOP_AREA


def _draw_line(
    c: canvas.Canvas,
    text: str,
    size: float,
    top: float,
    *,
    color: Tuple[float, float, float] = (0, 0, 0),
    indent: float = 0,
) -> float:
    if top < BOTTOM + 18:
        top = _new_page(c)
    c.setFont("Helvetica", size)
    c.setFillColorRGB(*color)
    # reportlab escapes ( ) \ itself; pre-escaping would render visible
    # backslashes. Clip by measured width instead of a fixed character count.
    line = _clip_to_width(c, text, "Helvetica", size, USABLE_WIDTH - indent)
    c.drawString(MARGIN_L + indent, top, line)
    return top - (size + 3)


def _draw_code_block(
    c: canvas.Canvas,
    lines: List[str],
    top: float,
    size: float = 8.2,
) -> float:
    if top < 80:
        top = _new_page(c)
    c.setFont("Courier", size)
    c.setFillColorRGB(0.27, 0.27, 0.27)
    top = _draw_line(c, "[code block]", size, top, color=(0.3, 0.3, 0.3))
    top -= 9
    for raw in lines:
        for piece in _wrap_text(c, raw, "Courier", size, USABLE_WIDTH - 8):
            if top < 48:
                top = _new_page(c)
            top = _draw_line(c, piece, size, top, color=(0.25, 0.25, 0.25), indent=8)
            top -= 3
    top -= 6
    return top


PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _draw_inline_image(
    c: canvas.Canvas,
    image_path: pathlib.Path,
    x: float,
    y: float,
    target_width_pt: float,
    target_height_pt: float,
) -> None:
    """Embed a PNG figure into the page via reportlab's image XObject writer.

    We validate the PNG signature up front so a non-image file cannot slip
    through, then let reportlab handle colourspace, alpha/SMask and Flate
    encoding — that path is exercised by the PDF regression test.
    """

    with image_path.open("rb") as fh:
        magic = fh.read(8)
    if magic != PNG_MAGIC:
        raise ValueError(f"declared figure is not a PNG: {image_path.name}")

    c.drawImage(
        str(image_path),
        x,
        y,
        width=target_width_pt,
        height=target_height_pt,
        mask="auto",
        preserveAspectRatio=True,
    )


def _ensure_image(
    c: canvas.Canvas,
    filename: str,
    top: float,
    *,
    caption: Optional[str] = None,
) -> Tuple[bool, float]:
    path = FIGURE_DIR / filename
    if not path.is_file():
        top = _draw_line(
            c,
            f"[figure file not located: {filename} in {FIGURE_DIR}]",
            9,
            top,
            color=(0.72, 0.04, 0.04),
        )
        return False, top

    try:
        iw, ih = ImageReader(str(path)).getSize()
    except Exception as exc:  # pragma: no cover - defensive
        top = _draw_line(
            c,
            f"[unable to read declared figure {filename}: {exc}]",
            9,
            top,
            color=(0.72, 0.04, 0.04),
        )
        return False, top

    if iw <= 0 or ih <= 0:
        top = _draw_line(
            c,
            f"[declared figure has zero dimensions: {filename}]",
            9,
            top,
            color=(0.72, 0.04, 0.04),
        )
        return False, top

    max_width = USABLE_WIDTH
    figure_width = min(max_width, max(1.25 * inch, (iw / 140.0) * 72))
    figure_height = figure_width * ih / iw
    top -= 2
    if top - figure_height < BOTTOM + 20:
        top = _new_page(c)
    x_off = (PW - figure_width) / 2.0

    if top < figure_height + BOTTOM + 10:
        top = _new_page(c)

    y_bottom = top - figure_height
    _draw_inline_image(
        c,
        path,
        x_off,
        y_bottom,
        figure_width,
        figure_height,
    )

    top -= figure_height + 1
    if caption:
        c.setFont("Helvetica-Oblique", 9)
        c.setFillColorRGB(0.3, 0.3, 0.3)
        for cap_line in _wrap_text(c, caption, "Helvetica-Oblique", 9, USABLE_WIDTH):
            if top < BOTTOM + 12:
                top = _new_page(c)
                c.setFont("Helvetica-Oblique", 9)
                c.setFillColorRGB(0.3, 0.3, 0.3)
            c.drawString(MARGIN_L, top, cap_line)
            top -= 9
    return True, top


def _contains_figure_token(joined: str) -> Tuple[Optional[str], List[str]]:
    joined_l = joined.lower()
    if "figure 1" in joined_l or "f1 " in joined_l:
        return "F1", ["Figure 1"]
    if "figure 2" in joined_l or "f2 " in joined_l:
        return "F2", ["Figure 2"]
    if "figure 3" in joined_l or "f3 " in joined_l:
        return "F3", ["Figure 3"]
    if "figure 4" in joined_l or "f4 " in joined_l:
        return "F4", ["Figure 4"]
    if "figure 5" in joined_l or "f5 " in joined_l:
        return "F5", ["Figure 5"]
    if "figure 6" in joined_l or "f6 " in joined_l:
        return "F6", ["Figure 6"]
    if "figure 7" in joined_l or "f7 " in joined_l:
        return "F7", ["Figure 7"]
    return None, []


def _wrap_paragraph(c: canvas.Canvas, text: str, top: float, size: float = 10.0) -> float:
    for line in _wrap_text(c, text, "Helvetica", size, USABLE_WIDTH):
        top = _draw_line(c, line, size, top)
        top -= 2
    return top


def _render_manifest_footer(c: canvas.Canvas, top: float, manifest: Dict[str, Any]) -> float:
    top = _draw_line(
        c,
        "CMIDO_DRAFT_MANUSCRIPT.pdf — rendered review copy",
        9,
        top,
        color=(0.25, 0.25, 0.25),
    )
    top -= 3
    for row in manifest.get("lines", []):
        top = _draw_line(c, row, 8.2, top, color=(0.45, 0.45, 0.45))
        top -= 2
    return top


def build_pdf(
    source_md: pathlib.Path,
    output_pdf: pathlib.Path,
    figure_dir: pathlib.Path,
    *,
    manifest_overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    if not source_md.is_file():
        raise FileNotFoundError(f"MarkDown source not found: {source_md}")

    md_text = source_md.read_text(encoding="utf-8", errors="replace")
    lines = md_text.splitlines()

    c = canvas.Canvas(str(output_pdf), pagesize=A4, initialFontName="Helvetica")
    c.setTitle("CMIDO Draft Manuscript")
    c.setAuthor("CMIDO research packaging")
    c.setSubject("Stochastic Procurement Optimization Under Supply and Demand Uncertainty")

    top = TOP_AREA
    figure_tokens_used: Dict[str, int] = {}
    failed_images: List[str] = []
    manifest: Dict[str, Any] = {
        "source_md": _rel_root(source_md),
        "output_pdf": _rel_root(output_pdf),
        "figure_dir": _rel_root(figure_dir),
        "figure_classification": FIGURE_CLASSIFICATION,
        "figures_declared_in_script": FIGURE_FILENAMES,
        "figures_referenced_in_manuscript": {},
        "figures_locally_matched": {},
        "figures_missing": [],
    }

    idx = 0
    n = len(lines)

    def _rel(src: pathlib.Path) -> str:
        try:
            return _rel_root(src)
        except ValueError:
            return str(src)

    while idx < n:
        s = lines[idx].strip()

        # fenced code blocks -------------------------------------------------------
        if s.startswith("```"):
            idx += 1
            code_lines: List[str] = []
            while idx < n and not lines[idx].strip().startswith("```"):
                code_lines.append(lines[idx].rstrip())
                idx += 1
            idx += 1
            if code_lines:
                top = _draw_code_block(c, code_lines, top)
            continue

        # headings ----------------------------------------------------------------
        if s.startswith("## "):
            top = _render_heading(c, s[3:].strip(), 2, top)
            idx += 1
            continue
        if s.startswith("# "):
            top = _render_heading(c, s[2:].strip(), 1, top)
            idx += 1
            continue
        if s.startswith("### "):
            top = _render_heading(c, s[4:].strip(), 3, top)
            idx += 1
            continue

        # spacing / list items ----------------------------------------------------
        if s == "":
            idx += 1
            continue

        # blockquotes -------------------------------------------------------------
        if s.startswith("> "):
            c.setFont("Helvetica-Oblique", 9.5)
            c.setFillColorRGB(0.2, 0.2, 0.2)
            for line in _wrap_text(c, s[2:], "Helvetica-Oblique", 9.5, USABLE_WIDTH - 16):
                if top < BOTTOM + 16:
                    top = _new_page(c)
                    c.setFont("Helvetica-Oblique", 9.5)
                    c.setFillColorRGB(0.2, 0.2, 0.2)
                c.drawString(MARGIN_L + 16, top, line)
                top -= 11
            idx += 1
            continue

        if s.startswith("- ") or s.startswith("* "):
            top = _draw_line(c, "- " + s[2:], 10, top, indent=14)
            idx += 1
            continue

        # paragraph / image / figure token ---------------------------------------
        para: List[str] = []
        j = idx
        while (
            j < n
            and lines[j].strip() != ""
            and not lines[j].strip().startswith(("#", ">", "-", "*"))
            and not lines[j].strip().startswith("```")
        ):
            para.append(lines[j].rstrip())
            j += 1

        if not para:
            # Defensive: never spin on a line the block rules skip.
            idx = max(j, idx + 1)
            continue

        joined = " ".join(para)

        # image markdown syntax
        m = re.search(r"^!\[[^\]]*\]\(([^)]+)\)", joined)
        if m:
            _figname = m.group(1).strip()
            caption_text = f"Image {_figname} — see {_rel(figure_dir / _figname)}"
            ok, top = _ensure_image(c, _figname, top, caption=caption_text)
            if not ok:
                failed_images.append(_figname)
            idx = j
            continue

        # explicit figure reference
        hit, labels = _contains_figure_token(joined)
        if hit:
            top = _wrap_paragraph(c, joined, top)
            top -= 2
            classification = FIGURE_CLASSIFICATION.get(hit, "(unclassified)")
            caption = f"Figure {hit[1:]} — {classification}"
            filename = FIGURE_FILENAMES.get(hit, f"{hit}.png")
            was_embedded, top = _ensure_image(c, filename, top, caption=caption)
            if not was_embedded:
                failed_images.append(filename)
            manifest["figures_referenced_in_manuscript"][hit] = labels
            figure_tokens_used[hit] = figure_tokens_used.get(hit, 0) + 1
            manifest["figures_locally_matched"][hit] = filename
            idx = j
            continue

        # figure referenced by filename (backticked path or bare filename) ------
        mentioned = [
            fname for fname in FIGURE_FILENAMES.values() if fname in joined
        ]
        if mentioned:
            top = _wrap_paragraph(c, joined, top)
            for fname in mentioned:
                fid = next(
                    (k for k, v in FIGURE_FILENAMES.items() if v == fname), fname
                )
                classification = FIGURE_CLASSIFICATION.get(fid, "(unclassified)")
                caption = f"Figure {fid[1:]} — {classification}"
                was_embedded, top = _ensure_image(c, fname, top, caption=caption)
                if not was_embedded:
                    failed_images.append(fname)
                figure_tokens_used[fid] = figure_tokens_used.get(fid, 0) + 1
                manifest["figures_locally_matched"][fid] = fname
            idx = j
            continue

        # ordinary body paragraph -------------------------------------------------
        top = _wrap_paragraph(c, joined, top)
        idx = j

    # close final page with a short manifest footer
    top = _render_manifest_footer(c, top, manifest)
    c.showPage()
    c.save()

    manifest["figures_referenced_in_manuscript"] = {
        k: v for k, v in figure_tokens_used.items() if v > 0
    }
    manifest["figures_locally_matched"] = {
        k: manifest["figures_locally_matched"][k]
        for k in figure_tokens_used
    }
    manifest["figures_missing"] = failed_images or []
    manifest["sha256"] = hashlib.sha256(_bytes(output_pdf)).hexdigest()
    manifest["bytes"] = output_pdf.stat().st_size
    manifest["pages_estimate"] = _pages_estimate(output_pdf)
    if manifest_overrides:
        manifest.update(manifest_overrides)

    return manifest


def _pages_estimate(pdf: pathlib.Path) -> int:
    try:
        import pymupdf  # type: ignore

        return pymupdf.open(str(pdf)).page_count
    except Exception:
        pass
    try:
        import pypdf  # type: ignore

        return len(pypdf.PdfReader(str(pdf)).pages)
    except Exception:
        return -1


def main() -> int:
    if not SOURCE_MD.is_file():
        print(f"missing source: {SOURCE_MD}")
        return 1
    if not figure_dir_is_usable(FIGURE_DIR):
        print(f"missing required figure directory: {FIGURE_DIR}")
        return 1

    pathlib.Path(OUTPUT_PDF).parent.mkdir(parents=True, exist_ok=True)
    manifest = build_pdf(SOURCE_MD, OUTPUT_PDF, FIGURE_DIR)
    print("PDF written:", OUTPUT_PDF)
    print("bytes:", manifest["bytes"])
    print("SHA256:", manifest["sha256"])
    print("estimated pages:", manifest["pages_estimate"])
    print("figure tokens matched in manuscript:", manifest["figures_referenced_in_manuscript"])
    print("figures matched to local files:", manifest["figures_locally_matched"])
    if manifest["figures_missing"]:
        print("WARNING missing figures:", manifest["figures_missing"])
    return 0


def figure_dir_is_usable(figure_dir: pathlib.Path) -> bool:
    if not figure_dir.is_dir():
        return False
    try:
        names = {entry.name for entry in figure_dir.iterdir()}
        return all(fname in names for fname in FIGURE_FILENAMES.values())
    except OSError:
        return False


def _verify_embedded_images(pdf: pathlib.Path) -> Dict[str, Any]:
    """Report embedded image XObjects using pymupdf when available.

    Falls back to a raw-stream scan of the PDF so this still works without
    pymupdf, but the pymupdf path is what the regression test relies on.
    """
    try:
        import pymupdf  # type: ignore

        doc = pymupdf.open(str(pdf))
        widths: List[int] = []
        heights: List[int] = []
        for page in doc:
            for img in page.get_images(full=True):
                widths.append(img[2])
                heights.append(img[3])
        doc.close()
        return {
            "image_objects_found": len(widths),
            "image_widths": widths,
            "image_heights": heights,
            "reader": "pymupdf",
        }
    except Exception:
        pass

    raw = _bytes(pdf)
    widths = [int(m) for m in re.findall(rb"/Subtype\s*/Image[^>]*?/Width\s+(\d+)", raw)]
    # width/height pairs are not reliably ordered in a raw scan; just count objects
    count = len(re.findall(rb"/Subtype\s*/Image", raw))
    return {
        "image_objects_found": count,
        "image_widths": widths,
        "image_heights": [],
        "reader": "raw-scan",
    }


def verify_pdf(pdf: pathlib.Path) -> Dict[str, Any]:
    """Inspect the built PDF: page count, extracted text and embedded images.

    Uses pymupdf when available; otherwise falls back to pypdf. Markers below
    are terms that are actually present in the manuscript source, so this is a
    meaningful regression check rather than an aspirational one.
    """
    text = ""
    pages = -1
    reader = None
    try:
        import pymupdf  # type: ignore

        reader = "pymupdf"
        doc = pymupdf.open(str(pdf))
        pages = doc.page_count
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
    except Exception:
        try:
            import pypdf  # type: ignore

            reader = "pypdf"
            r = pypdf.PdfReader(str(pdf))
            pages = len(r.pages)
            text = "\n".join((p.extract_text() or "") for p in r.pages)
        except Exception:
            reader = None

    raw = _bytes(pdf)
    image_check = _verify_embedded_images(pdf)

    markers = [
        "CMIDO",
        "Abstract",
        "Introduction",
        "References",
        "quantile",
        "Figure 1",
        "Figure 6",
        "Table",
        "uncertainty",
        "procurement",
    ]
    return {
        "file": str(pdf),
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "text_reader": reader,
        "pages": pages,
        "image_objects": image_check["image_objects_found"],
        "image_widths": image_check["image_widths"],
        "image_heights": image_check["image_heights"],
        "image_reader": image_check.get("reader"),
        "text_length": len(text),
        "text_presence_markers": {
            marker: marker.lower() in text.lower() for marker in markers
        },
    }


if __name__ == "__main__":
    raise SystemExit(main())
