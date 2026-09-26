from __future__ import annotations

from collections import Counter
from typing import Any


def validate_project_structure(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    required_sections = [
        "project",
        "calendar",
        "activities",
        "dependencies",
        "materials",
        "activity_materials",
        "suppliers",
        "supplier_materials",
    ]

    for section in required_sections:
        if section not in data:
            errors.append(f"Missing required section: {section}")

    if errors:
        return errors

    project_id = data["project"]["project_id"]

    # ---------------------------------------------------------
    # Activity validation
    # ---------------------------------------------------------
    activities = data["activities"]

    activity_ids = [activity["activity_id"] for activity in activities]

    duplicates = [
        activity_id
        for activity_id, count in Counter(activity_ids).items()
        if count > 1
    ]

    for activity_id in duplicates:
        errors.append(f"Duplicate activity ID: {activity_id}")

    for activity in activities:
        if activity["project_id"] != project_id:
            errors.append(
                f"Activity {activity['activity_id']} belongs "
                f"to another project"
            )

    activity_id_set = set(activity_ids)

    # ---------------------------------------------------------
    # Dependency validation
    # ---------------------------------------------------------
    dependencies = data["dependencies"]

    dependency_ids = [
        dependency["dependency_id"]
        for dependency in dependencies
    ]

    duplicates = [
        dependency_id
        for dependency_id, count in Counter(dependency_ids).items()
        if count > 1
    ]

    for dependency_id in duplicates:
        errors.append(f"Duplicate dependency ID: {dependency_id}")

    for dependency in dependencies:
        if dependency["project_id"] != project_id:
            errors.append(
                f"Dependency {dependency['dependency_id']} "
                f"belongs to another project"
            )

        predecessor = dependency["predecessor_id"]
        successor = dependency["successor_id"]

        if predecessor not in activity_id_set:
            errors.append(
                f"Dependency {dependency['dependency_id']} references "
                f"unknown predecessor: {predecessor}"
            )

        if successor not in activity_id_set:
            errors.append(
                f"Dependency {dependency['dependency_id']} references "
                f"unknown successor: {successor}"
            )

    # ---------------------------------------------------------
    # Material validation
    # ---------------------------------------------------------
    materials = data["materials"]

    material_ids = [material["material_id"] for material in materials]

    duplicates = [
        material_id
        for material_id, count in Counter(material_ids).items()
        if count > 1
    ]

    for material_id in duplicates:
        errors.append(f"Duplicate material ID: {material_id}")

    material_id_set = set(material_ids)

    # ---------------------------------------------------------
    # Activity-material validation
    # ---------------------------------------------------------
    for mapping in data["activity_materials"]:
        activity_id = mapping["activity_id"]
        material_id = mapping["material_id"]

        if activity_id not in activity_id_set:
            errors.append(
                f"Activity-material mapping references "
                f"unknown activity: {activity_id}"
            )

        if material_id not in material_id_set:
            errors.append(
                f"Activity-material mapping references "
                f"unknown material: {material_id}"
            )

        if mapping["quantity_required"] < 0:
            errors.append(
                f"Negative material quantity for "
                f"{activity_id} -> {material_id}"
            )

    # ---------------------------------------------------------
    # Supplier validation
    # ---------------------------------------------------------
    suppliers = data["suppliers"]

    supplier_ids = [
        supplier["supplier_id"]
        for supplier in suppliers
    ]

    duplicates = [
        supplier_id
        for supplier_id, count in Counter(supplier_ids).items()
        if count > 1
    ]

    for supplier_id in duplicates:
        errors.append(f"Duplicate supplier ID: {supplier_id}")

    supplier_id_set = set(supplier_ids)

    # ---------------------------------------------------------
    # Supplier-material validation
    # ---------------------------------------------------------
    for mapping in data["supplier_materials"]:
        supplier_id = mapping["supplier_id"]
        material_id = mapping["material_id"]

        if supplier_id not in supplier_id_set:
            errors.append(
                f"Supplier-material mapping references "
                f"unknown supplier: {supplier_id}"
            )

        if material_id not in material_id_set:
            errors.append(
                f"Supplier-material mapping references "
                f"unknown material: {material_id}"
            )

    return errors


def validate_project(data: dict[str, Any]) -> None:
    errors = validate_project_structure(data)

    if errors:
        message = "\n".join(f"- {error}" for error in errors)
        raise ValueError(
            f"CMIDO project validation failed:\n{message}"
        )
