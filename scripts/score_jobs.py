#!/usr/bin/env python3
"""Deterministic pre-screen for job lists. Human semantic review is still required."""

import argparse
import csv
import json
import re
from pathlib import Path


RISK_TERMS = ["大小周", "单休", "996", "长期出差", "频繁出差", "高强度", "高压", "经常加班"]


def text(value):
    return re.sub(r"\s+", "", str(value or "")).casefold()


def hits(haystack, terms):
    return [term for term in terms if text(term) and text(term) in haystack]


def salary_min_k(value):
    value = str(value or "").replace("–", "-").replace("—", "-").casefold()
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|~|至)\s*\d+(?:\.\d+)?\s*k", value)
    if not match:
        match = re.search(r"(\d+(?:\.\d+)?)\s*k", value)
    return float(match.group(1)) if match else None


def tier(score, hard_conflict):
    if hard_conflict:
        return "D"
    if score >= 75:
        return "A"
    if score >= 58:
        return "B"
    return "C"


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
    evidence_skills = profile.get("evidence_skills", [])
    preferred_tasks = profile.get("preferred_tasks", [])
    cities = profile.get("preferred_cities", [])
    city_is_hard = bool(profile.get("city_is_hard_constraint", False))
    avoid = list(dict.fromkeys(profile.get("avoid_signals", []) + RISK_TERMS))
    salary_floor = profile.get("minimum_monthly_salary_k")

    output = []
    for row in rows:
        title = row.get("title") or row.get("岗位名称") or ""
        city = row.get("city") or row.get("城市") or ""
        salary = row.get("salary") or row.get("薪资") or ""
        description = row.get("description") or row.get("职位描述") or ""
        haystack = text(" ".join([title, description]))

        title_hits = hits(text(title), target_titles)
        skill_hits = hits(haystack, evidence_skills)
        task_hits = hits(haystack, preferred_tasks)
        risk_hits = hits(haystack, avoid)

        role_score = min(35, (25 if title_hits else 0) + 4 * len(task_hits))
        skill_score = min(30, 5 * len(skill_hits))
        location_score = 15 if not cities or any(text(c) in text(city) for c in cities) else 0
        parsed_salary = salary_min_k(salary)
        salary_score = 10
        salary_conflict = False
        if salary_floor is not None and parsed_salary is not None:
            salary_score = 10 if parsed_salary >= float(salary_floor) else 0
            salary_conflict = parsed_salary < float(salary_floor)
        elif salary_floor is not None:
            salary_score = 5

        evidence_score = 10 if description.strip() else 3
        score = max(0, min(100, role_score + skill_score + location_score + salary_score + evidence_score - min(15, 5 * len(risk_hits))))
        city_conflict = bool(cities and city and location_score == 0)
        hard_conflict = salary_conflict or (city_is_hard and city_conflict)
        confidence = "高" if description.strip() and salary else "中" if description.strip() else "低"

        enriched = dict(row)
        enriched.update(
            {
                "match_score": score,
                "fit_tier": tier(score, hard_conflict),
                "confidence": confidence,
                "matched_keywords": " | ".join(dict.fromkeys(title_hits + skill_hits + task_hits)),
                "risk_flags": " | ".join(risk_hits),
                "hard_conflicts": " | ".join(
                    x
                    for x, active in [
                        ("城市", city_is_hard and city_conflict),
                        ("薪资", salary_conflict),
                    ]
                    if active
                ),
                "review_note": "预筛分数；需结合完整JD、公司信息和用户偏好人工复核",
            }
        )
        output.append(enriched)

    output.sort(key=lambda row: (row["fit_tier"], -int(row["match_score"])))
    fields = list(output[0]) if output else list(rows[0]) if rows else []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output)
    print(f"Scored {len(output)} jobs -> {args.output}")


if __name__ == "__main__":
    main()
