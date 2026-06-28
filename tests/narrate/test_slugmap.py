from __future__ import annotations

import json

from ghps.narrate.slugmap import (
    load_registry,
    match_slug,
    reconcile_slugs,
    save_registry,
    update_registry,
)


def _registry():
    return [
        {"slug": "weather-integration", "title": "Weather", "repos": ["riff"], "pr_numbers": ["riff#8"]},
        {"slug": "web-audio-gated-flows-and-flow-picker", "title": "Audio",
         "repos": ["riff"], "pr_numbers": ["riff#12"]},
    ]


def test_match_slug_exact_pr_set():
    assert match_slug(["riff#12"], _registry()) == "web-audio-gated-flows-and-flow-picker"


def test_match_slug_no_match_returns_none():
    assert match_slug(["riff#99"], _registry()) is None


def test_match_slug_tolerates_grown_membership():
    # A theme that gained a PR later still maps to its original slug
    # (Jaccard {12} vs {12,20} = 0.5, at the >= threshold).
    assert match_slug(["riff#12", "riff#20"], _registry()) == "web-audio-gated-flows-and-flow-picker"


def test_match_slug_below_threshold_is_none():
    # One shared PR out of four (Jaccard 0.25) is too weak to pin.
    assert match_slug(["riff#12", "riff#30", "riff#31", "riff#32"], _registry()) is None


def test_reconcile_pins_drifted_slug():
    # The cold rebuild minted a different slug for the same PR; reconcile pins it back.
    themes = [{"slug": "audio-gated-flows-improvements", "pr_numbers": ["riff#12"]}]
    reconcile_slugs(themes, _registry())
    assert themes[0]["slug"] == "web-audio-gated-flows-and-flow-picker"


def test_reconcile_leaves_new_theme_untouched():
    themes = [{"slug": "brand-new-theme", "pr_numbers": ["riff#50"]}]
    reconcile_slugs(themes, _registry())
    assert themes[0]["slug"] == "brand-new-theme"


def test_reconcile_does_not_assign_same_pinned_slug_twice():
    # Two themes both overlapping the same entry: only the best gets the slug,
    # the other keeps its minted slug (no duplicate URLs).
    themes = [
        {"slug": "minted-a", "pr_numbers": ["riff#12"]},
        {"slug": "minted-b", "pr_numbers": ["riff#12", "riff#21"]},
    ]
    reconcile_slugs(themes, _registry())
    pinned = [t["slug"] for t in themes]
    assert pinned.count("web-audio-gated-flows-and-flow-picker") == 1


def test_update_registry_appends_new_and_unions_prs():
    reg = _registry()
    published = [
        {"slug": "web-audio-gated-flows-and-flow-picker", "title": "Audio v2",
         "repos": ["riff"], "pr_numbers": ["riff#12", "riff#21"]},
        {"slug": "brand-new-theme", "title": "New", "repos": ["riff"], "pr_numbers": ["riff#50"]},
    ]
    out = update_registry(reg, published)
    by_slug = {e["slug"]: e for e in out}
    assert by_slug["brand-new-theme"]["pr_numbers"] == ["riff#50"]
    # existing entry's PR set is unioned with the new membership
    assert by_slug["web-audio-gated-flows-and-flow-picker"]["pr_numbers"] == ["riff#12", "riff#21"]


def test_load_save_roundtrip(tmp_path):
    p = tmp_path / "learn-slugs.json"
    assert load_registry(p) == []          # missing file -> empty
    save_registry(p, _registry())
    again = load_registry(p)
    assert {e["slug"] for e in again} == {
        "weather-integration", "web-audio-gated-flows-and-flow-picker"}
    # persisted as sorted, indented JSON
    assert json.loads(p.read_text()) == again
