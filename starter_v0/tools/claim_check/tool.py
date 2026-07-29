from __future__ import annotations

import re


CURRENT_MARKERS = {
    "today",
    "this week",
    "latest",
    "current",
    "recently",
    "released",
    "announced",
    "hom nay",
    "tuan nay",
    "moi nhat",
}
SCIENTIFIC_MARKERS = {
    "study",
    "paper",
    "research",
    "clinical",
    "trial",
    "arxiv",
    "doi",
    "nghien cuu",
    "bai bao",
    "khoa hoc",
}
PRODUCT_MARKERS = {
    "price",
    "pricing",
    "model",
    "feature",
    "benchmark",
    "release",
    "product",
    "gia",
    "tinh nang",
}


def _contains_any(text: str, markers: set[str]) -> bool:
    return any(marker in text for marker in markers)


def _infer_domain(text: str, requested: str) -> str:
    if requested in {"current_events", "scientific", "product", "general"}:
        return requested
    if re.search(r"\b20\d{2}\b", text) or _contains_any(text, CURRENT_MARKERS):
        return "current_events"
    if _contains_any(text, SCIENTIFIC_MARKERS):
        return "scientific"
    if _contains_any(text, PRODUCT_MARKERS):
        return "product"
    return "general"


def _recommend_tools(text: str, domain: str) -> list[str]:
    tools: list[str] = []
    if "http://" in text or "https://" in text:
        tools.append("fetch")
    if domain == "scientific":
        tools.extend(["papers", "paper_text"])
    if domain in {"current_events", "product", "general"}:
        tools.append("lookup")
    return list(dict.fromkeys(tools))


def _evidence_needed(domain: str) -> list[str]:
    if domain == "current_events":
        return ["recent primary source", "independent reputable news source", "publication date"]
    if domain == "scientific":
        return ["peer-reviewed paper or preprint", "method/sample details", "independent replication or expert commentary"]
    if domain == "product":
        return ["official product documentation", "release note or pricing page", "date/version"]
    return ["primary source", "independent corroborating source", "date and author"]


def check_claim(claim: str = "", domain: str = "auto", urgency: str = "normal") -> dict:
    claim = (claim or "").strip()
    urgency = urgency if urgency in {"low", "normal", "high"} else "normal"
    normalized = " ".join(claim.split())

    if not normalized:
        return {
            "tool": "claim_check",
            "error": "missing_claim",
            "message": "Provide a factual claim to triage.",
            "missing_fields": ["claim"],
        }

    text = normalized.lower()
    inferred_domain = _infer_domain(text, domain)
    recommended_tools = _recommend_tools(text, inferred_domain)

    risk_score = 1
    if inferred_domain in {"current_events", "scientific"}:
        risk_score += 1
    if urgency == "high" or _contains_any(text, {"breaking", "viral", "urgent", "sap", "ngay lap tuc"}):
        risk_score += 1
    if any(marker in text for marker in ["always", "never", "guaranteed", "100%", "luon luon", "khong bao gio"]):
        risk_score += 1

    risk_level = "low" if risk_score <= 1 else "medium" if risk_score == 2 else "high"
    search_query = re.sub(r"^claim\s*:\s*", "", normalized, flags=re.IGNORECASE)

    return {
        "tool": "claim_check",
        "error": None,
        "claim": normalized,
        "domain": inferred_domain,
        "urgency": urgency,
        "risk_level": risk_level,
        "verification_need": "high" if risk_level == "high" else "normal",
        "recommended_tools": recommended_tools,
        "evidence_needed": _evidence_needed(inferred_domain),
        "search_queries": [search_query],
    }
