import json

from src.construction.scheduling.graph import (
    build_predecessor_map,
    build_successor_map,
)


def load_project():
    with open(
        "data/projects/cmido_demo_project.json",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def test_predecessor_map_contains_all_activities():
    project = load_project()

    predecessors = build_predecessor_map(project)

    assert len(predecessors) == 11


def test_successor_map_contains_all_activities():
    project = load_project()

    successors = build_successor_map(project)

    assert len(successors) == 11


def test_first_activity_has_no_predecessor():
    project = load_project()

    predecessors = build_predecessor_map(project)

    root_activities = [
        activity_id
        for activity_id, preds in predecessors.items()
        if not preds
    ]

    assert len(root_activities) >= 1


def test_dependency_count_is_preserved():
    project = load_project()

    predecessors = build_predecessor_map(project)

    total_dependencies = sum(
        len(preds)
        for preds in predecessors.values()
    )

    assert total_dependencies == 12