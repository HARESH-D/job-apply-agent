from services.company_tier import COMPANY_TIERS, classify_company


def test_curated_company_tiers_and_unrated_fallback():
    assert classify_company("Microsoft").tier == "tier1"
    assert classify_company("Microsoft Corporation").tier == "tier1"
    assert classify_company("Cisco").tier == "tier2"
    assert classify_company("Unmapped Example Labs").tier == "unrated"


def test_curated_configuration_supports_all_five_tiers():
    assert {entry["tier"] for entry in COMPANY_TIERS.values()} == {
        "tier1",
        "tier2",
        "tier3",
        "tier4",
        "tier5",
    }
