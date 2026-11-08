"""Тесты извлечения групп из JWT payload (OIDC_GROUPS_CLAIM)."""

from app.services.sso.groups import extract_groups_from_claim


def test_groups_top_level_list() -> None:
    payload = {"groups": ["atrium_role_admin", "outstaff"]}
    assert extract_groups_from_claim(payload, "groups") == ["atrium_role_admin", "outstaff"]


def test_realm_access_roles_nested() -> None:
    payload = {"realm_access": {"roles": ["offline_access", "uma_authorization"]}}
    assert extract_groups_from_claim(payload, "realm_access.roles") == [
        "offline_access",
        "uma_authorization",
    ]


def test_missing_claim() -> None:
    assert extract_groups_from_claim({}, "groups") == []


def test_single_string() -> None:
    assert extract_groups_from_claim({"groups": "single"}, "groups") == ["single"]


def test_empty_claim_path_returns_empty() -> None:
    assert extract_groups_from_claim({"groups": ["a"]}, "") == []


def test_intermediate_segment_not_dict_returns_empty() -> None:
    assert extract_groups_from_claim({"realm_access": "not-a-dict"}, "realm_access.roles") == []
