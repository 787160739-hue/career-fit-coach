# Optional local-state schemas

Use these only when the user wants reusable files. JSON is preferred for script inputs; Markdown is preferred for narrative evidence.

## `profile.json`

```json
{
  "years_experience": 2,
  "education_level": "硕士",
  "target_titles": ["AI应用项目经理", "企业数字化项目经理"],
  "strategic_target_titles": ["AI应用产品经理"],
  "preferred_cities": ["成都", "深圳", "杭州", "厦门"],
  "city_is_hard_constraint": false,
  "minimum_monthly_salary_k": 14,
  "experience_is_hard_constraint": false,
  "education_is_hard_constraint": false,
  "evidence_skills": ["需求分析", "厂商选型", "POC", "UAT", "Agent工作流", "数据分析"],
  "preferred_tasks": ["系统方案", "工具搭建", "数据分析"],
  "avoid_signals": ["长期出差", "大小周", "高频无效加班"],
  "hard_constraints": ["大小周", "长期出差"],
  "score_weights": {
    "capability": 0.65,
    "preference": 0.25,
    "strategic": 0.10
  },
  "notes": "Do not store direct identifiers or confidential data by default."
}
```

`hard_constraints` is a list of explicit terms whose presence in the job text is disqualifying. Nuanced constraints such as mandatory language level or travel frequency still require semantic review. `score_weights` are normalized by the scoring script; they guide triage and do not override hard conflicts.

## `career_directions.json`

Use this after comparing plausible role families:

```json
{
  "primary_direction": "企业数字化产品经理",
  "adjacent_direction": "AI应用产品经理",
  "directions": [
    {
      "role_family": "企业数字化产品经理",
      "recommendation": "主攻",
      "evidence_fit": "高",
      "critical_gaps": ["缺少正式产品岗位名称"],
      "transition_cost": "中",
      "resume_explainability": "强",
      "work_style_fit": "高",
      "market_evidence": "待岗位样本验证",
      "option_value": "可延展至AI应用产品",
      "unknowns": ["目标城市实际岗位量"]
    }
  ]
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
job_id,eligibility,eligibility_gaps,capability_score,preference_score,strategic_score,application_priority_score,fit_tier,confidence,status,match_evidence,gaps,risk_signals,quality_signals,quality_unknowns,recruiter_questions,resume_variant,last_action_date
```

Suggested statuses: `待分析`, `重点投递`, `待确认`, `已投递`, `面试中`, `暂停`, `淘汰`.

## `application_events.csv`

Append events instead of overwriting history:

```text
job_id,role_family,event_date,stage,outcome,reason_source,recruiter_feedback,candidate_observation,suspected_gap,next_action
```

Recommended stages: `收集`, `通过筛选`, `已投递`, `HR联系`, `一面`, `二面`, `终面`, `Offer`. Recommended `reason_source` values: `employer_explicit`, `recruiter_explicit`, `candidate_inference`, `unknown`.
