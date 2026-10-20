"""Audit whether career-market records have traceable, recently reviewed sources."""

import json
import math
import re
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CAREERS_PATH = PROJECT_ROOT / "data" / "careers.json"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def audit_career_catalog(careers: dict, today: date | None = None, max_age_days: int = 365) -> dict:
    """Validate that published market claims have claim-specific evidence."""
    today = today or date.today()
    issues = []
    fully_sourced_count = 0
    sourced_claim_count = 0
    unavailable_claim_count = 0

    for career_id, career in careers.items():
        if not isinstance(career, dict):
            issues.append({"career_id": career_id, "field": "record", "issue": "invalid_record"})
            continue

        salary_data = career.get("salary_data")
        if not isinstance(salary_data, dict):
            issues.append({"career_id": career_id, "field": "salary_data", "issue": "missing_or_invalid"})
        else:
            if salary_data.get("schema_version") != 1:
                issues.append({
                    "career_id": career_id,
                    "field": "salary_data.schema_version",
                    "issue": "unsupported_schema_version",
                })
            for field in ("type", "currency", "period", "location", "data_period", "status", "reviewed_at"):
                if not str(salary_data.get(field) or "").strip():
                    issues.append({
                        "career_id": career_id,
                        "field": f"salary_data.{field}",
                        "issue": "missing_value",
                    })
            try:
                datetime.strptime(str(salary_data.get("reviewed_at") or ""), "%Y-%m-%d")
            except ValueError:
                issues.append({
                    "career_id": career_id,
                    "field": "salary_data.reviewed_at",
                    "issue": "invalid_date",
                })
            sample_size = salary_data.get("sample_size")
            if sample_size is not None and (
                isinstance(sample_size, bool)
                or not isinstance(sample_size, int)
                or sample_size < 1
            ):
                issues.append({
                    "career_id": career_id,
                    "field": "salary_data.sample_size",
                    "issue": "invalid_sample_size",
                })
            if salary_data.get("currency") != "VND" or salary_data.get("period") != "month":
                issues.append({
                    "career_id": career_id,
                    "field": "salary_data",
                    "issue": "unsupported_currency_or_period",
                })
            observations = salary_data.get("observations")
            if not isinstance(observations, list):
                issues.append({
                    "career_id": career_id,
                    "field": "salary_data.observations",
                    "issue": "invalid_observations",
                })
            else:
                for index, observation in enumerate(observations):
                    field = f"salary_data.observations[{index}]"
                    if not isinstance(observation, dict):
                        issues.append({"career_id": career_id, "field": field, "issue": "invalid_record"})
                        continue
                    statistic = observation.get("statistic")
                    if statistic not in {
                        "median", "mean", "advertised_range", "advertised_ceiling",
                        "reported_experience_range",
                    }:
                        issues.append({
                            "career_id": career_id,
                            "field": f"{field}.statistic",
                            "issue": "invalid_statistic",
                        })
                    has_value = observation.get("value_vnd_per_month") is not None
                    has_low = observation.get("minimum_vnd_per_month") is not None
                    has_high = observation.get("maximum_vnd_per_month") is not None
                    if (
                        (statistic in {"median", "mean"} and not has_value)
                        or (statistic == "advertised_range" and not (has_low and has_high))
                        or (statistic == "advertised_ceiling" and not has_high)
                        or (statistic == "reported_experience_range" and not (has_low and has_high))
                    ):
                        issues.append({
                            "career_id": career_id,
                            "field": field,
                            "issue": "missing_required_amount",
                        })
                    for amount_field in (
                        "value_vnd_per_month",
                        "minimum_vnd_per_month",
                        "maximum_vnd_per_month",
                    ):
                        value = observation.get(amount_field)
                        if value is not None and (
                            isinstance(value, bool)
                            or not isinstance(value, (int, float))
                            or not math.isfinite(value)
                            or value < 0
                        ):
                            issues.append({
                                "career_id": career_id,
                                "field": f"{field}.{amount_field}",
                                "issue": "invalid_nonnegative_amount",
                            })
                    low = observation.get("minimum_vnd_per_month")
                    high = observation.get("maximum_vnd_per_month")
                    if (
                        isinstance(low, (int, float))
                        and not isinstance(low, bool)
                        and math.isfinite(low)
                        and isinstance(high, (int, float))
                        and not isinstance(high, bool)
                        and math.isfinite(high)
                        and low > high
                    ):
                        issues.append({
                            "career_id": career_id,
                            "field": field,
                            "issue": "minimum_exceeds_maximum",
                        })
                    expiry = observation.get("expires_at")
                    if expiry:
                        try:
                            datetime.strptime(str(expiry), "%Y-%m-%d")
                        except ValueError:
                            issues.append({
                                "career_id": career_id,
                                "field": f"{field}.expires_at",
                                "issue": "invalid_date",
                            })
            if salary_data.get("role_scope") == "related_role_proxy" and not salary_data.get("proxy_role"):
                issues.append({
                    "career_id": career_id,
                    "field": "salary_data.proxy_role",
                    "issue": "missing_proxy_role",
                })

        for field in ("muc_luong", "xu_huong_thi_truong", "khu_vuc"):
            if not str(career.get(field) or "").strip():
                issues.append({"career_id": career_id, "field": field, "issue": "missing_value"})

        sources = career.get("nguon_tham_khao", [])
        if not isinstance(sources, list):
            sources = []
            issues.append({
                "career_id": career_id,
                "field": "nguon_tham_khao",
                "issue": "invalid_source_list",
            })

        source_scopes = set()
        for index, source in enumerate(sources):
            if not isinstance(source, dict):
                issues.append({
                    "career_id": career_id,
                    "field": f"nguon_tham_khao[{index}]",
                    "issue": "invalid_source_record",
                })
                continue

            source_url = str(source.get("url") or "").strip()
            parsed_url = urlparse(source_url)
            if parsed_url.scheme != "https" or not parsed_url.netloc:
                issues.append({
                    "career_id": career_id,
                    "field": f"nguon_tham_khao[{index}].url",
                    "issue": "missing_or_invalid_https_url",
                })

            scope = source.get("pham_vi", [])
            if not isinstance(scope, list):
                scope = []
                issues.append({
                    "career_id": career_id,
                    "field": f"nguon_tham_khao[{index}].pham_vi",
                    "issue": "invalid_claim_scope",
                })
            source_scopes.update(scope)
            if source.get("loai_tham_chieu"):
                comparison_target = str(
                    source.get("nghe_tham_chieu")
                    or source.get("doi_tuong_tham_chieu")
                    or ""
                ).strip()
                if not comparison_target:
                    issues.append({
                        "career_id": career_id,
                        "field": f"nguon_tham_khao[{index}].doi_tuong_tham_chieu",
                        "issue": "missing_comparison_target",
                    })
                else:
                    for field in scope:
                        claim = str(career.get(field) or "")
                        if comparison_target.casefold() not in claim.casefold():
                            issues.append({
                                "career_id": career_id,
                                "field": field,
                                "issue": "comparison_target_not_disclosed_in_claim",
                            })
            if not str(source.get("ten") or "").strip():
                issues.append({
                    "career_id": career_id,
                    "field": f"nguon_tham_khao[{index}].ten",
                    "issue": "missing_source_title",
                })
            if not str(source.get("ky_du_lieu") or "").strip():
                issues.append({
                    "career_id": career_id,
                    "field": f"nguon_tham_khao[{index}].ky_du_lieu",
                    "issue": "missing_source_period",
                })

        review_date = str(career.get("ngay_kiem_tra") or "").strip()
        if sources:
            try:
                checked = datetime.strptime(review_date, "%Y-%m-%d").date()
            except ValueError:
                issues.append({
                    "career_id": career_id,
                    "field": "ngay_kiem_tra",
                    "issue": "missing_or_invalid_date",
                })
            else:
                if checked > today:
                    issues.append({"career_id": career_id, "field": "ngay_kiem_tra", "issue": "date_in_future"})
                elif (today - checked).days > max_age_days:
                    issues.append({"career_id": career_id, "field": "ngay_kiem_tra", "issue": "review_overdue"})

            if not str(career.get("nguon_du_lieu") or "").strip():
                issues.append({"career_id": career_id, "field": "nguon_du_lieu", "issue": "missing_value"})
            updated = str(career.get("thoi_diem_cap_nhat") or "")
            years = [int(year) for year in re.findall(r"\b20\d{2}\b", updated)]
            if not years:
                issues.append({
                    "career_id": career_id,
                    "field": "thoi_diem_cap_nhat",
                    "issue": "missing_update_period",
                })
            elif max(years) > today.year:
                issues.append({
                    "career_id": career_id,
                    "field": "thoi_diem_cap_nhat",
                    "issue": "update_period_in_future",
                })

        claims_complete = True
        for field in ("muc_luong", "xu_huong_thi_truong"):
            claim = str(career.get(field) or "").strip()
            if claim.startswith("Chưa có dữ liệu được xác thực"):
                unavailable_claim_count += 1
                if field in source_scopes:
                    claims_complete = False
                    issues.append({
                        "career_id": career_id,
                        "field": field,
                        "issue": "claim_marked_unavailable_but_cited",
                    })
            elif field not in source_scopes:
                claims_complete = False
                issues.append({
                    "career_id": career_id,
                    "field": field,
                    "issue": "claim_has_no_matching_source",
                })
            else:
                sourced_claim_count += 1

        if claims_complete and not any(item["career_id"] == career_id for item in issues):
            fully_sourced_count += 1

    return {
        "career_count": len(careers),
        "issue_count": len(issues),
        "ready_count": fully_sourced_count,
        "sourced_claim_count": sourced_claim_count,
        "unavailable_claim_count": unavailable_claim_count,
        "issues": issues,
    }


def main() -> int:
    with CAREERS_PATH.open(encoding="utf-8") as file:
        careers = json.load(file)
    result = audit_career_catalog(careers)
    print(
        f"Danh mục nghề: {result['career_count']} | Nghề không còn tuyên bố thiếu nguồn: "
        f"{result['ready_count']} | Thông tin có trích dẫn: {result['sourced_claim_count']} | "
        f"Thông tin đang ẩn do thiếu dữ liệu: {result['unavailable_claim_count']} | "
        f"Vấn đề cần xử lý: {result['issue_count']}"
    )
    for issue in result["issues"]:
        print(
            f"- {issue['career_id']} / {issue['field']}: {issue['issue']}"
        )
    return 0 if result["issue_count"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
