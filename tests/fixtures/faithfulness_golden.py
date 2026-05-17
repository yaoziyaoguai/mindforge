"""M2 Faithfulness golden fixtures — TDD §4.1c。

用于确定性 faithfulness 计算的分级测试用例。
"""

FAITHFULNESS_GOLDEN = {
    "faithful_case": {
        "section_text": (
            "authentication uses authorization codes and refresh tokens for secure access"
        ),
        "card_bodies": {
            "c_auth_1": "authentication uses authorization codes for secure access",
            "c_auth_2": "refresh tokens enable secure access for authentication",
        },
        "expected_score_min": 0.5,
    },
    "unfaithful_case": {
        "section_text": "PostgreSQL supports window functions like ROW_NUMBER and RANK.",
        "card_bodies": {
            "c_api_1": "REST API endpoints use JSON for request and response bodies.",
        },
        "expected_score_max": 0.2,
    },
    "partial_case": {
        "section_text": (
            "JWT tokens provide stateless authentication. Rate limiting prevents abuse."
        ),
        "card_bodies": {
            "c_auth_1": "JWT is a compact token format for stateless authentication.",
        },
        "expected_score_min": 0.2,
        "expected_score_max": 0.5,
    },
    "no_references_case": {
        "section_text": "This section covers general architecture principles.",
        "card_bodies": {},
        "expected_warning": "no_card_references",
    },
}
