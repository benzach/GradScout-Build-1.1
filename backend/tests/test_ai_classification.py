"""
Tests for app/ai_classification.py. Entirely mocked — no real network
calls, no real API key needed, no cost. What's being tested is the
wrapper logic itself (validation against the canonical list, graceful
failure handling, the opt-out-when-unconfigured behaviour), not
Claude's actual classification quality, which isn't something a unit
test can meaningfully assert on anyway.
"""
from unittest.mock import patch

from app.ai_classification import classify_industry_with_ai, classify_location_with_ai

CANONICAL_LOCATIONS = ["London", "Manchester", "Other UK"]
CANONICAL_INDUSTRIES = ["Technology", "Finance", "Other"]


class _FakeResponse:
    def __init__(self, text: str, status: int = 200):
        self._text = text
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.exceptions.HTTPError(f"{self.status_code} error")

    def json(self):
        return {"content": [{"type": "text", "text": self._text}]}


def test_returns_none_without_api_key_and_makes_no_request():
    with patch.dict("os.environ", {}, clear=True), \
         patch("app.ai_classification.requests.post") as mock_post:
        result = classify_location_with_ai("some village", "Grad Analyst", CANONICAL_LOCATIONS)

    assert result is None
    mock_post.assert_not_called()


def test_valid_canonical_response_is_accepted():
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key"}), \
         patch("app.ai_classification.requests.post", return_value=_FakeResponse("Manchester")):
        result = classify_location_with_ai("Salford Quays", "Grad Analyst", CANONICAL_LOCATIONS)

    assert result == "Manchester"


def test_unknown_response_returns_none():
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key"}), \
         patch("app.ai_classification.requests.post", return_value=_FakeResponse("UNKNOWN")):
        result = classify_location_with_ai("somewhere in Portugal", "Grad Analyst", CANONICAL_LOCATIONS)

    assert result is None


def test_hallucinated_non_canonical_response_is_rejected():
    """
    The critical guardrail: a fixed-vocabulary field must never accept
    a value the model invented, even if it looks plausible - "Leeds" is
    a real UK city, just not one in *this* test's canonical list, and
    that distinction is exactly what must be enforced.
    """
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key"}), \
         patch("app.ai_classification.requests.post", return_value=_FakeResponse("Leeds")):
        result = classify_location_with_ai("some village", "Grad Analyst", CANONICAL_LOCATIONS)

    assert result is None


def test_network_failure_returns_none_not_raises():
    import requests as requests_module

    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key"}), \
         patch("app.ai_classification.requests.post", side_effect=requests_module.exceptions.Timeout("simulated")):
        result = classify_location_with_ai("some village", "Grad Analyst", CANONICAL_LOCATIONS)

    assert result is None


def test_http_error_status_returns_none_not_raises():
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key"}), \
         patch("app.ai_classification.requests.post", return_value=_FakeResponse("", status=401)):
        result = classify_location_with_ai("some village", "Grad Analyst", CANONICAL_LOCATIONS)

    assert result is None


def test_blank_raw_location_short_circuits_without_a_request():
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key"}), \
         patch("app.ai_classification.requests.post") as mock_post:
        result = classify_location_with_ai("   ", "Grad Analyst", CANONICAL_LOCATIONS)

    assert result is None
    mock_post.assert_not_called()


def test_industry_classification_follows_the_same_validation_rules():
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key"}), \
         patch("app.ai_classification.requests.post", return_value=_FakeResponse("Finance")):
        result = classify_industry_with_ai("Graduate Actuary", "Join our pensions team...", CANONICAL_INDUSTRIES)

    assert result == "Finance"


def test_industry_classification_rejects_hallucinated_category():
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key"}), \
         patch("app.ai_classification.requests.post", return_value=_FakeResponse("Healthcare")):
        result = classify_industry_with_ai("Graduate Nurse", "Join our ward team...", CANONICAL_INDUSTRIES)

    assert result is None


def test_response_with_surrounding_whitespace_is_trimmed():
    """Models sometimes wrap short answers in a trailing newline - this shouldn't cause a false non-match against the canonical list."""
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key"}), \
         patch("app.ai_classification.requests.post", return_value=_FakeResponse("  London\n")):
        result = classify_location_with_ai("EC postcode job", "Grad Analyst", CANONICAL_LOCATIONS)

    assert result == "London"
