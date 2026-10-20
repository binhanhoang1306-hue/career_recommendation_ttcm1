"""Check market-source availability and flag listing dates for manual review."""

import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CAREERS_PATH = PROJECT_ROOT / "data" / "careers.json"
REQUEST_TIMEOUT = (4, 10)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def classify_http_status(status_code: int) -> str:
    if 200 <= status_code < 400:
        return "reachable"
    if status_code in (401, 403, 429):
        return "blocked_or_rate_limited"
    if status_code in (404, 410):
        return "not_found"
    return "http_error"


def _check_url(url: str) -> dict:
    try:
        response = requests.get(
            url,
            allow_redirects=True,
            timeout=REQUEST_TIMEOUT,
            stream=True,
            headers={"User-Agent": "CareerCatalogSourceCheck/1.0"},
        )
    except requests.exceptions.RequestException as exc:
        return {"url": url, "status": "network_error", "detail": type(exc).__name__}
    try:
        response.raw.decode_content = True
        page_sample = response.raw.read(512 * 1024).decode(
            response.encoding or "utf-8", errors="replace"
        )
        return {
            "url": url,
            "status": classify_http_status(response.status_code),
            "http_status": response.status_code,
            "final_url": response.url,
            "years_in_page_sample": sorted(set(re.findall(r"\b20\d{2}\b", page_sample))),
        }
    except requests.exceptions.RequestException as exc:
        return {"url": url, "status": "network_error", "detail": type(exc).__name__}
    finally:
        response.close()


def check_market_sources(careers: dict, today: date | None = None) -> dict:
    today = today or date.today()
    urls = set()
    for career in careers.values():
        sources = career.get("nguon_tham_khao", []) if isinstance(career, dict) else []
        if not isinstance(sources, list):
            continue
        for source in sources:
            if not isinstance(source, dict) or not isinstance(source.get("url"), str):
                continue
            parsed_url = urlparse(source["url"])
            if parsed_url.scheme == "https" and parsed_url.netloc:
                urls.add(source["url"])
    urls = sorted(urls)
    with ThreadPoolExecutor(max_workers=6) as executor:
        url_results = list(executor.map(_check_url, urls))

    url_results_by_url = {item["url"]: item for item in url_results}
    period_checks = []
    listings = []
    for career_id, career in careers.items():
        sources = career.get("nguon_tham_khao", []) if isinstance(career, dict) else []
        if isinstance(sources, list):
            for source in sources:
                if not isinstance(source, dict) or not source.get("url"):
                    continue
                url_result = url_results_by_url.get(source["url"], {})
                expected_period = str(source.get("ky_du_lieu") or "")
                expected_years = sorted(set(re.findall(r"\b20\d{2}\b", expected_period)))
                observed_years = url_result.get("years_in_page_sample", [])
                if url_result.get("status") != "reachable":
                    status = "not_checked_due_to_access"
                elif not expected_years:
                    status = "period_needs_manual_review"
                elif set(expected_years).issubset(observed_years):
                    status = "period_years_seen_in_page"
                else:
                    status = "period_years_not_all_seen"
                period_checks.append({
                    "career_id": career_id,
                    "url": source["url"],
                    "expected_period": expected_period,
                    "expected_years": expected_years,
                    "observed_years_in_page_sample": observed_years,
                    "status": status,
                    "manual_review_required": True,
                })

        salary_data = career.get("salary_data") if isinstance(career, dict) else None
        if not isinstance(salary_data, dict):
            continue
        observations = salary_data.get("observations", [])
        if not isinstance(observations, list):
            continue
        for index, observation in enumerate(observations):
            if not isinstance(observation, dict) or not str(
                observation.get("statistic", "")
            ).startswith("advertised_"):
                continue
            expiry = observation.get("expires_at")
            try:
                expiry_date = date.fromisoformat(str(expiry)) if expiry else None
            except ValueError:
                expiry_date = None
            listings.append({
                "career_id": career_id,
                "observation": index,
                "expires_at": expiry,
                "status": "expired" if expiry_date and expiry_date < today else (
                    "expiry_unknown" if expiry_date is None else "not_expired_by_recorded_date"
                ),
                "manual_review_required": True,
            })

    return {
        "checked_at": today.isoformat(),
        "url_count": len(url_results),
        "urls": url_results,
        "period_checks": period_checks,
        "listings": listings,
        "manual_review_required": True,
    }


def main() -> int:
    with CAREERS_PATH.open(encoding="utf-8") as file:
        careers = json.load(file)
    result = check_market_sources(careers)
    for item in result["urls"]:
        suffix = f" HTTP {item['http_status']}" if "http_status" in item else ""
        detail = f" ({item['detail']})" if "detail" in item else ""
        print(f"{item['status']}{suffix}: {item['url']}{detail}")
    for item in result["listings"]:
        print(
            f"listing {item['status']}: {item['career_id']} observation "
            f"{item['observation']} (expiry {item['expires_at'] or 'unknown'}; "
            "manual review required)"
        )
    for item in result["period_checks"]:
        print(
            f"period {item['status']}: {item['career_id']} {item['url']} "
            f"(expected years {item['expected_years']}; page sample years "
            f"{item['observed_years_in_page_sample']})"
        )
    counts = {}
    for item in result["urls"]:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    print(f"URL results: {counts}; listing records: {len(result['listings'])}")
    print(
        "Year matches are only a review aid: they do not prove the figure's period or "
        "market claim. Open every source marked for manual review."
    )
    return 1 if any(item["status"] == "not_found" for item in result["urls"]) else 0


if __name__ == "__main__":
    sys.exit(main())
