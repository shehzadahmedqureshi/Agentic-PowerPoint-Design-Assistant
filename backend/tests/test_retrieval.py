from app.services.retrieval import (
    _column_composition,
    _column_count,
    _count_similarity,
    _geometry_similarity,
    _kpi_count,
    _layout_compatible,
    _repeated_item_count,
    _table_dimension_similarity,
)


def _structure(elements: list[dict]) -> dict:
    return {"elements": elements}


def _element(kind: str, x: float, y: float, width: float, height: float) -> dict:
    return {
        "element_type": kind,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "character_count": 20 if kind == "text_box" else None,
    }


def test_geometry_prefers_matching_layout() -> None:
    query = _structure([
        _element("text_box", 0.05, 0.08, 0.4, 0.2),
        _element("image", 0.0, 0.36, 0.48, 0.64),
        _element("text_box", 0.55, 0.2, 0.35, 0.1),
    ])
    matching = _structure([
        _element("text_box", 0.06, 0.1, 0.39, 0.2),
        _element("image", 0.0, 0.35, 0.49, 0.65),
        _element("text_box", 0.56, 0.2, 0.34, 0.1),
    ])
    cards = _structure([
        _element("text_box", 0.05, 0.08, 0.5, 0.1),
        _element("text_box", 0.05, 0.4, 0.25, 0.4),
        _element("text_box", 0.37, 0.4, 0.25, 0.4),
    ])

    assert _geometry_similarity(query, matching) > _geometry_similarity(query, cards)
    assert _count_similarity(query, matching) > _count_similarity(query, cards)


def test_table_layout_only_accepts_table_candidates() -> None:
    query = _structure([
        _element("text_box", 0.05, 0.05, 0.8, 0.1),
        _element("table", 0.08, 0.2, 0.84, 0.65),
    ])
    with_table = _structure([
        _element("text_box", 0.06, 0.06, 0.8, 0.1),
        _element("table", 0.1, 0.22, 0.8, 0.6),
    ])
    without_table = _structure([
        _element("text_box", 0.06, 0.06, 0.8, 0.1),
        _element("text_box", 0.1, 0.22, 0.8, 0.6),
    ])

    assert _layout_compatible(query, with_table)
    assert not _layout_compatible(query, without_table)


def test_plain_table_rejects_table_slide_dominated_by_illustration() -> None:
    query = _structure([
        _element("text_box", 0.05, 0.05, 0.8, 0.1),
        _element("table", 0.08, 0.2, 0.84, 0.65),
    ])
    illustrated_table = _structure([
        _element("text_box", 0.05, 0.1, 0.35, 0.15),
        _element("image", 0.08, 0.35, 0.32, 0.5),
        _element("table", 0.5, 0.15, 0.2, 0.3),
    ])

    assert not _layout_compatible(query, illustrated_table)


def test_table_dimensions_prefer_matching_column_count() -> None:
    query = _structure([
        {**_element("table", 0.08, 0.2, 0.84, 0.65), "table_rows": 5, "table_columns": 3},
    ])
    exact = _structure([
        {**_element("table", 0.05, 0.25, 0.9, 0.6), "table_rows": 6, "table_columns": 3},
    ])
    wrong_columns = _structure([
        {**_element("table", 0.08, 0.2, 0.84, 0.65), "table_rows": 5, "table_columns": 7},
    ])

    assert _table_dimension_similarity(query, exact) > _table_dimension_similarity(
        query, wrong_columns
    )


def test_three_kpi_layout_requires_three_large_short_values() -> None:
    query = _structure([
        {**_element("text_box", 0.08, 0.35, 0.22, 0.14), "font_size": 40, "character_count": 3},
        {**_element("text_box", 0.38, 0.35, 0.22, 0.14), "font_size": 40, "character_count": 4},
        {**_element("text_box", 0.68, 0.35, 0.22, 0.14), "font_size": 40, "character_count": 3},
    ])
    true_kpis = _structure([
        {**_element("text_box", 0.08, 0.4, 0.22, 0.14), "font_size": 48, "character_count": 1},
        {**_element("text_box", 0.38, 0.4, 0.22, 0.14), "font_size": 48, "character_count": 1},
        {**_element("text_box", 0.68, 0.4, 0.22, 0.14), "font_size": 48, "character_count": 1},
    ])
    generic_columns = _structure([
        _element("text_box", 0.05, 0.3, 0.28, 0.5),
        _element("text_box", 0.36, 0.3, 0.28, 0.5),
        _element("text_box", 0.68, 0.3, 0.28, 0.5),
    ])

    assert _kpi_count(query) == 3
    assert _layout_compatible(query, true_kpis)
    assert not _layout_compatible(query, generic_columns)


def test_four_step_process_rejects_three_repeated_items() -> None:
    four_steps = _structure([
        {**_element("text_box", x, 0.42, 0.08, 0.14), "character_count": 0}
        for x in (0.1, 0.34, 0.57, 0.8)
    ])
    three_items = _structure([
        {**_element("text_box", x, 0.32, 0.1, 0.16), "character_count": 0}
        for x in (0.14, 0.45, 0.74)
    ])

    assert _repeated_item_count(four_steps) == 4
    assert _repeated_item_count(three_items) == 3
    assert not _layout_compatible(four_steps, three_items)


def test_column_detector_distinguishes_two_and_three_columns() -> None:
    two_columns = _structure([
        _element("text_box", 0.06, 0.2, 0.42, 0.62),
        _element("text_box", 0.52, 0.2, 0.42, 0.62),
        _element("text_box", 0.09, 0.38, 0.34, 0.26),
        _element("text_box", 0.55, 0.38, 0.34, 0.26),
    ])
    three_columns = _structure([
        _element("text_box", 0.05, 0.3, 0.28, 0.5),
        _element("text_box", 0.36, 0.3, 0.28, 0.5),
        _element("text_box", 0.68, 0.3, 0.28, 0.5),
    ])

    assert _column_count(two_columns) == 2
    assert _column_count(three_columns) == 3
    assert not _layout_compatible(two_columns, three_columns)


def test_two_column_composition_distinguishes_text_and_images() -> None:
    text_text = _structure([
        _element("text_box", 0.06, 0.25, 0.4, 0.5),
        _element("text_box", 0.54, 0.25, 0.4, 0.5),
    ])
    image_text = _structure([
        _element("image", 0.06, 0.25, 0.4, 0.5),
        _element("text_box", 0.54, 0.25, 0.4, 0.5),
        _element("text_box", 0.07, 0.7, 0.2, 0.13),
    ])

    assert _column_composition(text_text) == "text-text"
    assert _column_composition(image_text) == "mixed-text"
    assert not _layout_compatible(text_text, image_text)
    assert _layout_compatible(text_text, image_text, enforce_composition=False)
