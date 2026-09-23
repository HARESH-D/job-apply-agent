"""Curated company classification. Unknown names are never inferred."""
import re
from dataclasses import dataclass


TIER_LABELS = {
    "tier1": "Tier 1 · Global leader",
    "tier2": "Tier 2 · Leading product",
    "tier3": "Tier 3 · Established",
    "tier4": "Tier 4 · Growth company",
    "tier5": "Tier 5 · Global services",
    "unrated": "Unrated",
}

_CURATED = {
    "tier1": [
        "Google", "Microsoft", "Apple", "Amazon", "Meta", "NVIDIA",
        "Netflix", "OpenAI",
    ],
    "tier2": [
        "Adobe", "Airbnb", "Atlassian", "Cisco", "Databricks", "LinkedIn",
        "Oracle", "Qualcomm", "Salesforce", "SAP", "ServiceNow", "Snowflake",
        "Stripe", "Uber",
    ],
    "tier3": [
        "Bosch", "Cargill", "Dell", "Gartner", "Goldman Sachs", "Halliburton",
        "IBM", "Intel", "JPMorgan Chase", "Siemens",
    ],
    "tier4": [
        "Canva", "Freshworks", "PhonePe", "Razorpay", "Swiggy", "Zomato",
    ],
    "tier5": [
        "Accenture", "Capgemini", "Cognizant", "HCLTech", "Infosys",
        "Tata Consultancy Services", "TCS", "Wipro",
    ],
}


def normalize_company_name(name: str) -> str:
    normalized = name.lower().replace("&", " and ")
    normalized = re.sub(
        r"\b(incorporated|corporation|corp|inc|limited|ltd|llc|plc|pvt)\b\.?",
        "",
        normalized,
    )
    return re.sub(r"[^a-z0-9]+", " ", normalized).strip()


COMPANY_TIERS = {
    normalize_company_name(company): {
        "tier": tier,
        "canonical_name": company,
    }
    for tier, companies in _CURATED.items()
    for company in companies
}


@dataclass(frozen=True)
class CompanyTierResult:
    tier: str
    label: str


def classify_company(name: str) -> CompanyTierResult:
    entry = COMPANY_TIERS.get(normalize_company_name(name))
    tier = entry["tier"] if entry else "unrated"
    return CompanyTierResult(tier=tier, label=TIER_LABELS[tier])
