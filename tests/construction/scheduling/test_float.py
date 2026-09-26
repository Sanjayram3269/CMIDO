import json

from src.construction.scheduling.float import (
    calculate_total_float,
)


def load_project():
    with open(
        "data/projects/cmido_demo_project.json",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def test_float_is_calculated_for_all_activities():
    project = load_project()

    results = calculate_total_float(project)

    assert len(results) == 11

    for result in results:
        assert "total_float" in result


def test_float_formula_ls_minus_es():
    project = load_project()

    results = calculate_total_float(project)

    for result in results:
        expected = result["ls"] - result["es"]

        assert result["total_float"] == expected


def test_float_formula_lf_minus_ef():
    project = load_project()

    results = calculate_total_float(project)

    for result in results:
        expected = result["lf"] - result["ef"]

        assert result["total_float"] == expected


def test_expected_zero_float_activities():
    project = load_project()

    results = calculate_total_float(project)

    by_id = {
        result["activity_id"]: result
        for result in results
    }

    expected_zero_float = [
        "A001",
        "A002",
        "A003",
        "A004",
        "A006",
        "A007",
        "A008",
        "A009",
        "A011",
    ]

    for activity_id in expected_zero_float:
        assert by_id[activity_id]["total_float"] == 0


def test_expected_nonzero_float_activities():
    project = load_project()

    results = calculate_total_float(project)

    by_id = {
        result["activity_id"]: result
        for result in results
    }

    assert by_id["A005"]["total_float"] == 2
    assert by_id["A010"]["total_float"] == 1


def test_float_is_never_negative():
    project = load_project()

    results = calculate_total_float(project)

    for result in results:
        assert result["total_float"] >= 0