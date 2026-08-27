# Job-data acquisition and fallbacks

## Accepted inputs

- Full job-description text or screenshots.
- Detail-page URLs.
- CSV files exported from a visible job-list page.
- Saved HTML or PDF pages.
- A user-created shortlist with title, company and link.

Normalize to the fields in `schemas.md`. Preserve unknown fields as blank rather than guessing.

## Recruitment-site decision tree

1. If the user already has job descriptions, analyze them directly.
2. If a signed-in visible browser page is available and the user requests help, inspect only visible/interactive content.
3. If a list page cannot be semantically read, ask the user to open it normally and use the local exporter asset. The exporter reads anchors already present in the page and downloads a CSV locally. It supports 猎聘、Boss直聘、智联招聘、前程无忧、拉勾 and LinkedIn/领英; read `site-adapters.md` for the recognized URL forms.
4. If the exporter yields only titles and URLs, analyze a small shortlist first. Detail pages may still be readable individually.
5. If detail pages are blocked, ask the user to copy the job-description text or save/print selected pages; do not keep probing.

## Direct request rules

- Check `robots.txt` before a scripted fetch.
- Use a transparent user agent and low frequency.
- Do not use login cookies or browser credentials in a script.
- Stop on 403, 429, CAPTCHA, risk-control copy, login redirect, JavaScript-only shell or content unrelated to the requested job.
- Save raw diagnostic output only when helpful and avoid retaining personal session data.

The issue is normally the recruitment site's access model and anti-automation controls, not the assistant's identity. Logged-in browser rendering and direct HTTP fetching are different execution paths.

## CSV workflow

For several exports:

```powershell
python scripts/merge_job_csv.py job_list.csv "job_list (1).csv" --output merged_jobs.csv
```

Then enrich the highest-priority rows with description text. A title-only list is suitable for rough filtering, not final fit conclusions.

The merge script records a normalized `platform` field based on the exported URL, so files from different sites can be combined in one pipeline. Keep the original source page and export time when the exporter supplies them.
