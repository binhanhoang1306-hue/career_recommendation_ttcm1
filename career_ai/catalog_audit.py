"""Audit whether career-market records have traceable, recently reviewed sources."""

import json
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
