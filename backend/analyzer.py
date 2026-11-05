"""Crawler + scoring engine: URL in, full privacy assessment out."""
import ipaddress
import os
import re
import socket
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .ml_model import LABELS, classify_sentences

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; FineprintBot/1.0; +privacy-research)"}
ALLOW_LOCAL = os.environ.get("FINEPRINT_ALLOW_LOCAL") == "1"  # only for testing

TRACKERS = {
    "google-analytics.com": ("Google Analytics", "Analytics"),
    "googletagmanager.com": ("Google Tag Manager", "Analytics"),
    "doubleclick.net": ("DoubleClick", "Advertising"),
    "googlesyndication.com": ("Google AdSense", "Advertising"),
    "connect.facebook.net": ("Meta Pixel", "Advertising"),
    "facebook.com/tr": ("Meta Pixel", "Advertising"),
    "hotjar.com": ("Hotjar", "Session replay"),
    "clarity.ms": ("Microsoft Clarity", "Session replay"),
    "fullstory.com": ("FullStory", "Session replay"),
    "segment.com": ("Segment", "Data pipeline"),
    "mixpanel.com": ("Mixpanel", "Analytics"),
    "amplitude.com": ("Amplitude", "Analytics"),
    "criteo.com": ("Criteo", "Advertising"),
    "taboola.com": ("Taboola", "Advertising"),
    "outbrain.com": ("Outbrain", "Advertising"),
    "adnxs.com": ("Xandr", "Advertising"),
    "scorecardresearch.com": ("Scorecard Research", "Analytics"),
    "analytics.tiktok.com": ("TikTok Pixel", "Advertising"),
    "snap.licdn.com": ("LinkedIn Insight", "Advertising"),
    "ads-twitter.com": ("X Ads", "Advertising"),
    "ct.pinterest.com": ("Pinterest Tag", "Advertising"),
    "hs-scripts.com": ("HubSpot", "Marketing"),
    "quantserve.com": ("Quantcast", "Advertising"),
    "bat.bing.com": ("Microsoft Ads", "Advertising"),
    "amazon-adsystem.com": ("Amazon Ads", "Advertising"),
}

CONSENT_BANNERS = ["cookiebot", "onetrust", "cookieconsent", "cookie-consent", "cc-window", "truste",
                   "quantcast choice", "we use cookies", "accept all cookies", "cookie settings",
                   "cookie preferences", "didomi", "usercentrics"]

PERMISSIONS = {
    "Precise location": r"\b(precise|geo)?\s?location\b|\bgps\b",
    "Camera": r"\bcamera\b",
    "Microphone": r"\bmicrophone\b|voice recordings?",
    "Contacts": r"\bcontacts?\b|address book",
    "Photos & media": r"\bphotos?\b|media library",
    "Biometrics": r"biometric|face ?print|fingerprint",
    "Device identifiers": r"device id|advertising id|\bimei\b|ip address",
    "Browsing history": r"browsing (history|activity)",
    "Payment details": r"credit card|payment (information|details)|bank account",
    "Health data": r"health (data|information)",
}
SENSITIVE_PERMS = {"Precise location", "Camera", "Microphone", "Contacts", "Biometrics", "Health data"}

BENCHMARKS = [  # illustrative reference ranges, not scans of real companies
    {"name": "Ad-driven social platforms", "score": 32},
    {"name": "Typical e-commerce", "score": 55},
    {"name": "News & media sites", "score": 46},
    {"name": "Privacy-first services", "score": 86},
]


class ScanError(Exception):
    pass


