"""Basic unit tests for token validation logic.

NOTE: Uses a fabricated token without signature verification (for structure tests).
Future enhancement: generate real signed JWT with ephemeral key.
"""
from shared.auth.token_validation import _extract_header


def test_extract_header_invalid_structure():
    try:
        _extract_header("invalid")
    except Exception as exc:
        assert "Invalid JWT" in str(exc)
    else:
        raise AssertionError("Expected exception for invalid structure")


def test_extract_header_minimal():
    # header.payload.signature (base64url); we only inspect header portion
    import base64, json
    header = {"alg": "RS256", "kid": "123"}
    h_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
    token = f"{h_b64}.x.y"
    parsed = _extract_header(token)
    assert parsed["kid"] == "123"
