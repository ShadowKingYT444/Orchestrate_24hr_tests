import html
import json
from pathlib import Path

def write_report(report, destination):
    dest = Path(destination)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    rows = []
    for category, checks in report["checks"].items():
        for check in checks:
            values = [category, check["name"], check["status"], check["kind"], " | ".join(check["evidence"])]
            rows.append("<tr>" + "".join("<td>" + html.escape(str(v)) + "</td>" for v in values) + "</tr>")
    content = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Orchestrate local evaluation</title><style>body{font:16px system-ui;max-width:1200px;margin:2rem auto;padding:1rem;color:#172033}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccd3df;padding:.65rem;text-align:left;overflow-wrap:anywhere}th{background:#edf2fa}code{white-space:pre-wrap}</style><h1>Orchestrate local evaluation</h1><p>Diagnostic evidence only. No official score or winner prediction. Voice/interview excluded (30%); remaining categories retain their original weights. No silent renormalization.</p>'
    content += '<p>Status: ' + html.escape(report["status"]) + '</p><p>Profile: ' + html.escape(report["profile"]) + '</p>'
    content += '<h2>Local check counts</h2><p>Counts are diagnostics, not quality grades or points. Adding trivial checks does not improve an official score.</p><pre>' + html.escape(json.dumps(report.get("scorecards", {}), indent=2)) + '</pre>'
    content += '<table><thead><tr><th>Category</th><th>Check</th><th>Status</th><th>Evidence type</th><th>Evidence</th></tr></thead><tbody>' + "".join(rows) + '</tbody></table>'
    content += '<h2>Coverage and limitations</h2><pre>' + html.escape(json.dumps(report["coverage"], indent=2)) + '</pre></html>'
    if report.get("metrics") is not None:
        content = content.removesuffix('</html>') + '<h2>Local labelled output metrics</h2><pre>' + html.escape(json.dumps(report["metrics"], indent=2)) + '</pre></html>'
    (dest / "report.html").write_text(content, encoding="utf-8")


def write_comparison(report, destination):
    dest = Path(destination)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "comparison.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    content = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Local configuration comparison</title><h1>Local configuration comparison</h1><p>Exact matches against supplied local labels. No official score or quality ranking.</p><pre>'
    content += html.escape(json.dumps(report, indent=2)) + '</pre></html>'
    (dest / "comparison.html").write_text(content, encoding="utf-8")
