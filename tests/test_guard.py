from dby.guard import REPLACEMENT, scrub, scrub_obj


def test_scores_are_removed():
    for text in ["市场潜力 8/10", "可行性：7.5 分", "综合评分 85", "这个点子 90分。", "成功率约 70%"]:
        out, hits = scrub(text)
        assert REPLACEMENT in out, text
        assert hits, text


def test_hype_phrases_are_removed():
    out, hits = scrub("这是一个蓝海市场，前景广阔，属于刚需。")
    assert "蓝海" not in out and "前景广阔" not in out and "刚需" not in out
    assert len(hits) == 3


def test_build_advice_is_removed_but_method_advice_kept():
    out, hits = scrub("建议立即开发。建议做 5 次访谈。")
    assert "建议立即开发" not in out
    assert "建议做 5 次访谈" in out
    assert len(hits) == 1


def test_ordinary_numbers_untouched():
    text = "每次访谈 15 分钟，分析 3 条评论，第 7 天复盘，定金 9.9 元，分享给 10 个人。"
    out, hits = scrub(text)
    assert out == text
    assert hits == []


def test_scrub_obj_walks_nested_json():
    hits = []
    data = {"a": ["潜力巨大", {"b": "评分 9 分"}], "n": 3}
    out = scrub_obj(data, "t", hits)
    assert out["n"] == 3
    assert "潜力巨大" not in out["a"][0]
    assert len(hits) == 2
    assert all(h.where == "t" for h in hits)