def safe_url(url):
    url = url.strip()
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    p = urlparse(url)
    if not p.hostname or "." not in p.hostname and not ALLOW_LOCAL:
        raise ScanError("That doesn't look like a valid website address.")
    if not ALLOW_LOCAL:
        try:
            infos = socket.getaddrinfo(p.hostname, None)
        except socket.gaierror:
            raise ScanError("Couldn't find that domain. Check the spelling?")
        for i in infos:
            ip = ipaddress.ip_address(i[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                raise ScanError("Private or local addresses can't be scanned.")
    return url


def _get(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=12, allow_redirects=True)
    except requests.RequestException:
        raise ScanError("We couldn't reach that website. It may be down or blocking automated visitors.")
    if not ALLOW_LOCAL:
        safe_url(r.url)  # re-check after redirects
    return r


def _find_links(soup, base):
    found = {"privacy": None, "terms": None, "cookie": None}
    for a in soup.find_all("a", href=True):
        text = (a.get_text(" ", strip=True) + " " + a["href"]).lower()
        href = urljoin(base, a["href"])
        if not href.startswith("http"):
            continue
        if "cookie" in text and not found["cookie"]:
            found["cookie"] = href
        elif "privacy" in text and not found["privacy"]:
            found["privacy"] = href
        elif re.search(r"terms|conditions|\btos\b", text) and not found["terms"]:
            found["terms"] = href
    return found


def _page_text(html):
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "nav", "header", "footer", "svg", "form"]):
        tag.decompose()
    return re.sub(r"\s+", " ", soup.get_text(" ")).strip()[:80_000]


def _sentences(text):
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9"\u201c])', text)
    seen, out = set(), []
    for s in parts:
        s = s.strip()
        if 35 <= len(s) <= 450 and s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
    return out[:600]


