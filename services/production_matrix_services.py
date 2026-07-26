from apps.production.models import ProductionTask, Scene, ScriptVersion
from apps.projects.models import Department


def get_production_planning_matrix(*, project, filters: dict = None) -> dict:
    """
    Computes scene-by-department production planning matrix and big-picture stats.
    Efficient single-pass query to avoid N+1 per cell.
    """
    filters = filters or {}

    scenes = list(Scene.objects.filter(sequence__act__project=project).order_by("scene_number"))
    departments = list(project.departments.all().order_by("name"))

    tasks_qs = ProductionTask.objects.filter(project=project).select_related(
        "scene",
    ).prefetch_related(
        "packet_sections__department",
        "canonical_selections",
        "submissions__versions",
        "character_links__character",
        "script_links",
    )

    # Filter application
    if filters.get("scene_id"):
        tasks_qs = tasks_qs.filter(scene_id=filters["scene_id"])
    if filters.get("department_id"):
        tasks_qs = tasks_qs.filter(packet_sections__department_id=filters["department_id"])
    if filters.get("task_type"):
        tasks_qs = tasks_qs.filter(task_type=filters["task_type"])
    if filters.get("status"):
        tasks_qs = tasks_qs.filter(status=filters["status"])
    if filters.get("character_id"):
        tasks_qs = tasks_qs.filter(character_links__character_id=filters["character_id"])

    tasks = list(tasks_qs.distinct())

    cell_map = {}
    for t in tasks:
        scene_id = t.scene_id
        for ps in t.packet_sections.all():
            dept_id = ps.department_id
            cell_map.setdefault((scene_id, dept_id), []).append(t)

    def get_cell_highest_status(tasks_list):
        if not tasks_list:
            return "unplanned"
        statuses = [t.status for t in tasks_list]

        # Check for accepted canonical selection
        if any(t.active_canonical_selection() for t in tasks_list):
            return "accepted"
        if any(s == "satisfied" for s in statuses):
            return "accepted"
        if any(t.submissions.filter(status="revision_requested").exists() for t in tasks_list):
            return "revision_requested"
        if any(t.submissions.filter(status="in_review").exists() for t in tasks_list):
            return "under_review"
        if "open" in statuses:
            return "open"
        if "ready" in statuses:
            return "ready"
        return "draft"

    matrix_rows = []
    total_scenes = len(scenes)
    fully_planned_scenes = 0
    partially_planned_scenes = 0
    unplanned_scenes = 0

    duplicate_warnings = []

    for scene in scenes:
        row_cells = []
        scene_task_count = 0
        scene_depts_planned = set()

        for dept in departments:
            cell_tasks = cell_map.get((scene.id, dept.id), [])
            cell_status = get_cell_highest_status(cell_tasks)

            if cell_tasks:
                scene_task_count += len(cell_tasks)
                scene_depts_planned.add(dept.id)

                types = [t.task_type for t in cell_tasks]
                if len(types) > 1 and len(set(types)) < len(types):
                    duplicate_warnings.append({
                        "scene": scene,
                        "department": dept,
                        "tasks": cell_tasks,
                        "message": f"Multiple {cell_tasks[0].task_type} tasks created for Scene {scene.scene_number} under {dept.name}.",
                    })

            row_cells.append({
                "department": dept,
                "tasks": cell_tasks,
                "task_count": len(cell_tasks),
                "highest_status": cell_status,
            })

        if len(scene_depts_planned) == len(departments) and len(departments) > 0:
            fully_planned_scenes += 1
        elif len(scene_depts_planned) > 0:
            partially_planned_scenes += 1
        else:
            unplanned_scenes += 1

        matrix_rows.append({
            "scene": scene,
            "cells": row_cells,
            "scene_task_count": scene_task_count,
            "depts_planned_count": len(scene_depts_planned),
        })

    doc = project.script_documents.order_by("-created_at").first()
    latest_version = doc.versions.first() if doc else None
    unresolved_character_mentions_count = 0

    if latest_version:
        unresolved_character_mentions_count = latest_version.character_suggestions.filter(
            status="suggested"
        ).count()

    total_tasks = len(tasks)
    coverage_pct = round(((fully_planned_scenes + partially_planned_scenes) / total_scenes * 100), 1) if total_scenes > 0 else 0.0

    return {
        "scenes": scenes,
        "departments": departments,
        "matrix_rows": matrix_rows,
        "total_tasks": total_tasks,
        "total_scenes": total_scenes,
        "fully_planned_scenes": fully_planned_scenes,
        "partially_planned_scenes": partially_planned_scenes,
        "unplanned_scenes": unplanned_scenes,
        "unresolved_character_mentions_count": unresolved_character_mentions_count,
        "duplicate_warnings": duplicate_warnings,
        "coverage_pct": coverage_pct,
    }
