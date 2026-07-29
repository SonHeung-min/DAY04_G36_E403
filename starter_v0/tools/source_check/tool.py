from __future__ import annotations

from urllib.parse import urlparse


HIGH_TRUST_SUFFIXES = (".gov", ".edu")
KNOWN_RESEARCH_DOMAINS = {
    "arxiv.org",
    "nature.com",
    "science.org",
    "acm.org",
    "ieee.org",
    "openai.com",
    "anthropic.com",
}
WEAK_SOURCE_DOMAINS = {
    "medium.com",
    "substack.com",
    "reddit.com",
    "x.com",
    "twitter.com",
    "facebook.com",
    "linkedin.com",
}


def _domain(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"https://{url}")
    return (parsed.netloc or parsed.path).lower().removeprefix("www.")


def _assessment(domain: str, purpose: str) -> tuple[str, list[str], list[str]]:
    reasons: list[str] = []
    cautions: list[str] = []

    if domain.endswith(HIGH_TRUST_SUFFIXES):
        rating = "strong"
        reasons.append("official or academic domain")
    elif domain in KNOWN_RESEARCH_DOMAINS or any(domain.endswith(f".{item}") for item in KNOWN_RESEARCH_DOMAINS):
        rating = "strong"
        reasons.append("recognized research or primary source domain")
    elif domain in WEAK_SOURCE_DOMAINS or any(domain.endswith(f".{item}") for item in WEAK_SOURCE_DOMAINS):
        rating = "weak"
        cautions.append("social or user-generated source; verify with primary sources")
    else:
        rating = "medium"
        cautions.append("domain is not in the local trust list; inspect author, date, and citations")

    if purpose == "publishing" and rating != "strong":
        cautions.append("publishing use should cite a stronger primary source when possible")
    if purpose == "citation" and rating == "weak":
        cautions.append("avoid using this as a primary citation unless quoting social reaction")

    return rating, reasons, cautions


def check_sources(urls: list[str] | None = None, purpose: str = "research", max_items: int = 5) -> dict:
    urls = [url for url in (urls or []) if str(url).strip()]
    purpose = purpose if purpose in {"research", "citation", "publishing"} else "research"
    max_items = max(1, min(int(max_items or 5), 10))

    items = []
    for url in urls[:max_items]:
        domain = _domain(str(url).strip())
        rating, reasons, cautions = _assessment(domain, purpose)
        items.append({
            "url": url,
            "domain": domain,
            "purpose": purpose,
            "rating": rating,
            "reasons": reasons,
            "cautions": cautions,
        })

    return {
        "tool": "source_check",
        "error": None,
        "purpose": purpose,
        "item_count": len(items),
        "items": items,
    }
