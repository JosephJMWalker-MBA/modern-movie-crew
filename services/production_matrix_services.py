from apps.production.models import CoveragePlan, ProductionTask, Scene, ScriptVersion
from apps.projects.models import Department
from services.shot_planning_services import detect_editorial_completeness_warnings


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
        "shot_links__shot",
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

    # Pre-fetch coverage plans and shots per scene
    plans = list(CoveragePlan.objects.filter(project=project).prefetch_related(
        "shots__task_links__task__canonical_selections",
        "segment_links",
        "warning_waivers",
    ))

    # Build scene to shots lookup
    scene_plans_map = {}
    for p in plans:
        link = p.segment_links.first()
        if link and link.start_segment and link.start_segment.scene_id:
            s_id = link.start_segment.scene_id
            scene_plans_map.setdefault(s_id, []).append(p)

    matrix_rows = []
    total_scenes = len(scenes)
    fully_planned_scenes = 0
    partially_planned_scenes = 0
    unplanned_scenes = 0

    duplicate_warnings = []
    total_shots_count = 0
    total_accepted_shots_count = 0
    total_editorial_warnings_count = 0

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

        # Scene shot coverage metrics
        scene_plans = scene_plans_map.get(scene.id, [])
        scene_shots = []
        scene_warnings = []
        for p in scene_plans:
            scene_shots.extend(list(p.shots.all()))
            scene_warnings.extend(detect_editorial_completeness_warnings(coverage_plan=p))

        scene_shots_count = len(scene_shots)
        accepted_shots_count = sum(
            1 for s in scene_shots if any(l.task.active_canonical_selection() for l in s.task_links.all())
        )

        total_shots_count += scene_shots_count
        total_accepted_shots_count += accepted_shots_count
        total_editorial_warnings_count += len(scene_warnings)

        matrix_rows.append({
            "scene": scene,
            "cells": row_cells,
            "scene_task_count": scene_task_count,
            "depts_planned_count": len(scene_depts_planned),
            "scene_shots_count": scene_shots_count,
            "accepted_shots_count": accepted_shots_count,
            "scene_warnings_count": len(scene_warnings),
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
        "total_shots_count": total_shots_count,
        "total_accepted_shots_count": total_accepted_shots_count,
        "total_editorial_warnings_count": total_editorial_warnings_count,
        "duplicate_warnings": duplicate_warnings,
        "coverage_pct": coverage_pct,
    }
