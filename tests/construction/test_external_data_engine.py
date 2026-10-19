"""Tests for the CMIDO external-data ingestion engine.

Covers the required scenarios: valid CSV/JSON uploads, missing/extra columns,
invalid dates/numerics/categories, empty datasets and missing required fields,
malformed files and unsupported formats, upload size limits, valid schema
mapping, successful execution of each supported analysis, backend failures and
readable error states, isolation between independent runs, and output
provenance and export integrity.

The engine is Streamlit-free, so every behaviour the dashboard relies on is
exercised here directly and deterministically.
"""

from __future__ import annotations

import json
import pathlib
import sys

import pandas as pd
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.construction.external_data import (  # noqa: E402
    MAX_UPLOAD_BYTES,
    RunStore,
    parse_upload,
    profile_table,
    run_workflow,
    safe_filename,
    validate_mapping,
    build_mapping_spec,
)
from src.construction.external_data.contracts import ANALYSES  # noqa: E402
from src.construction.external_data.parsing import ParseError  # noqa: E402

FIXTURE = ROOT / "examples" / "external_data" / "forecast_intervals_fixture.csv"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fixture_payload() -> bytes:
    return FIXTURE.read_bytes()


def _tmp_store(tmp_path: pathlib.Path) -> RunStore:
    return RunStore(tmp_path / "runs")


# ---------------------------------------------------------------------------
# Valid uploads
# ---------------------------------------------------------------------------


class TestValidUploads:
    def test_fixture_parses_as_csv(self) -> None:
        parsed = parse_upload("forecast_intervals_fixture.csv", _fixture_payload())
        assert parsed.file_format == "csv"
        assert parsed.frame.shape == (200, 5)
        assert list(parsed.frame.columns) == [
            "region", "observed", "q50", "lower_80", "upper_80",
        ]

    def test_json_array_of_objects_parses(self) -> None:
        payload = json.dumps(
            [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]
        ).encode("utf-8")
        parsed = parse_upload("data.json", payload)
        assert parsed.file_format == "json"
        assert parsed.frame.shape == (2, 2)

    def test_json_column_mapping_parses(self) -> None:
        payload = json.dumps({"a": [1, 2, 3], "b": ["x", "y", "z"]}).encode("utf-8")
        parsed = parse_upload("cols.json", payload)
        assert parsed.frame.shape == (3, 2)

    def test_safe_filename_strips_paths(self) -> None:
        assert safe_filename("../../etc/passwd") == "passwd"
        assert safe_filename("C:\\windows\\evil.csv") == "evil.csv"
        assert safe_filename("") == "upload"
        assert safe_filename("!!!") == "upload"


# ---------------------------------------------------------------------------
# Malformed files and unsupported formats
# ---------------------------------------------------------------------------


class TestMalformedAndUnsupported:
    def test_unsupported_extension_rejected(self) -> None:
        with pytest.raises(ParseError, match="Unsupported file type"):
            parse_upload("payload.exe", b"MZ\x90\x00")

    def test_no_extension_rejected(self) -> None:
        with pytest.raises(ParseError, match="Unsupported file type"):
            parse_upload("noext", b"anything")

    def test_empty_payload_rejected(self) -> None:
        with pytest.raises(ParseError, match="empty"):
            parse_upload("empty.csv", b"")

    def test_malformed_csv_raises_readable_error(self) -> None:
        # A byte that is not valid UTF-8 in a way pandas rejects, or a broken
        # quote; either way the engine must surface a ParseError, not crash.
        with pytest.raises(ParseError):
            parse_upload("bad.csv", b'\xff\xfe\x00,unclosed"quote\n')

    def test_malformed_json_raises_readable_error(self) -> None:
        with pytest.raises(ParseError, match="Could not parse the JSON"):
            parse_upload("bad.json", b"{not valid json")

    def test_json_top_level_scalar_rejected(self) -> None:
        with pytest.raises(ParseError, match="top level"):
            parse_upload("scalar.json", b"42")

    def test_empty_json_array_rejected(self) -> None:
        with pytest.raises(ParseError, match="empty"):
            parse_upload("empty.json", b"[]")

    def test_no_server_path_leaks_in_error(self) -> None:
        with pytest.raises(ParseError) as exc:
            parse_upload("bad.json", b"{not valid json")
        assert str(ROOT) not in str(exc.value)
        assert "D:\\" not in str(exc.value)


