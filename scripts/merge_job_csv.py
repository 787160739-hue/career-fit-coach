#!/usr/bin/env python3
"""Merge exported job CSV files, normalize common headers, and deduplicate rows."""

import argparse
import csv
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


ALIASES = {
    "platform": ["platform", "平台", "招聘网站", "网站"],
    "title": ["title", "job_title", "岗位名称", "职位名称", "职位"],
    "company": ["company", "公司", "公司名称"],
    "city": ["city", "城市", "地点", "工作地点"],
    "salary": ["salary", "薪资", "薪酬"],
    "experience": ["experience", "经验", "工作经验"],
    "education": ["education", "学历"],
    "description": ["description", "职位描述", "岗位描述", "JD"],
    "url": ["url", "link", "详情页链接", "职位链接", "岗位链接"],
    "source": ["source", "来源"],
    "source_page": ["source_page", "来源页面", "列表页链接"],
    "exported_at": ["exported_at", "导出时间", "采集时间"],
    "inspection_date": ["inspection_date", "采集日期", "查看日期"],
}


PLATFORM_HOSTS = {
    "liepin": ("liepin.com",),
    "boss": ("zhipin.com",),
    "zhaopin": ("zhaopin.com",),
    "51job": ("51job.com",),
    "lagou": ("lagou.com",),
    "linkedin": ("linkedin.com",),
}

CANONICAL_HOSTS = {
    "liepin": "www.liepin.com",
    "boss": "www.zhipin.com",
    "zhaopin": "www.zhaopin.com",
    "51job": "we.51job.com",
    "lagou": "www.lagou.com",
    "linkedin": "www.linkedin.com",
}


def platform_from_hostname(hostname):
    hostname = (hostname or "").casefold()
    for platform, suffixes in PLATFORM_HOSTS.items():
        if any(hostname == suffix or hostname.endswith("." + suffix) for suffix in suffixes):
            return platform
    return "other" if hostname else ""


def pick(row, names):
    for name in names:
        value = row.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def canonical_url(value):
    value = value.strip()
    if not value:
        return ""
    parts = urlsplit(value)
    platform = platform_from_hostname(parts.hostname)
    hostname = CANONICAL_HOSTS.get(platform, parts.netloc.lower())
    return urlunsplit((parts.scheme.lower(), hostname, parts.path.rstrip("/"), "", ""))


def detect_platform(value):
    return platform_from_hostname(urlsplit(value).hostname)


def read_rows(path):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            return []
        rows = []
        for raw in reader:
            row = {field: pick(raw, aliases) for field, aliases in ALIASES.items()}
            if not row["source"]:
                row["source"] = path.name
            row["url"] = canonical_url(row["url"])
            if not row["platform"]:
                row["platform"] = detect_platform(row["url"])
            if row["title"] or row["url"]:
                rows.append(row)
        return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    merged = []
    seen = set()
    for path in args.inputs:
        for row in read_rows(path):
            key = row["url"] or "|".join(
                row[field].casefold() for field in ("title", "company", "city")
            )
            if key in seen:
                continue
            seen.add(key)
            merged.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(ALIASES))
        writer.writeheader()
        writer.writerows(merged)
    print(f"Merged {len(merged)} unique jobs -> {args.output}")


if __name__ == "__main__":
    main()
