from collections import Counter
from math import sqrt

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TemplateSlide
from app.schemas import DesignMatch


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (left_norm * right_norm)))


def _elements(structure: dict) -> list[dict]:
    return [element for element in structure.get("elements", []) if element.get("width", 0) > 0.01 and element.get("height", 0) > 0.01]


def _count_similarity(query: dict, candidate: dict) -> float:
    query_counts = Counter(element.get("element_type") for element in _elements(query))
    candidate_counts = Counter(element.get("element_type") for element in _elements(candidate))
    kinds = set(query_counts) | set(candidate_counts)
    total = sum(max(query_counts[kind], candidate_counts[kind]) for kind in kinds)
    difference = sum(abs(query_counts[kind] - candidate_counts[kind]) for kind in kinds)
    return 1.0 if total == 0 else max(0.0, 1.0 - difference / total)


def _column_count(structure: dict) -> int | None:
    candidates = [
        element
        for element in _elements(structure)
        if element.get("element_type") == "text_box"
        and int(element.get("character_count") or 0) > 0
        and float(element["width"]) >= 0.15
        and float(element["width"]) <= 0.48
        and float(element["height"]) >= 0.12
        and float(element["x"]) >= 0
        and float(element["x"]) + float(element["width"]) <= 1.02
        and not (float(element["y"]) < 0.2 and float(element["width"]) > 0.5)
    ]
    if len(candidates) < 2:
        return None

    centers = sorted(
        float(element["x"]) + float(element["width"]) / 2
        for element in candidates
    )
    clusters: list[list[float]] = []
    for center in centers:
        if not clusters or center - sum(clusters[-1]) / len(clusters[-1]) >= 0.18:
            clusters.append([center])
        else:
            clusters[-1].append(center)
    return len(clusters) if 2 <= len(clusters) <= 3 else None


def _side_content(structure: dict, side: str) -> str:
    has_text = False
    has_image = False
    for element in _elements(structure):
        center = float(element["x"]) + float(element["width"]) / 2
        if (side == "left" and center >= 0.5) or (side == "right" and center < 0.5):
            continue
        if (
            element.get("element_type") == "text_box"
            and int(element.get("character_count") or 0) > 0
            and not (float(element["y"]) < 0.2 and float(element["width"]) > 0.5)
        ):
            has_text = True
        if (
            element.get("element_type") == "image"
            and float(element["width"]) * float(element["height"]) >= 0.04
        ):
            has_image = True
    if has_text and has_image:
        return "mixed"
    if has_image:
        return "image"
    if has_text:
        return "text"
    return "empty"


def _column_composition(structure: dict) -> str | None:
    if _column_count(structure) != 2:
        return None
    return f"{_side_content(structure, 'left')}-{_side_content(structure, 'right')}"


def _has_prominent_image(structure: dict) -> bool:
    return any(
        element.get("element_type") == "image"
        and float(element["width"]) * float(element["height"]) >= 0.08
        for element in _elements(structure)
    )


def _kpi_count(structure: dict) -> int:
    """Count large, short value-like text elements without reading their text."""
    return sum(
        1
        for element in _elements(structure)
        if element.get("element_type") == "text_box"
        and float(element.get("font_size") or 0) >= 32
        and 0.2 <= float(element["y"]) <= 0.75
        and 0 < int(element.get("character_count") or 0) <= 8
        and float(element["width"]) <= 0.4
    )


def _repeated_item_count(structure: dict) -> int | None:
    """Detect horizontally repeated visual anchors used by steps or processes."""
    centers = sorted(
        float(element["x"]) + float(element["width"]) / 2
        for element in _elements(structure)
        if element.get("element_type") == "text_box"
        and int(element.get("character_count") or 0) == 0
        and 0.25 <= float(element["y"]) <= 0.8
        and float(element["width"]) <= 0.15
        and float(element["height"]) <= 0.2
        and float(element["width"]) * float(element["height"]) <= 0.04
    )
    clusters: list[list[float]] = []
    for center in centers:
        if not clusters or center - sum(clusters[-1]) / len(clusters[-1]) >= 0.12:
            clusters.append([center])
        else:
            clusters[-1].append(center)
    return len(clusters) if len(clusters) >= 3 else None


def _layout_compatible(
    query: dict,
    candidate: dict,
    *,
    enforce_composition: bool = True,
) -> bool:
    query_types = Counter(element.get("element_type") for element in _elements(query))
    candidate_types = Counter(
        element.get("element_type") for element in _elements(candidate)
    )
    for structural_type in ("table", "chart"):
        if bool(query_types[structural_type]) != bool(candidate_types[structural_type]):
            return False
    # A large illustration changes the visual composition substantially. In
    # particular, it must not outrank a clean table/chart slide merely because
    # both PPTX files happen to contain a table object.
    if (
        (query_types["table"] or query_types["chart"])
        and not _has_prominent_image(query)
        and _has_prominent_image(candidate)
    ):
        return False
    query_kpis = _kpi_count(query)
    if query_kpis >= 2 and _kpi_count(candidate) != query_kpis:
        return False
    query_items = _repeated_item_count(query)
    if query_items is not None and _repeated_item_count(candidate) != query_items:
        return False
    if query_types["image"] and not candidate_types["image"]:
        return False
    query_columns = _column_count(query)
    candidate_columns = _column_count(candidate)
    if query_columns is not None and query_columns != candidate_columns:
        return False
    if enforce_composition and query_columns == 2:
        return _column_composition(query) == _column_composition(candidate)
    return True