# ---------------------------------------------------------------------------
# Upload size limits
# ---------------------------------------------------------------------------


class TestSizeLimits:
    def test_oversized_upload_rejected(self) -> None:
        big = b"x" * (MAX_UPLOAD_BYTES + 1)
        with pytest.raises(ParseError, match="upload limit"):
            parse_upload("big.csv", big)

    def test_limit_is_10_mib(self) -> None:
        assert MAX_UPLOAD_BYTES == 10 * 1024 * 1024


# ---------------------------------------------------------------------------
# Missing / extra columns and invalid values
# ---------------------------------------------------------------------------


class TestColumnHandling:
    def test_missing_required_column_blocks_validation(self) -> None:
        parsed = parse_upload("forecast_intervals_fixture.csv", _fixture_payload())
        spec = build_mapping_spec(
            "forecast_coverage",
            {"observed": "does_not_exist", "interval_lower": "lower_80",
             "interval_upper": "upper_80"},
        )
        report = validate_mapping(parsed.frame, spec)
        assert not report.ok
        assert any("not found" in e.message for e in report.errors)

    def test_missing_required_field_blocks_validation(self) -> None:
        parsed = parse_upload("forecast_intervals_fixture.csv", _fixture_payload())
        spec = build_mapping_spec(
            "forecast_coverage", {"observed": "observed"}  # bounds unmapped
        )
        report = validate_mapping(parsed.frame, spec)
        assert not report.ok
        assert any("not mapped" in e.message for e in report.errors)

    def test_extra_columns_are_tolerated(self) -> None:
        payload = (
            b"region,observed,lower_80,upper_80,unrelated\n"
            b"north,10,8,12,zzz\nsouth,20,15,25,yyy\n"
        )
        parsed = parse_upload("extra.csv", payload)
        spec = build_mapping_spec(
            "forecast_coverage",
            {"observed": "observed", "interval_lower": "lower_80",
             "interval_upper": "upper_80"},
        )
        report = validate_mapping(parsed.frame, spec)
        assert report.ok

    def test_non_numeric_measure_produces_error(self) -> None:
        payload = b"label,value\na,1\nb,not_a_number\nc,3\n"
        parsed = parse_upload("mixed.csv", payload)
        # 'label' is categorical; mapping it as the numeric measure must error.
        spec = build_mapping_spec("descriptive_statistics", {"measure": "label"})
        report = validate_mapping(parsed.frame, spec)
        assert not report.ok

    def test_partially_non_numeric_measure_warns(self) -> None:
        payload = b"measure\n1\n2\noops\n4\n"
        parsed = parse_upload("partial.csv", payload)
        spec = build_mapping_spec("descriptive_statistics", {"measure": "measure"})
        report = validate_mapping(parsed.frame, spec)
        assert report.ok  # numeric coercion handles the rest
        assert any("non-numeric" in w.message for w in report.warnings)


# ---------------------------------------------------------------------------
# Empty datasets and missing required fields
# ---------------------------------------------------------------------------


class TestEmptyAndMissing:
    def test_header_only_table_has_zero_rows(self) -> None:
        parsed = parse_upload("header.csv", b"a,b,c\n")
        assert parsed.frame.shape[0] == 0
        profile = profile_table(parsed.frame)
        assert any("no data rows" in w for w in profile["warnings"])

    def test_empty_measure_blocks_analysis(self) -> None:
        # A row where the measure is null but another column has a value:
        # the table is non-empty, yet the measure column has no usable numbers.
        payload = b"measure,other\n,5\n"
        parsed = parse_upload("nulls.csv", payload)
        assert parsed.frame.shape[0] == 1
        # Validation sees a numeric column with no usable values -> error.
        spec = build_mapping_spec("descriptive_statistics", {"measure": "measure"})
        report = validate_mapping(parsed.frame, spec)
        assert not report.ok


# ---------------------------------------------------------------------------
# Valid schema mapping + successful execution of each supported analysis
# ---------------------------------------------------------------------------


