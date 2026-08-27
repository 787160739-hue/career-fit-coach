import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PipelineTests(unittest.TestCase):
    def test_merge_deduplicates_and_detects_platforms(self):
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
            temp = Path(temp_dir)
            profile = temp / "profile.json"
            jobs = temp / "jobs.csv"
            output = temp / "scored.csv"
            profile.write_text(
                json.dumps(
                    {
                        "target_titles": ["数字化项目经理"],
                        "preferred_cities": ["成都"],
                        "minimum_monthly_salary_k": 15,
                        "evidence_skills": ["需求分析"],
                        "preferred_tasks": ["系统方案"],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            jobs.write_text(
                "title,company,city,salary,description,url\n"
                "数字化项目经理,示例公司,成都,10-12k,负责需求分析与系统方案,https://example.com/job/1\n",
                encoding="utf-8-sig",
            )

            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "score_jobs.py"), str(profile), str(jobs), "--output", str(output)],
                check=True,
                capture_output=True,
                text=True,
            )
            with output.open(encoding="utf-8-sig", newline="") as handle:
                row = next(csv.DictReader(handle))

            self.assertEqual(row["fit_tier"], "D")
            self.assertEqual(row["hard_conflicts"], "薪资")


if __name__ == "__main__":
    unittest.main()
