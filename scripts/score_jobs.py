#!/usr/bin/env python3
"""Deterministic job-list triage. Semantic human/agent review is still required."""

import argparse
import csv
import json
import re
from pathlib import Path


RISK_TERMS = ["大小周", "单休", "996", "长期出差", "频繁出差", "高强度", "高压", "经常加班"]
DEFAULT_WEIGHTS = {"capability": 0.65, "preference": 0.35, "strategic": 0.0}
TIER_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3}
EDUCATION_RANK = {
    "不限": 0,
    "高中": 1,
    "中专": 1,
    "大专": 2,
    "专科": 2,
    "本科": 3,
    "学士": 3,
    "硕士": 4,
    "研究生": 4,
    "博士": 5,
}


def text(value):
    return re.sub(r"\s+", "", str(value or "")).casefold()


def hits(haystack, terms):
    return [str(term) for term in terms if text(term) and text(term) in haystack]


def salary_monthly_range_k(value):
    value = str(value or "").replace("–", "-").replace("—", "-").casefold()
    monthly = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|~|至)\s*(\d+(?:\.\d+)?)\s*k", value)
    if monthly:
        return float(monthly.group(1)), float(monthly.group(2))
    single_monthly = re.search(r"(\d+(?:\.\d+)?)\s*k", value)
    if single_monthly:
        amount = float(single_monthly.group(1))
        return amount, amount
    annual = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|~|至)\s*(\d+(?:\.\d+)?)\s*(?:万|w)\s*/?\s*年", value)
    if annual:
        return float(annual.group(1)) * 10 / 12, float(annual.group(2)) * 10 / 12
    single_annual = re.search(r"(\d+(?:\.\d+)?)\s*(?:万|w)\s*/?\s*年", value)
    if single_annual:
        amount = float(single_annual.group(1)) * 10 / 12
        return amount, amount
    return None


def experience_min_years(value):
    value = text(value)
    if not value:
        return None
    if "不限" in value or "应届" in value or "在校" in value:
        return 0
    ranged = re.search(r"(\d+)\s*(?:-|~|至)\s*\d+\s*年", value)
    if ranged:
        return int(ranged.group(1))
    minimum = re.search(r"(\d+)\s*年(?:以上|及以上|\+)", value)
    if minimum:
        return int(minimum.group(1))
    single = re.search(r"(\d+)\s*年", value)
    return int(single.group(1)) if single else None


def education_requirement(value):
    normalized = text(value)
    if not normalized:
        return None
    if "不限" in normalized:
        return 0
    matches = [rank for label, rank in EDUCATION_RANK.items() if label != "不限" and label in normalized]
    return max(matches) if matches else None


def normalize_weights(profile):
    supplied = profile.get("score_weights") or {}
    weights = {
        name: max(0.0, float(supplied.get(name, default)))
        for name, default in DEFAULT_WEIGHTS.items()
    }
    total = sum(weights.values())
    if total <= 0:
        return dict(DEFAULT_WEIGHTS)
    return {name: value / total for name, value in weights.items()}


def hard_constraint_terms(profile):
    value = profile.get("hard_constraints", [])
    if isinstance(value, dict):
        value = value.get("exclude_terms", [])
    return [str(item) for item in value if str(item).strip()]


def tier(score, eligibility, confidence):
    if eligibility == "ineligible":
        return "D"
    if score >= 75 and eligibility == "eligible" and confidence != "低":
        return "A"
    if score >= 58:
        return "B"
    return "C"