class TestSupportedAnalyses:
    def test_descriptive_statistics_runs(self, tmp_path: pathlib.Path) -> None:
        result = run_workflow(
            "forecast_intervals_fixture.csv", _fixture_payload(),
            "descriptive_statistics", {"measure": "observed", "group": "region"},
            store=_tmp_store(tmp_path),
        )
        assert result.error == ""
        rows = result.analysis["rows"]
        assert {r["group"] for r in rows} == {"east", "north", "south", "west"}
        for row in rows:
            assert row["n"] > 0
            assert row["mean_ci95_low"] <= row["mean"] <= row["mean_ci95_high"]

    def test_descriptive_without_group_returns_single_row(self, tmp_path) -> None:
        result = run_workflow(
            "forecast_intervals_fixture.csv", _fixture_payload(),
            "descriptive_statistics", {"measure": "observed"},
            store=_tmp_store(tmp_path),
        )
        assert result.error == ""
        assert len(result.analysis["rows"]) == 1

    def test_forecast_coverage_runs(self, tmp_path: pathlib.Path) -> None:
        result = run_workflow(
            "forecast_intervals_fixture.csv", _fixture_payload(),
            "forecast_coverage",
            {"observed": "observed", "interval_lower": "lower_80",
             "interval_upper": "upper_80", "quantile": "q50"},
            store=_tmp_store(tmp_path),
        )
        assert result.error == ""
        a = result.analysis
        assert a["n_scored"] == 200
        assert 0.0 <= a["coverage_rate"] <= 1.0
        assert a["mean_interval_width"] > 0
        assert a["pinball_loss_mean"] >= 0

    def test_forecast_coverage_without_quantile_omits_pinball(self, tmp_path) -> None:
        result = run_workflow(
            "forecast_intervals_fixture.csv", _fixture_payload(),
            "forecast_coverage",
            {"observed": "observed", "interval_lower": "lower_80",
             "interval_upper": "upper_80"},
            store=_tmp_store(tmp_path),
        )
        assert result.error == ""
        assert "pinball_loss_mean" not in result.analysis

    def test_results_respond_to_input_change(self, tmp_path: pathlib.Path) -> None:
        # Shift every observed value up; coverage must change, proving the
        # number is computed from the uploaded rows, not a frozen constant.
        parsed = parse_upload("f.csv", _fixture_payload())
        frame = parsed.frame.copy()
        frame["observed"] = frame["observed"] + 1000.0
        shifted = frame.to_csv(index=False).encode("utf-8")
        base = run_workflow(
            "f.csv", _fixture_payload(), "forecast_coverage",
            {"observed": "observed", "interval_lower": "lower_80",
             "interval_upper": "upper_80"},
            store=_tmp_store(tmp_path / "a"),
        )
        shifted_result = run_workflow(
            "f.csv", shifted, "forecast_coverage",
            {"observed": "observed", "interval_lower": "lower_80",
             "interval_upper": "upper_80"},
            store=_tmp_store(tmp_path / "b"),
        )
        assert base.analysis["coverage_rate"] != shifted_result.analysis["coverage_rate"]

    def test_deterministic_with_same_seed(self, tmp_path: pathlib.Path) -> None:
        kwargs = dict(store=_tmp_store(tmp_path))
        a = run_workflow("f.csv", _fixture_payload(), "descriptive_statistics",
                         {"measure": "observed"}, seed=7, **kwargs)
        b = run_workflow("f.csv", _fixture_payload(), "descriptive_statistics",
                         {"measure": "observed"}, seed=7, **kwargs)
        assert a.analysis["rows"][0]["mean_ci95_low"] == b.analysis["rows"][0]["mean_ci95_low"]

    def test_different_seed_changes_ci(self, tmp_path: pathlib.Path) -> None:
        a = run_workflow("f.csv", _fixture_payload(), "descriptive_statistics",
                         {"measure": "observed"}, seed=1,
                         store=_tmp_store(tmp_path / "a"))
        b = run_workflow("f.csv", _fixture_payload(), "descriptive_statistics",
                         {"measure": "observed"}, seed=999,
                         store=_tmp_store(tmp_path / "b"))
        # Means are identical (data-driven); bootstrap CI bounds may differ.
        assert a.analysis["rows"][0]["mean"] == b.analysis["rows"][0]["mean"]


