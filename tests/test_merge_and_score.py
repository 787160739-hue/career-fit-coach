import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_score(temp, profile_data, jobs_text):
    profile = temp / "profile.json"
    jobs = temp / "jobs.csv"
    output = temp / "scored.csv"
    profile.write_text(json.dumps(profile_data, ensure_ascii=False), encoding="utf-8")
    jobs.write_text(jobs_text, encoding="utf-8-sig")
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "score_jobs.py"), str(profile), str(jobs), "--output", str(output)],
        check=True,
        capture_output=True,
        text=True,
    )
    with output.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


class PipelineTests(unittest.TestCase):
    def test_merge_deduplicates_and_detects_import_platforms(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            first = temp / "first.csv"
            second = temp / "second.csv"
            output = temp / "merged.csv"
            first.write_text(
                "岗位名称,公司,城市,详情页链接\n"
                "数字化项目经理,示例甲,成都,https://www.liepin.com/job/123.shtml?track=x\n"
                "AI产品经理,示例乙,深圳,https://www.zhipin.com/job_detail/abc.html\n",
                encoding="utf-8-sig",
            )
            second.write_text(
                "title,company,city,url\n"
                "重复岗位,示例甲,成都,https://www.liepin.com/job/123.shtml?other=y\n"
                "数据产品经理,示例丙,杭州,https://www.linkedin.com/jobs/view/data-product-manager-456/?trk=x\n",
                encoding="utf-8-sig",
            )

            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "merge_job_csv.py"), str(first), str(second), "--output", str(output)],
                check=True,
                capture_output=True,
                text=True,
            )
            with output.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))

            self.assertEqual(len(rows), 3)
            self.assertEqual({row["platform"] for row in rows}, {"liepin", "boss", "linkedin"})
            self.assertTrue(all("?" not in row["url"] for row in rows))

    def test_score_marks_salary_hard_conflict(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            rows = run_score(
                Path(temp_dir),
                {
                    "target_titles": ["数字化项目经理"],
                    "preferred_cities": ["成都"],
                    "minimum_monthly_salary_k": 15,
                    "evidence_skills": ["需求分析"],
                    "preferred_tasks": ["系统方案"],
                },
                "title,company,city,salary,description,url\n"
                "数字化项目经理,示例公司,成都,10-12k,负责需求分析与系统方案,https://example.com/job/1\n",
            )
            self.assertEqual(rows[0]["eligibility"], "ineligible")
            self.assertEqual(rows[0]["fit_tier"], "D")
            self.assertEqual(rows[0]["hard_conflicts"], "薪资")

    def test_score_separates_capability_preference_and_explicit_constraint(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            rows = run_score(
                Path(temp_dir),
                {
                    "target_titles": ["AI产品经理"],
                    "strategic_target_titles": ["AI产品经理"],
                    "evidence_skills": ["需求分析", "Agent工作流"],
                    "preferred_tasks": ["系统方案"],
                    "avoid_signals": ["大小周"],
                    "hard_constraints": ["大小周"],
                    "score_weights": {"capability": 0.5, "preference": 0.3, "strategic": 0.2},
                },
                "title,description,url\n"
                "AI产品经理,负责需求分析、Agent工作流和系统方案，实行大小周,https://example.com/job/2\n",
            )
            row = rows[0]
            self.assertGreater(int(row["capability_score"]), int(row["preference_score"]))
            self.assertEqual(row["strategic_score"], "100")
            self.assertEqual(row["fit_tier"], "D")
            self.assertIn("非协商项:大小周", row["hard_conflicts"])

    def test_missing_hard_screen_data_cannot_be_tier_a(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            rows = run_score(
                Path(temp_dir),
                {
                    "years_experience": 3,
                    "education_level": "本科",
                    "minimum_monthly_salary_k": 15,
                    "target_titles": ["AI产品经理"],
                    "evidence_skills": ["需求分析", "Agent工作流", "数据分析", "POC", "UAT"],
                    "preferred_tasks": ["系统方案", "工具搭建"],
                },
                "title,description,url\n"
                "AI产品经理,负责需求分析、Agent工作流、数据分析、POC、UAT、系统方案和工具搭建,https://example.com/job/3\n",
            )
            row = rows[0]
            self.assertEqual(row["eligibility"], "unknown")
            self.assertNotEqual(row["fit_tier"], "A")
            self.assertIn("薪资", row["unknown_fields"])
            self.assertIn("经验要求", row["unknown_fields"])

    def test_experience_and_education_are_stretch_gaps_by_default(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            rows = run_score(
                Path(temp_dir),
                {"years_experience": 2, "education_level": "本科"},
                "title,experience,education,description,url\n"
                "数据产品经理,3-5年,硕士,负责数据产品,https://example.com/job/4\n",
            )
            self.assertNotEqual(rows[0]["fit_tier"], "D")
            self.assertIn("经验", rows[0]["eligibility_gaps"])
            self.assertIn("学历", rows[0]["eligibility_gaps"])

    def test_experience_and_education_can_be_explicit_hard_constraints(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            rows = run_score(
                Path(temp_dir),
                {
                    "years_experience": 2,
                    "education_level": "本科",
                    "experience_is_hard_constraint": True,
                    "education_is_hard_constraint": True,
                },
                "title,experience,education,description,url\n"
                "数据产品经理,3-5年,硕士,负责数据产品,https://example.com/job/4b\n",
            )
            self.assertEqual(rows[0]["fit_tier"], "D")
            self.assertIn("经验", rows[0]["hard_conflicts"])
            self.assertIn("学历", rows[0]["hard_conflicts"])

    def test_annual_salary_is_normalized_for_floor_check(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            rows = run_score(
                Path(temp_dir),
                {"minimum_monthly_salary_k": 14},
                "title,salary,description,url\n"
                "岗位甲,18-24万/年,职责明确,https://example.com/job/5\n"
                "岗位乙,12-15万/年,职责明确,https://example.com/job/6\n",
            )
            by_title = {row["title"]: row for row in rows}
            self.assertNotIn("薪资", by_title["岗位甲"]["hard_conflicts"])
            self.assertIn("薪资", by_title["岗位乙"]["hard_conflicts"])

    def test_pipeline_analysis_finds_only_sufficient_sample_bottleneck(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            events = temp / "events.csv"
            output = temp / "summary.json"
            lines = ["job_id,stage,outcome,reason_source,suspected_gap"]
            for index in range(1, 6):
                lines.append(f"job-{index},已投递,,,")
            lines.extend(
                [
                    "job-1,HR联系,未进入面试,recruiter_explicit,年限不足",
                    "job-2,HR联系,等待安排,candidate_inference,技术深度",
                ]
            )
            events.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "analyze_pipeline.py"), str(events), "--output", str(output)],
                check=True,
                capture_output=True,
                text=True,
            )
            summary = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(summary["jobs_observed"], 5)
            self.assertEqual(summary["bottleneck"]["from"], "applied")
            self.assertEqual(summary["bottleneck"]["to"], "recruiter_contact")
            self.assertEqual(summary["explicit_reason_counts"]["年限不足"], 1)
            self.assertEqual(summary["candidate_inference_counts"]["技术深度"], 1)

    def test_pipeline_small_sample_does_not_claim_bottleneck(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            events = temp / "events.csv"
            output = temp / "summary.json"
            events.write_text("job_id,stage\njob-1,已投递\njob-2,HR联系\n", encoding="utf-8-sig")
            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "analyze_pipeline.py"), str(events), "--output", str(output)],
                check=True,
                capture_output=True,
                text=True,
            )
            summary = json.loads(output.read_text(encoding="utf-8"))
            self.assertIsNone(summary["bottleneck"])
            self.assertTrue(any("样本不足" in warning for warning in summary["warnings"]))


if __name__ == "__main__":
    unittest.main()