def analyze(raw_url):
    url = safe_url(raw_url)
    resp = _get(url)
    final_url = resp.url
    html = resp.text[:1_500_000]
    soup = BeautifulSoup(html, "html.parser")
    domain = urlparse(final_url).hostname

    # 1. locate policies
    links = _find_links(soup, final_url)
    if not links["privacy"]:
        for path in ("/privacy-policy", "/privacy", "/legal/privacy"):
            try:
                t = requests.get(urljoin(final_url, path), headers=HEADERS, timeout=8)
                if t.status_code == 200 and len(t.text) > 2000:
                    links["privacy"] = t.url
                    break
            except requests.RequestException:
                pass

    # 2. fetch policy text
    texts = []
    for key in ("privacy", "terms", "cookie"):
        if links[key]:
            try:
                r = requests.get(links[key], headers=HEADERS, timeout=12)
                if r.ok:
                    texts.append(_page_text(r.text))
            except requests.RequestException:
                pass
    policy_text = " ".join(texts)

    # 3. NLP - clause classification
    clauses = classify_sentences(_sentences(policy_text))
    for c in clauses:
        meta = LABELS[c["label"]]
        c.update(label_name=meta["name"], risk=meta["risk"], plain=meta["plain"])
    order = {"high": 0, "medium": 1, "low": 2, "info": 3, "positive": 4}
    clauses.sort(key=lambda c: (order[c["risk"]], -c["confidence"]))

    # 4. trackers
    lower = html.lower()
    trackers, seen = [], set()
    for frag, (name, cat) in TRACKERS.items():
        if frag in lower and name not in seen:
            seen.add(name)
            trackers.append({"domain": frag, "name": name, "category": cat})

    # 5. cookies
    jar = list(resp.cookies)
    cookies = {
        "count": len(jar),
        "insecure": sum(1 for c in jar if not c.secure),
        "banner_detected": any(k in lower for k in CONSENT_BANNERS),
        "list": [{"name": c.name, "secure": bool(c.secure),
                  "httponly": c.has_nonstandard_attr("HttpOnly")} for c in jar][:12],
    }

    # 6. permissions
    permissions = [name for name, rx in PERMISSIONS.items() if re.search(rx, policy_text, re.I)]

    # 7. scoring
    checks = {"https": final_url.startswith("https://"), "policy_found": bool(links["privacy"]),
              "terms_found": bool(links["terms"])}
    score, breakdown = 100.0, []

    def add(name, pts):
        nonlocal score
        if pts:
            breakdown.append({"name": name, "points": round(pts, 1)})
            score += pts

    if not checks["https"]:
        add("Site not served over HTTPS", -15)
    if not checks["policy_found"]:
        add("No privacy policy found", -25)
    by_label = {}
    for c in clauses:
        by_label.setdefault(c["label"], []).append(c)
    bonus = 0.0
    for label, items in by_label.items():
        w = LABELS[label]["weight"]
        scaled = w * min(1 + 0.25 * (len(items) - 1), 1.75)
        if w > 0:
            add(LABELS[label]["name"], -scaled)
        elif w < 0:
            bonus += -w * min(1 + 0.2 * (len(items) - 1), 1.6)
    if bonus:
        add("Good privacy practices", min(bonus, 12))
    if trackers:
        add(f"{len(trackers)} third-party tracker(s)", -min(len(trackers) * 2.5, 20))
        if not cookies["banner_detected"]:
            add("Trackers without a visible consent banner", -6)
    if cookies["insecure"]:
        add("Cookies without the Secure flag", -min(cookies["insecure"] * 1.5, 6))
    sens = [p for p in permissions if p in SENSITIVE_PERMS]
    if sens:
        add("Sensitive data categories mentioned", -min(len(sens) * 2, 10))

    score = int(max(0, min(100, round(score))))
    if score >= 80:
        grade, verdict = "Privacy-friendly", "This site treats your data with care."
    elif score >= 60:
        grade, verdict = "Fair", "Mostly reasonable, but read the flagged parts."
    elif score >= 40:
        grade, verdict = "Risky", "Several practices could expose your data."
    else:
        grade, verdict = "High risk", "Think twice before sharing personal details here."

    # 8. plain-English summary & recommendations
    summary = []
    if not checks["policy_found"]:
        summary.append("We couldn't find a privacy policy on this site, which is a red flag by itself.")
    for label, items in sorted(by_label.items(), key=lambda kv: -LABELS[kv[0]]["weight"]):
        if LABELS[label]["risk"] != "info":
            summary.append(LABELS[label]["plain"])
    if trackers:
        cats = sorted({t["category"].lower() for t in trackers})
        summary.append(f"{len(trackers)} third-party tracker(s) load on the homepage ({', '.join(cats)}).")
    if not summary:
        summary.append("Nothing alarming stood out in the text we could read.")

    recs = []
    if "data_selling" in by_label:
        recs.append("Look for a 'Do not sell or share my personal information' link and use it.")
    if trackers:
        recs.append(f"Browse with a tracker blocker (uBlock Origin, Privacy Badger) - {len(trackers)} trackers were found.")
    if trackers and not cookies["banner_detected"]:
        recs.append("No consent banner was detected. Reject non-essential cookies in your browser settings.")
    if sens:
        recs.append("Deny app or browser permissions (" + ", ".join(sens[:3]).lower() + ") unless a feature truly needs them.")
    if "long_retention" in by_label:
        recs.append("Use a throwaway email and delete your account when you're done - your data may stay on file.")
    if "user_rights" in by_label or "consent_control" in by_label:
        recs.append("Use the rights they offer: request a copy or deletion of your data (India's DPDP Act 2023 and GDPR back this up).")
    else:
        recs.append("Ask the site in writing for access to, or deletion of, your data (DPDP Act 2023 / GDPR).")
    if "policy_changes" in by_label:
        recs.append("Re-check this policy every few months - they can change it without telling you.")
    recs.append("Share the minimum: skip optional profile fields and use unique passwords.")

    return {
        "url": final_url, "domain": domain, "score": score, "grade": grade, "verdict": verdict,
        "summary": summary, "clauses": clauses[:24], "clause_total": len(clauses),
        "trackers": trackers, "cookies": cookies, "permissions": permissions,
        "sensitive_permissions": sens, "recommendations": recs[:7], "breakdown": breakdown,
        "policy_urls": links, "checks": checks, "policy_chars": len(policy_text),
    }
