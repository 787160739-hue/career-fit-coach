# career-fit-coach

一个面向 Codex 的个人求职决策 Skill：从工作经历与偏好梳理开始，完成职业方向比较、多个招聘网站的岗位数据导入、证据化匹配、岗位质量审查、定向简历、投递决策与反馈学习。

## 能做什么

- 通过渐进式访谈形成可复用的求职画像，区分事实证据、能力、偏好、限制与未知项。
- 用职业方向矩阵比较证据、缺口、转型成本、工作方式、市场证据和不确定性。
- 合并并规范化多个招聘网站导出的 CSV，分别输出资格、能力匹配、偏好匹配、战略价值和投递优先级。
- 审查岗位职责范围、名称与实际工作、决策权、AI真实性等质量与风险信号。
- 根据重点岗位建立“招聘意图—要求—证据—筛选风险—策略”矩阵，生成一页优先的定向简历方案。
- 记录投递事件和面试反馈，用带小样本保护的漏斗分析更新求职策略。

目前随附的浏览器本地导出器识别猎聘、Boss直聘、智联招聘、前程无忧和拉勾的可见岗位详情链接。LinkedIn/领英只支持导入用户自行提供的链接、文本、PDF或平台允许的导出文件，不使用本项目的浏览器导出器采集。

## 边界

本项目不会自动投递、绕过登录或验证码、调用招聘网站隐藏接口，也不会规避频率限制。网站页面结构可能变化；导出器只读取浏览器当前页面已经渲染出的链接，并在本地生成 CSV。

## 安装

将仓库克隆到 Codex 的个人 Skill 目录：

```powershell
git clone https://github.com/787160739-hue/career-fit-coach "$env:USERPROFILE\.codex\skills\career-fit-coach"
```

重新打开 Codex 后，可在对话中使用：

```text
$career-fit-coach 帮我梳理经历和工作偏好，并给出求职方向。
```

也可以直接描述简历优化、岗位匹配或招聘网站 CSV 筛选需求，Codex 会在适用时调用此 Skill。

## 岗位数据工作流

1. 优先提供完整 JD、岗位链接、截图、PDF 或招聘网站导出的 CSV。
2. 列表页难以读取时，打开 `assets/job-list-exporter.html`，把“导出当前岗位”拖到浏览器书签栏。
3. 正常登录招聘网站并打开岗位列表，等待卡片显示后点击该书签。
4. 合并多个导出文件：

```powershell
python scripts/merge_job_csv.py job_list.csv "job_list (1).csv" --output merged_jobs.csv
```

5. 可选：根据画像做确定性预筛；结果会分开显示资格、能力、偏好和战略分数，仍需人工结合完整 JD 复核。

```powershell
python scripts/score_jobs.py profile.json merged_jobs.csv --output scored_jobs.csv
```

`references/schemas.md` 提供了 `profile.json` 与岗位表字段示例。

## 投递反馈工作流

按 `references/schemas.md` 的格式将投递、HR联系、面试和 Offer 记录到 `application_events.csv`，然后生成描述性漏斗：

```powershell
python scripts/analyze_pipeline.py application_events.csv --output pipeline_summary.json
```

默认至少需要5个进入某环节的岗位，才会把该环节列为候选瓶颈。脚本不会把候选人的猜测包装成招聘方反馈，也不会根据一两次拒绝自动改变职业方向。

## 验证

项目测试仅依赖 Python 标准库；导出器测试需要 Node.js：

```powershell
python -m unittest discover -s tests -p "test_*.py"
node tests/test_exporter.mjs
```

测试覆盖跨站导入去重、LinkedIn导入与导出边界、薪资格式、城市/经验/学历/显式非协商条件、能力与偏好分离、未知信息降级以及反馈漏斗的小样本保护。

## 隐私

默认不要把电话号码、个人邮箱、证件信息、雇主机密或精确薪酬历史写入可复用状态。发布岗位数据或画像前请自行脱敏。

## License

[MIT](LICENSE)