def confidence_for(row, description):
    populated = sum(bool(row.get(field, "").strip()) for field in ("city", "salary", "experience", "education"))
    if description.strip() and populated >= 3:
        return "高"
    if description.strip() or populated >= 2:
        return "中"
    return "低"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("profile", type=Path)
    parser.add_argument("jobs", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    profile = json.loads(args.profile.read_text(encoding="utf-8-sig"))
    with args.jobs.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    target_titles = profile.get("target_titles", [])
    strategic_titles = profile.get("strategic_target_titles", [])
    evidence_skills = profile.get("evidence_skills", [])
    preferred_tasks = profile.get("preferred_tasks", [])
    cities = profile.get("preferred_cities", [])
    city_is_hard = bool(profile.get("city_is_hard_constraint", False))
    avoid = list(dict.fromkeys(profile.get("avoid_signals", []) + RISK_TERMS))
    explicit_excludes = hard_constraint_terms(profile)
    salary_floor = profile.get("minimum_monthly_salary_k")
    candidate_years = profile.get("years_experience")
    candidate_education = education_requirement(profile.get("education_level", ""))
    experience_is_hard = bool(profile.get("experience_is_hard_constraint", False))
    education_is_hard = bool(profile.get("education_is_hard_constraint", False))
    weights = normalize_weights(profile)

    output = []
    for raw in rows:
        row = dict(raw)
        title = row.get("title") or row.get("岗位名称") or ""
        city = row.get("city") or row.get("城市") or ""
        salary = row.get("salary") or row.get("薪资") or ""
        experience = row.get("experience") or row.get("经验") or ""
        education = row.get("education") or row.get("学历") or ""
        description = row.get("description") or row.get("职位描述") or ""
        normalized = text(" ".join([title, city, salary, experience, education, description]))

        title_hits = hits(text(title), target_titles)
        strategic_hits = hits(text(title), strategic_titles)
        skill_hits = hits(normalized, evidence_skills)
        task_hits = hits(normalized, preferred_tasks)
        risk_hits = hits(normalized, avoid)
        explicit_conflict_hits = hits(normalized, explicit_excludes)

        capability_score = min(
            100,
            (45 if title_hits else 0) + min(35, 7 * len(skill_hits)) + min(20, 5 * len(task_hits)),
        )
        preference_score = max(0, min(100, 50 + min(50, 15 * len(task_hits)) - min(50, 20 * len(risk_hits))))
        strategic_score = 100 if strategic_hits else 40 if strategic_titles else 50

        conflicts = []
        unknowns = []
        hard_unknowns = []
        eligibility_gaps = []

        city_match = not cities or any(text(candidate_city) in text(city) for candidate_city in cities)
        if city_is_hard:
            if not city.strip():
                unknowns.append("城市")
                hard_unknowns.append("城市")
            elif not city_match:
                conflicts.append("城市")

        salary_range = salary_monthly_range_k(salary)
        if salary_floor is not None:
            if salary_range is None:
                unknowns.append("薪资")
                hard_unknowns.append("薪资")
            elif salary_range[1] < float(salary_floor):
                conflicts.append("薪资")

        required_years = experience_min_years(experience)
        if candidate_years is not None:
            if required_years is None:
                unknowns.append("经验要求")
            elif float(candidate_years) < required_years:
                if experience_is_hard:
                    conflicts.append("经验")
                else:
                    eligibility_gaps.append("经验")
                    capability_score = max(0, capability_score - 15)

        required_education = education_requirement(education)
        if candidate_education is not None:
            if required_education is None:
                unknowns.append("学历要求")
            elif candidate_education < required_education:
                if education_is_hard:
                    conflicts.append("学历")
                else:
                    eligibility_gaps.append("学历")
                    capability_score = max(0, capability_score - 15)

        conflicts.extend(f"非协商项:{term}" for term in explicit_conflict_hits)
        conflicts = list(dict.fromkeys(conflicts))
        unknowns = list(dict.fromkeys(unknowns))
        eligibility = "ineligible" if conflicts else "unknown" if hard_unknowns else "eligible"

        priority = round(
            capability_score * weights["capability"]
            + preference_score * weights["preference"]
            + strategic_score * weights["strategic"]
        )
        if eligibility == "ineligible":
            priority = 0

        normalized_row = {
            "city": str(city),
            "salary": str(salary),
            "experience": str(experience),
            "education": str(education),
        }
        confidence = confidence_for(normalized_row, description)
        reasons = []
        if title_hits:
            reasons.append("目标岗位名称命中")
        if skill_hits:
            reasons.append(f"证据技能命中:{','.join(skill_hits)}")
        if task_hits:
            reasons.append(f"偏好任务命中:{','.join(task_hits)}")
        if strategic_hits:
            reasons.append("战略方向命中")

        enriched = dict(row)
        enriched.update(
            {
                "eligibility": eligibility,
                "capability_score": capability_score,
                "preference_score": preference_score,
                "strategic_score": strategic_score,
                "application_priority_score": priority,
                "match_score": priority,
                "fit_tier": tier(priority, eligibility, confidence),
                "confidence": confidence,
                "matched_keywords": " | ".join(dict.fromkeys(title_hits + skill_hits + task_hits + strategic_hits)),
                "score_reasons": " | ".join(reasons),
                "risk_flags": " | ".join(risk_hits),
                "hard_conflicts": " | ".join(conflicts),
                "eligibility_gaps": " | ".join(eligibility_gaps),
                "unknown_fields": " | ".join(unknowns),
                "score_weights": json.dumps(weights, ensure_ascii=False, sort_keys=True),
                "review_note": "确定性预筛；语言、出差频率、岗位质量和完整语义仍需人工复核",
            }
        )
        output.append(enriched)

    output.sort(key=lambda item: (TIER_ORDER[item["fit_tier"]], -int(item["application_priority_score"])))
    fields = list(output[0]) if output else list(rows[0]) if rows else []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output)
    print(f"Scored {len(output)} jobs -> {args.output}")


if __name__ == "__main__":
    main()
