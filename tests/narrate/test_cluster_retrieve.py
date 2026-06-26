from ghps.narrate.cluster import cosine, retrieve, pr_embed_text, ATTACH_HI, ASK_LO


def test_cosine_identity():
    assert abs(cosine([1.0, 0.0], [1.0, 0.0]) - 1.0) < 1e-9
    assert abs(cosine([1.0, 0.0], [0.0, 1.0])) < 1e-9


def test_retrieve_ranks_by_cosine():
    themes = [
        {"theme_id": "a", "embedding": [1.0, 0.0]},
        {"theme_id": "b", "embedding": [0.0, 1.0]},
    ]
    out = retrieve([0.9, 0.1], themes, top=2)
    assert out[0][0]["theme_id"] == "a" and out[0][1] > out[1][1]


def test_thresholds_ordered():
    assert ATTACH_HI > ASK_LO


def test_pr_embed_text_includes_problem():
    txt = pr_embed_text({"title": "T", "problem": "P", "approach": "A",
                         "components": ["c"], "apis_changed": ["x"]})
    assert "P" in txt and "T" in txt
