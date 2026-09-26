import json

from src.construction.scheduling.classification import (
    classify_activities,
)


def load_project():
    with open(
        "data/projects/cmido_demo_project.json",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def test_classification_contains_all_activities():
    project = load_project()

    results = classify_activities(project)

    assert len(results) == 11


def test_zero_float_is_critical():
    project = load_project()

    results = classify_activities(project)

    by_id = {
        item["activity_id"]: item
        for item in results
    }

    assert by_id["A001"]["classification"] == "CRITICAL"
    assert by_id["A004"]["classification"] == "CRITICAL"
    assert by_id["A011"]["classification"] == "CRITICAL"


def test_positive_float_is_non_critical():
    project = load_project()

    results = classify_activities(project)

    by_id = {
        item["activity_id"]: item
        for item in results
    }

    assert by_id["A005"]["classification"] == "NON_CRITICAL"
    assert by_id["A010"]["classification"] == "NON_CRITICAL"


def test_classification_matches_float():
    project = load_project()

    results = classify_activities(project)

    for item in results:
        if item["total_float"] == 0:
            assert item["classification"] == "CRITICAL"
        else:
            assert item["classification"] == "NON_CRITICAL"