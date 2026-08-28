# Recruitment-site adapters

Read this reference when the user names a platform, an exported CSV has unknown links, or the browser exporter stops finding job cards.

## Supported platforms

| Platform | Recognized host | Typical detail path | Bundled exporter |
|---|---|---|---|
| 猎聘 | `liepin.com` | `/job/<id>.shtml`, `/a/<id>.shtml` | Supported, subject to current site rules |
| Boss直聘 | `zhipin.com` | `/job_detail/<id>.html` | Supported, subject to current site rules |
| 智联招聘 | `zhaopin.com` | `/jobdetail/<id>.htm` or `.html` | Supported, subject to current site rules |
| 前程无忧 | `51job.com` | `/pc/jobdetail/...`, `/job/...`, `/jobs/...` and legacy numeric `.html` details | Supported, subject to current site rules |
| 拉勾 | `lagou.com` | `/jobs/<id>.html`, `/wn/jobs/<id>.html` | Supported, subject to current site rules |
| LinkedIn / 领英 | `linkedin.com`, including `cn.linkedin.com` | `/jobs/view/<slug-or-id>` | **Import only; do not use browser exporter** |

These patterns describe visible job-detail links, not permission to crawl the sites. Platform routes and DOM structures can change; test against a currently visible list page before claiming support.

`merge_job_csv.py` may normalize a LinkedIn URL that the user supplies. That import support is separate from browser collection and does not authorize scraping or automated activity on LinkedIn.

## Export behavior

The local exporter:

- scans only anchors already rendered in the current page;
- requires both a recognized host and a recognized detail path;
- strips tracking query strings and fragments for deduplication;
- exports platform, title, canonical detail URL, source page and export time;
- does not scroll, paginate, sign in, open hidden APIs or transmit data.

If a site virtualizes cards, ask the user to scroll through the desired results before exporting. If no matching links are present after cards are visible, use copied job text, screenshots or a site-native saved list instead of weakening the pattern to every link on the page.

## Maintenance rule

When adding or changing a platform:

1. Confirm a current detail URL from the platform's own site.
2. Add the narrowest practical host/path rule to the exporter.
3. Add the same host mapping to `merge_job_csv.py` only when imported links should be recognized; importer support and exporter permission are separate decisions.
4. Test one valid URL, one irrelevant same-site URL and one tracking-query duplicate.
5. Update this table and keep the access-control fallback unchanged.
