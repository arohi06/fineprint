"""Builds a standalone, printable HTML privacy report (Print -> Save as PDF)."""
from html import escape as e
import time


def build_report(r):
    color = "#2f5d50" if r["score"] >= 70 else "#b9822a" if r["score"] >= 45 else "#c4562f"
    clauses = "".join(
        f"<li><b>{e(c['label_name'])}</b> <i>({e(c['risk'])})</i><br>“{e(c['text'])}”<br>"
        f"<span class='pl'>{e(c['plain'])}</span></li>" for c in r["clauses"])
    trackers = "".join(f"<li>{e(t['name'])} - {e(t['category'])}</li>" for t in r["trackers"]) or "<li>None detected</li>"
    summary = "".join(f"<li>{e(s)}</li>" for s in r["summary"])
    recs = "".join(f"<li>{e(s)}</li>" for s in r["recommendations"])
    perms = ", ".join(e(p) for p in r["permissions"]) or "None detected"
    when = time.strftime("%d %b %Y, %H:%M", time.localtime(r.get("created_at", time.time())))
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Fineprint report - {e(r['domain'])}</title>
<style>
body{{font:15px/1.6 Georgia,serif;color:#1c2620;background:#f3eee4;max-width:760px;margin:40px auto;padding:0 24px}}
h1{{font-size:34px;margin:0}} h2{{border-bottom:1px solid #d8d0bf;padding-bottom:6px;margin-top:34px}}
.score{{font-size:64px;color:{color};line-height:1}} .pl{{color:#6b7268}} li{{margin:8px 0}}
small{{color:#6b7268}}
</style></head><body>
<small>fineprint. privacy assessment - {when}</small>
<h1>{e(r['domain'])}</h1>
<p><span class="score">{r['score']}</span> / 100 &nbsp; <b>{e(r['grade'])}</b><br>{e(r['verdict'])}</p>
<h2>Plain-English summary</h2><ul>{summary}</ul>
<h2>Risky &amp; notable clauses</h2><ul>{clauses or '<li>None found</li>'}</ul>
<h2>Third-party trackers</h2><ul>{trackers}</ul>
<h2>Data categories mentioned</h2><p>{perms}</p>
<h2>Recommendations</h2><ul>{recs}</ul>
<p><small>Automated analysis - a guide, not legal advice. Source: {e(r['url'])}</small></p>
</body></html>"""