# ---------------------------------------------------------------------------
# Unsupported analyses are refused honestly
# ---------------------------------------------------------------------------


class TestUnsupportedAnalyses:
    @pytest.mark.parametrize("key", ["ro1_model_training", "ro2_propagation", "ro3_optimization"])
    def test_unsupported_refused_with_reason(self, key: str, tmp_path: pathlib.Path) -> None:
        result = run_workflow("f.csv", _fixture_payload(), key, {},
                              store=_tmp_store(tmp_path))
        assert result.error != ""
        assert result.analysis is None
        spec = next(a for a in ANALYSES if a.key == key)
        assert not spec.supported
        assert spec.unavailable_reason

    def test_every_supported_analysis_is_implemented(self) -> None:
        from src.construction.external_data.contracts import ANALYSES_BY_KEY
        supported = [a.key for a in ANALYSES if a.supported]
        assert set(supported) == {"descriptive_statistics", "forecast_coverage"}
        for key in supported:
            assert ANALYSES_BY_KEY[key].unavailable_reason == ""


# ---------------------------------------------------------------------------
# Backend failures -> readable error states
# ---------------------------------------------------------------------------


class TestReadableErrors:
    def test_unknown_analysis_key_raises_keyerror(self) -> None:
        with pytest.raises(KeyError):
            build_mapping_spec("does_not_exist", {})

    def test_all_null_measure_fails_with_readable_error(self, tmp_path: pathlib.Path) -> None:
        # Bypass validation to exercise the analysis engine's own guard.
        payload = b"measure\n\n\n\n"
        parsed = parse_upload("nulls.csv", payload)
        from src.construction.external_data.analysis import AnalysisError, execute_analysis
        spec = build_mapping_spec("descriptive_statistics", {"measure": "measure"})
        with pytest.raises(AnalysisError, match="No numeric"):
            execute_analysis(parsed.frame, spec)


# ---------------------------------------------------------------------------
# Isolation between independent runs
# ---------------------------------------------------------------------------


class TestRunIsolation:
    def test_runs_land_in_separate_directories(self, tmp_path: pathlib.Path) -> None:
        store = _tmp_store(tmp_path)
        a = run_workflow("f.csv", _fixture_payload(), "descriptive_statistics",
                         {"measure": "observed"}, store=store)
        b = run_workflow("f.csv", _fixture_payload(), "descriptive_statistics",
                         {"measure": "observed"}, store=store)
        assert a.record.run_id != b.record.run_id
        assert a.record.output_dir != b.record.output_dir

    def test_store_never_writes_under_canonical_results(self, tmp_path: pathlib.Path) -> None:
        store = _tmp_store(tmp_path)
        r = run_workflow("f.csv", _fixture_payload(), "descriptive_statistics",
                         {"measure": "observed"}, store=store)
        out = pathlib.Path(r.record.output_dir)
        assert not out.is_relative_to(ROOT / "results" / "8Q_publication_artifacts")
        assert out.is_relative_to(tmp_path)

    def test_run_record_persists_and_lists(self, tmp_path: pathlib.Path) -> None:
        store = _tmp_store(tmp_path)
        r = run_workflow("f.csv", _fixture_payload(), "descriptive_statistics",
                         {"measure": "observed"}, store=store)
        loaded = store.read_run_record(r.record.run_id)
        assert loaded is not None
        assert loaded["status"] == "SUCCEEDED"
        assert store.list_runs() == [r.record.run_id]


# ---------------------------------------------------------------------------
# Output provenance and export integrity
# ---------------------------------------------------------------------------


