# -*- coding: utf-8 -*-
"""Logic quyết định dùng chung cho các API quyết định.

Phần điều chỉnh xác suất theo sở thích và kỹ năng mềm được đặt ở đây để chỉ có một cách tính duy nhất.

Quy tắc:
  - Mô hình học máy (Tầng 1) cho xác suất 7 nhóm nghề từ 12 điểm môn.
  - Sở thích (+INTEREST_BOOST, tương đối) và kỹ năng mềm (theo cấp độ) điều chỉnh điểm xếp hạng
    bằng QUY TẮC sau khi mô hình đã dự đoán; kết quả điều chỉnh không còn là xác suất đã hiệu chuẩn.
    Các yếu tố này không nằm trong dữ liệu huấn luyện.
  - Kỹ năng "Chưa đánh giá" (không có giá trị hợp lệ) bị bỏ qua hoàn toàn: không cộng, không trừ.
"""
from .domain_knowledge import INTEREST_BOOST, SKILL_LEVEL_MULTIPLIERS, SOFT_SKILL_GROUP_BOOST


def clean_skill_levels(skills: dict | None) -> dict:
    """Chỉ giữ các kỹ năng có cấp độ hợp lệ (weak/medium/strong/excellent). 'Chưa đánh giá' bị loại bỏ."""
    return {k: v for k, v in (skills or {}).items() if v in SKILL_LEVEL_MULTIPLIERS}


def apply_interest_and_skill_boost(ranked_groups: list, interests_selected: list, skill_levels: dict = None) -> list:
    """Điều chỉnh và chuẩn hoá điểm xếp hạng nhóm theo sở thích/kỹ năng.

    `ranked_groups` nhận phân phối xác suất mô hình, nhưng đầu ra đã được điều chỉnh
    là thứ hạng theo quy tắc, không còn mang ý nghĩa xác suất đã hiệu chuẩn.
    """
    boosted = []
    for g, p in ranked_groups:
        factor = 1.0
        if interests_selected and g in interests_selected:
            factor += INTEREST_BOOST
        if skill_levels:
            for sk, level in skill_levels.items():
                mult = SKILL_LEVEL_MULTIPLIERS.get(level, 0.08)
                sk_boost = SOFT_SKILL_GROUP_BOOST.get(sk, {}).get(g, 0.0)
                factor += sk_boost * mult * 3.0  # Tác động rõ rệt vào việc xếp hạng nhóm ngành
        boosted.append((g, p * factor))
    total = sum(p for _, p in boosted) or 1.0
    boosted = [(g, p / total) for g, p in boosted]
    boosted.sort(key=lambda x: -x[1])
    return boosted
