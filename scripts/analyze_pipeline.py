#!/usr/bin/env python3
"""Summarize application funnel events without claiming causal certainty."""

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


STAGES = ["collected", "screened", "applied", "recruiter_contact", "interview_1", "interview_2", "final", "offer"]
STAGE_LABELS = {
    "collected": "收集",
    "screened": "通过筛选",
    "applied": "已投递",
    "recruiter_contact": "HR联系",
    "interview_1": "一面",
    "interview_2": "二面",
    "final": "终面",
    "offer": "Offer",
}
ALIASES = {
    "收集": "collected",
    "已收集": "collected",
    "collected": "collected",
    "通过筛选": "screened",
    "重点投递": "screened",
    "screened": "screened",
    "已投递": "applied",
    "applied": "applied",
    "hr联系": "recruiter_contact",
    "招聘方联系": "recruiter_contact",
    "recruiter_contact": "recruiter_contact",
    "一面": "interview_1",
    "初面": "interview_1",
    "interview_1": "interview_1",
    "二面": "interview_2",
    "interview_2": "interview_2",
    "终面": "final",
    "final": "final",
    "offer": "offer",
    "录用": "offer",
}


def normalize_stage(value):
    return ALIASES.get(str(value or "").strip().casefold())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("events", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--minimum-sample", type=int, default=5)
    args = parser.parse_args()

    with args.events.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    highest_stage = {}
    explicit_reasons = Counter()
    inferred_reasons = Counter()
    ignored_events = 0
    for row in rows:
        job_id = str(row.get("job_id") or "").strip()
        stage = normalize_stage(row.get("stage"))
        if not job_id or stage is None:
            ignored_events += 1
            continue
        highest_stage[job_id] = max(highest_stage.get(job_id, -1), STAGES.index(stage))
        reason = str(row.get("suspected_gap") or row.get("outcome") or "").strip()
        source = str(row.get("reason_source") or "unknown").strip()
        if reason:
            if source in {"employer_explicit", "recruiter_explicit"}:
                explicit_reasons[reason] += 1
            elif source == "candidate_inference":
                inferred_reasons[reason] += 1

    counts = {
        stage: sum(max_stage >= index for max_stage in highest_stage.values())
        for index, stage in enumerate(STAGES)
    }
    transitions = []
    bottleneck = None
    for current, following in zip(STAGES, STAGES[1:]):
        denominator = counts[current]
        numerator = counts[following]
        rate = round(numerator / denominator, 4) if denominator else None
        item = {
            "from": current,
            "to": following,
            "from_label": STAGE_LABELS[current],
            "to_label": STAGE_LABELS[following],
            "from_count": denominator,
            "to_count": numerator,
            "conversion_rate": rate,
            "sample_sufficient": denominator >= args.minimum_sample,
        }
        transitions.append(item)
        if item["sample_sufficient"] and rate is not None and (bottleneck is None or rate < bottleneck["conversion_rate"]):
            bottleneck = item

    warnings = []
    if len(highest_stage) < args.minimum_sample:
        warnings.append("总体样本不足；只能描述当前结果，不能据此改变职业方向。")
    if bottleneck is None:
        warnings.append("没有达到最低样本量的漏斗环节，暂不判断瓶颈。")
    if ignored_events:
        warnings.append(f"忽略了 {ignored_events} 条缺少 job_id 或无法识别阶段的事件。")

    result = {
        "jobs_observed": len(highest_stage),
        "minimum_sample": args.minimum_sample,
        "stage_counts": {STAGE_LABELS[stage]: count for stage, count in counts.items()},
        "transitions": transitions,
        "bottleneck": bottleneck,
        "explicit_reason_counts": dict(explicit_reasons.most_common()),
        "candidate_inference_counts": dict(inferred_reasons.most_common()),
        "warnings": warnings,
        "interpretation_note": "漏斗描述相关性，不证明拒绝原因；优先使用招聘方明确反馈并从最小层级调整策略。",
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Analyzed {len(highest_stage)} jobs -> {args.output}")


if __name__ == "__main__":
    main()