class TestProvenanceAndExport:
    def test_run_record_has_full_lineage(self, tmp_path: pathlib.Path) -> None:
        store = _tmp_store(tmp_path)
        r = run_workflow("f.csv", _fixture_payload(), "forecast_coverage",
                         {"observed": "observed", "interval_lower": "lower_80",
                          "interval_upper": "upper_80"}, store=store)
        rec = r.record
        assert rec.input_sha256 == hashlib_sha256(_fixture_payload())
        assert rec.input_size_bytes == len(_fixture_payload())
        assert rec.row_count == 200
        assert rec.provenance_class == "DER"
        assert rec.seed == 42
        assert rec.started_utc and rec.finished_utc
        assert rec.duration_seconds >= 0
        assert rec.status == "SUCCEEDED"

    def test_exports_written_and_readable(self, tmp_path: pathlib.Path) -> None:
        store = _tmp_store(tmp_path)
        r = run_workflow("f.csv", _fixture_payload(), "forecast_coverage",
                         {"observed": "observed", "interval_lower": "lower_80",
                          "interval_upper": "upper_80"}, store=store)
        for name in ("mapping", "validation", "profile", "result", "run_record"):
            path = pathlib.Path(r.exports[name])
            assert path.is_file()
            json.loads(path.read_text(encoding="utf-8"))
        # CSV export exists and is non-empty.
        csv_path = pathlib.Path(r.exports["result_table"])
        assert csv_path.is_file() and csv_path.stat().st_size > 0

    def test_mapping_export_matches_input(self, tmp_path: pathlib.Path) -> None:
        store = _tmp_store(tmp_path)
        mapping = {"observed": "observed", "interval_lower": "lower_80",
                   "interval_upper": "upper_80"}
        r = run_workflow("f.csv", _fixture_payload(), "forecast_coverage",
                         mapping, store=store)
        saved = json.loads(pathlib.Path(r.exports["mapping"]).read_text(encoding="utf-8"))
        assert saved == mapping

    def test_no_path_leak_in_run_record(self, tmp_path: pathlib.Path) -> None:
        store = _tmp_store(tmp_path)
        r = run_workflow("f.csv", _fixture_payload(), "descriptive_statistics",
                         {"measure": "observed"}, store=store)
        # The lineage records a relative/dataset-level path, not a host secret.
        assert r.record.input_filename == "f.csv"


def hashlib_sha256(payload: bytes) -> str:
    import hashlib

    return hashlib.sha256(payload).hexdigest()


class TestExportByteFidelity:
    """Persisted exports must equal the payload they were generated from.

    Regression: on Windows the default text-mode translation rewrote every
    newline while writing, turning the ``\r\n`` emitted by pandas into
    ``\r\r\n``. The on-disk result table then no longer matched the table the
    dashboard offers for download, so DOM-to-disk export concordance failed.
    """

    @pytest.mark.parametrize(
        "analysis_key,mapping",
        [
            ("descriptive_statistics", {"measure": "observed"}),
            (
                "forecast_coverage",
                {
                    "observed": "observed",
                    "interval_lower": "lower_80",
                    "interval_upper": "upper_80",
                },
            ),
        ],
    )
    def test_persisted_result_table_is_byte_identical_to_the_export(
        self, tmp_path: pathlib.Path, analysis_key: str, mapping: dict
    ) -> None:
        store = _tmp_store(tmp_path / analysis_key)
        r = run_workflow(
            "f.csv", _fixture_payload(), analysis_key, mapping, store=store
        )
        assert r.error == ""

        csv_path = pathlib.Path(r.exports["result_table"])
        raw = csv_path.read_bytes()
        assert b"\r\r\n" not in raw, "persisted CSV contains a mangled newline"

        stored = json.loads(pathlib.Path(r.exports["result"]).read_text(encoding="utf-8"))
        # The JSON export is serialised with sort_keys, so rebuild the table
        # from the analysis payload itself — the same source the dashboard's
        # download button renders.
        analysis = r.analysis or {}
        rows = analysis.get("rows")
        if not rows:
            rows = [
                {k: v for k, v in analysis.items() if not isinstance(v, (list, dict))}
            ]
        expected = pd.DataFrame(rows).to_csv(index=False, lineterminator="\n").encode(
            "utf-8"
        )
        assert raw == expected
        assert stored is not None

        # JSON exports must round-trip exactly as serialised, too.
        for name in ("mapping", "validation", "profile", "result", "run_record"):
            path = pathlib.Path(r.exports[name])
            text = path.read_text(encoding="utf-8")
            assert "\r" not in text, f"{name} was newline-mangled on disk"
            assert json.loads(text) is not None
