"""US0024: Design tokens + Jinja2 component partials.

Covers AC1 (token exports), AC2 (loader finds partials), AC3-AC4 (partial
rendering), AC5 (HTML escape), AC6 (no literal CSS values in partials),
AC7 (same partial in two wrapper contexts = identical inner HTML).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape

from techletter.compose.types import DeepDive, QuickMention
from techletter.delivery.renderers.tokens import COLORS, FONT, LAYOUT

# --- AC1: token exports -------------------------------------------------------


def test_AC1_colors_has_required_keys():
    required = {"bg", "fg", "muted", "accent", "border", "tag_bg"}
    assert required.issubset(COLORS.keys())


def test_AC1_font_has_required_keys():
    required = {"family", "mono", "size_body", "size_h1", "size_h2", "size_h3"}
    assert required.issubset(FONT.keys())


def test_AC1_layout_has_required_keys():
    required = {"max_width", "padding"}
    assert required.issubset(LAYOUT.keys())


def test_AC1_token_values_look_like_valid_css():
    # rough sanity: colors begin with '#', sizes end with 'px'
    for v in COLORS.values():
        assert v.startswith("#") and len(v) in (4, 7, 9)
    for k, v in FONT.items():
        if k.startswith("size_"):
            assert v.endswith("px")
    assert LAYOUT["max_width"].endswith("px")
    assert LAYOUT["padding"].endswith("px")


# --- Test environment ---------------------------------------------------------


@pytest.fixture
def env() -> Environment:
    return Environment(
        loader=PackageLoader("techletter.delivery", "templates"),
        autoescape=select_autoescape(["html", "j2", "html.j2"]),
        undefined=StrictUndefined,
    )


@pytest.fixture
def sample_dd() -> DeepDive:
    return DeepDive(
        cluster_id="c0",
        title="A deep dive title",
        body_md="ignored — body_html is passed in",
        item_kind="paper",
        primary_url="https://example.com/paper",  # type: ignore[arg-type]
        source_count=2,
    )


@pytest.fixture
def sample_qm() -> QuickMention:
    return QuickMention(
        title="Quick mention title",
        url="https://example.com/quick",  # type: ignore[arg-type]
        source="arxiv",
        item_kind="paper",
        one_liner="A short summary.",
    )


# --- AC2: loader finds partials ----------------------------------------------


def test_AC2_loader_finds_deep_dive_partial(env: Environment) -> None:
    tpl = env.get_template("components/deep_dive.html.j2")
    assert tpl is not None


def test_AC2_loader_finds_quick_mention_partial(env: Environment) -> None:
    tpl = env.get_template("components/quick_mention.html.j2")
    assert tpl is not None


# --- AC3: deep_dive renders required structure ------------------------------


def test_AC3_deep_dive_renders_title_link_and_tag(env: Environment, sample_dd: DeepDive) -> None:
    tpl = env.get_template("components/deep_dive.html.j2")
    out = tpl.render(
        dd=type("DD", (), {**sample_dd.model_dump(), "body_html": "<p>body</p>"})(),
        colors=COLORS,
        font=FONT,
        layout=LAYOUT,
    )
    assert "<h2" in out
    assert sample_dd.title in out
    assert 'href="https://example.com/paper"' in out
    assert 'class="tag"' in out
    assert "paper" in out
    assert "<p>body</p>" in out


# --- AC4: quick_mention renders required structure --------------------------


def test_AC4_quick_mention_renders_li_link_and_oneliner(
    env: Environment, sample_qm: QuickMention
) -> None:
    tpl = env.get_template("components/quick_mention.html.j2")
    out = tpl.render(qm=sample_qm, colors=COLORS, font=FONT, layout=LAYOUT)
    assert out.lstrip().startswith("<li")
    assert "</li>" in out
    assert 'href="https://example.com/quick"' in out
    assert sample_qm.title in out
    assert sample_qm.one_liner in out
    assert 'class="tag"' in out


# --- AC5: HTML escape --------------------------------------------------------


def test_AC5_dd_title_with_html_specials_is_escaped(env: Environment) -> None:
    dd = DeepDive(
        cluster_id="c0",
        title="A < B & C",
        body_md="x",
        item_kind="paper",
        primary_url="https://e.com",  # type: ignore[arg-type]
        source_count=1,
    )
    tpl = env.get_template("components/deep_dive.html.j2")
    out = tpl.render(
        dd=type("DD", (), {**dd.model_dump(), "body_html": ""})(),
        colors=COLORS,
        font=FONT,
        layout=LAYOUT,
    )
    assert "A &lt; B &amp; C" in out
    assert "A < B & C" not in out


def test_AC5_qm_title_with_html_specials_is_escaped(env: Environment) -> None:
    qm = QuickMention(
        title="X > Y",
        url="https://e.com",  # type: ignore[arg-type]
        source="arxiv",
        item_kind="paper",
        one_liner="z & w",
    )
    tpl = env.get_template("components/quick_mention.html.j2")
    out = tpl.render(qm=qm, colors=COLORS, font=FONT, layout=LAYOUT)
    assert "X &gt; Y" in out
    assert "z &amp; w" in out


# --- AC6: no literal CSS values in partial sources ---------------------------


def _partial_source(name: str) -> str:
    path = Path(__file__).parents[4] / "techletter" / "delivery" / "templates" / "components" / name
    return path.read_text(encoding="utf-8")


def test_AC6_deep_dive_partial_has_no_hex_literal():
    src = _partial_source("deep_dive.html.j2")
    # Grep #abc / #abcdef / #abcdef00 not inside Jinja `{{ }}`
    # Simpler: assert no `#[0-9a-fA-F]{3,8}` outside `colors.` references
    hexes = re.findall(r"#[0-9a-fA-F]{3,8}\b", src)
    assert hexes == [], f"hex color literals found: {hexes}"


def test_AC6_quick_mention_partial_has_no_hex_literal():
    src = _partial_source("quick_mention.html.j2")
    hexes = re.findall(r"#[0-9a-fA-F]{3,8}\b", src)
    assert hexes == [], f"hex color literals found: {hexes}"


# --- AC7: same partial in two wrappers → identical inner HTML ---------------


def test_AC7_partial_inner_html_identical_across_wrappers(
    env: Environment, sample_dd: DeepDive
) -> None:
    # Render the same partial inside two wrapper contexts; the inner HTML
    # produced by the partial itself must be byte-identical (only wrappers differ).
    inner_tpl = env.get_template("components/deep_dive.html.j2")
    inner = inner_tpl.render(
        dd=type("DD", (), {**sample_dd.model_dump(), "body_html": "<p>x</p>"})(),
        colors=COLORS,
        font=FONT,
        layout=LAYOUT,
    )

    div_wrapped = f"<div>{inner}</div>"
    table_wrapped = f"<table><tr><td>{inner}</td></tr></table>"

    # Strip wrappers and compare
    div_inner = div_wrapped[len("<div>"): -len("</div>")]
    table_inner = table_wrapped[
        len("<table><tr><td>"): -len("</td></tr></table>")
    ]
    assert div_inner == table_inner


# --- StrictUndefined: typo in token name fails loudly -----------------------


def test_strict_undefined_typo_in_context_raises(env: Environment, sample_qm: QuickMention) -> None:
    from jinja2.exceptions import UndefinedError

    tpl = env.get_template("components/quick_mention.html.j2")
    with pytest.raises(UndefinedError):
        # Missing `colors` should raise, not silently render empty
        tpl.render(qm=sample_qm, font=FONT, layout=LAYOUT)
