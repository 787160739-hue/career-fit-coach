import assert from "node:assert/strict";
import fs from "node:fs";

const html = fs.readFileSync(new URL("../assets/job-list-exporter.html", import.meta.url), "utf8");

for (const token of ["liepin\\\\.com", "zhipin\\\\.com", "zhaopin\\\\.com", "51job\\\\.com", "lagou\\\\.com", "linkedin\\\\.com"]) {
  assert.ok(html.includes(token), `missing site adapter: ${token}`);
}

assert.match(html, /不读取密码/);
assert.match(html, /不绕过网站验证/);
assert.match(html, /u\.search="";u\.hash=""/);
console.log("Exporter checks passed");