def _element_distance(left: dict, right: dict) -> float:
    return (
        abs(float(left["x"]) - float(right["x"]))
        + abs(float(left["y"]) - float(right["y"]))
        + abs(float(left["width"]) - float(right["width"]))
        + abs(float(left["height"]) - float(right["height"]))
    ) / 4


def _geometry_similarity(query: dict, candidate: dict) -> float:
    query_elements = _elements(query)
    candidate_elements = _elements(candidate)
    if not query_elements and not candidate_elements:
        return 1.0
    if not query_elements or not candidate_elements:
        return 0.0

    scores: list[float] = []
    used: set[int] = set()
    for query_element in query_elements:
        same_type = [
            (index, element)
            for index, element in enumerate(candidate_elements)
            if index not in used
            and element.get("element_type") == query_element.get("element_type")
        ]
        if not same_type:
            scores.append(0.0)
            continue
        index, closest = min(
            same_type,
            key=lambda pair: _element_distance(query_element, pair[1]),
        )
        used.add(index)
        scores.append(max(0.0, 1.0 - 2.0 * _element_distance(query_element, closest)))

    unmatched = len(candidate_elements) - len(used)
    scores.extend([0.0] * unmatched)
    return sum(scores) / len(scores)


def _table_dimension_similarity(query: dict, candidate: dict) -> float:
    query_tables = [
        element for element in _elements(query) if element.get("element_type") == "table"
    ]
    candidate_tables = [
        element
        for element in _elements(candidate)
        if element.get("element_type") == "table"
    ]
    if not query_tables and not candidate_tables:
        return 1.0
    if not query_tables or not candidate_tables:
        return 0.0

    query_table = query_tables[0]
    candidate_table = candidate_tables[0]
    query_columns = int(query_table.get("table_columns") or 0)
    candidate_columns = int(candidate_table.get("table_columns") or 0)
    query_rows = int(query_table.get("table_rows") or 0)
    candidate_rows = int(candidate_table.get("table_rows") or 0)
    if not query_columns or not candidate_columns:
        return 0.0

    column_score = 1.0 - abs(query_columns - candidate_columns) / max(
        query_columns, candidate_columns
    )
    row_score = (
        1.0 - abs(query_rows - candidate_rows) / max(query_rows, candidate_rows)
        if query_rows and candidate_rows
        else 0.0
    )
    return 0.8 * column_score + 0.2 * row_score


async def find_similar(
    session: AsyncSession,
    embedding: list[float],
    structure: dict,
    limit: int = 3,
    minimum_score: float = 0.75,
) -> list[DesignMatch]:
    all_templates = (await session.scalars(select(TemplateSlide))).all()
    compatible_templates = [
        template
        for template in all_templates
        if _layout_compatible(structure, template.structure)
    ]
    fallback_templates = [
        template
        for template in all_templates
        if _layout_compatible(
            structure,
            template.structure,
            enforce_composition=False,
        )
    ]
    is_fallback = not bool(compatible_templates)
    templates = compatible_templates or fallback_templates or all_templates
    ranked = []
    for template in templates:
        embedding_score = _cosine_similarity(embedding, list(template.structural_embedding))
        geometry_score = _geometry_similarity(structure, template.structure)
        count_score = _count_similarity(structure, template.structure)
        has_table = any(
            element.get("element_type") == "table" for element in _elements(structure)
        )
        if has_table:
            table_score = _table_dimension_similarity(structure, template.structure)
            final_score = (
                0.2 * embedding_score
                + 0.25 * geometry_score
                + 0.15 * count_score
                + 0.4 * table_score
            )
        else:
            final_score = 0.4 * embedding_score + 0.4 * geometry_score + 0.2 * count_score
        ranked.append((template, final_score))
    ranked.sort(key=lambda item: item[1], reverse=True)

    eligible = [item for item in ranked if item[1] >= minimum_score][:limit]
    if ranked and not eligible:
        eligible = [ranked[0]]
    return [
        DesignMatch(
            template_id=template.id,
            name=template.name,
            source_filename=template.source_filename,
            slide_number=template.slide_number,
            similarity=max(0.0, min(1.0, final_score)),
            preview_url=(f"/previews/{template.id}.png" if template.preview_path else None),
            download_url=f"/api/templates/{template.id}/download",
            is_fallback=is_fallback,
        )
        for template, final_score in eligible
    ]
