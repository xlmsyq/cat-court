"""不需要 API Key 也能跑的单元测试：只测结果归一化与 JSON 抽取。"""

from app import _normalize, _extract_json


def test_blame_normalized_to_100():
    v = _normalize({"blame": {"a": 30, "b": 30}})
    assert v["blame"]["a"] + v["blame"]["b"] == 100


def test_blame_missing_defaults_to_even():
    v = _normalize({})
    assert v["blame"] == {"a": 50, "b": 50}


def test_blame_clamped():
    v = _normalize({"blame": {"a": 900, "b": 100}})
    assert 0 <= v["blame"]["a"] <= 100
    assert v["blame"]["a"] + v["blame"]["b"] == 100


def test_intimacy_delta_bounded():
    assert _normalize({"intimacy_delta": 999})["intimacy_delta"] == 20
    assert _normalize({"intimacy_delta": -5})["intimacy_delta"] == 1


def test_tasks_fallback_when_empty():
    v = _normalize({"tasks": []})
    assert len(v["tasks"]) >= 3
    assert all(1 <= t["points"] <= 8 for t in v["tasks"])


def test_extract_json_from_code_fence():
    raw = "\u597d\u7684\uff1a\n```json\n{\"a\": 1}\n```\n"
    assert _extract_json(raw) == {"a": 1}


def test_extract_json_from_plain_text():
    assert _extract_json('\u55b5\u3002{"b": 2} \u4ee5\u4e0a') == {"b": 2}
