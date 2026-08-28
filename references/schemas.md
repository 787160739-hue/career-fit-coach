# Optional local-state schemas

Use these only when the user wants reusable files. JSON is preferred for script inputs; Markdown is preferred for narrative evidence.

## `profile.json`

```json
{
  "years_experience": 2,
  "target_titles": ["AI应用项目经理", "企业数字化项目经理"],
  "preferred_cities": ["成都", "深圳", "杭州", "厦门"],
  "city_is_hard_constraint": false,
  "minimum_monthly_salary_k": 14,
  "evidence_skills": ["需求分析", "厂商选型", "POC", "UAT", "Agent工作流", "数据分析"],
  "preferred_tasks": ["系统方案", "工具搭建", "数据分析"],
  "avoid_signals": ["长期出差", "大小周", "高频无效加班"],
  "hard_constraints": [],
  "notes": "Do not store direct identifiers or confidential data by default."
}
```

## `jobs.csv`

Recommended columns:

```text
platform,title,company,city,salary,experience,education,description,url,source,source_page,exported_at,inspection_date
```

Chinese aliases such as `平台`, `岗位名称`, `公司`, `城市`, `薪资`, `经验`, `职位描述`, `详情页链接`, `来源页面` and `导出时间` are accepted by the bundled merge script.

## `job_pipeline.csv`

Add decision fields after review:

```text
fit_tier,confidence,status,match_evidence,gaps,risk_signals,recruiter_questions,resume_variant,last_action_date
```

Suggested statuses: `待分析`, `重点投递`, `待确认`, `已投递`, `面试中`, `暂停`, `淘汰`.
