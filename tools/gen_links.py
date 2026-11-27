#!/usr/bin/env python3
"""Add cross-links to generated supplement pages:
- 'Toward the Light, page N(: P)' -> mapped online chapter
- 'Question N' cross-references -> qa1/qa2 question pages
- 'Postscript' references -> postscript.html

NOTE (future): printed page numbers in the Q&A / Doctrine texts currently
follow the 1979 English edition. Once the original 1929/30 editions are
available, the visible page numbers should be switched to the original
1929/30 pagination. The link TARGETS are unaffected (chapter-level,
content-matched against the main-book PDF, which already follows the
original/Danish-1939-style paging); only the displayed numbers change.
"""
import re, json, os, glob, html as htmlmod

REPO = "/home/eco/.lmstudio/apps/bionic/projects/eb7aa3af-1ac9-4dbb-b4ae-899ad090bc3c/workspace/site-preview"
SP = "/home/eco/.lmstudio/scratchpads/6e7bb3694d49c3bc55f172e8c3684244"

page_map = {int(k): v for k, v in json.load(open(SP + "/page_map.json")).items()}
for p in range(3, 19):
    page_map[p] = "ardor-account.html"   # English 1979 front matter / Ardor intro

friendly = {}
idx = open(f"{REPO}/book/index.html").read()
for m in re.finditer(r'href="([a-z0-9-]+\.html)">([^<]+)</a>', idx):
    friendly.setdefault(m.group(1), m.group(2))

def fname(f):
    return friendly.get(f, f.replace(".html", ""))

def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s)

PAGE_RE = re.compile(
    r"\bpages?\s+\d+(?:\s*[-–]\s*\d+|\s+to\s+\d+|\s+and\s+\d+)?"
    r"(?::\s*\d+(?:\s*[,–-]\s*\d+)*\.?\)?)?")

CUES = [
    ("speech of christ", "speech"),
    ("doctrine of atonement", "doctrine"),
    ("some psychic experiences", "skip"),
    ("supplement", "skip"),
    ("toward the light", "ttl"),
    ("ardor’s account", "ttl"),
    ("ardor's account", "ttl"),
]

def nearest_cue(tail):
    best, bestpos = None, -1
    for word, kind in CUES:
        p = tail.rfind(word)
        if p > bestpos:
            best, bestpos = kind, p
    return best

def target_for(kind, pageno):
    if kind == "ttl":
        return page_map.get(pageno)
    if kind == "speech":
        return "speech-of-christ.html"
    if kind == "doctrine":
        return "doctrine-christ.html" if 27 <= pageno <= 40 else "doctrine.html"
    return None

def process_text_segment(seg, curvol, curq):
    """Process a non-<a> text segment; returns (new_seg, n_links)."""
    n = 0
    # ---- page references ----
    out, last = [], 0
    for m in PAGE_RE.finditer(seg):
        tail = strip_tags(seg[max(0, m.start()-160):m.start()]).lower()
        kind = nearest_cue(tail)
        if kind in (None, "skip"):
            continue
        pageno = int(re.search(r"\d+", m.group(0)).group(0))
        target = target_for(kind, pageno)
        if not target:
            continue
        text = m.group(0)
        trail = ""
        while text and text[-1] in ").":
            trail = text[-1] + trail
            text = text[:-1]
        out.append(seg[last:m.start()])
        out.append(f'<a class="xref" href="{target}" '
                   f'title="Toward the Light — {htmlmod.escape(fname(target))}">{text}</a>{trail}')
        last = m.end()
        n += 1
    out.append(seg[last:])
    seg = "".join(out)

    # ---- question cross-references ----
    qpat = re.compile(r"\bquestions?\s+(\d+)(?:\s+and\s+(\d+))?", re.I)
    out, last = [], 0
    for m in qpat.finditer(seg):
        before = strip_tags(seg[max(0, m.start()-40):m.start()]).lower()
        after = seg[m.end():m.end()+25].lower()
        vol = curvol
        if re.search(r"(first\s+supplement|supplement\s+i)\s*,\s*$", before):
            vol = "qa1"
        elif re.search(r"(second\s+supplement|supplement\s+ii)\s*,\s*$", before):
            vol = "qa2"
        elif after.startswith(", first supplement"):
            vol = "qa1"
        elif after.startswith(", second supplement"):
            vol = "qa2"
        nums = [int(m.group(1))] + ([int(m.group(2))] if m.group(2) else [])
        lim = 71 if vol == "qa1" else 73
        if nums[0] == curq and vol == curvol:
            continue  # self-reference
        if not all(1 <= x <= lim for x in nums):
            continue
        res = m.group(0)
        for x in sorted(nums, reverse=True):
            sx = str(x)
            res = res.replace(sx, f'<a class="xref" href="{vol}-{x:02d}.html">{sx}</a>', 1)
            n += 1
        out.append(seg[last:m.start()])
        out.append(res)
        last = m.end()
    out.append(seg[last:])
    seg = "".join(out)

    # ---- postscript ----
    seg2, cnt = re.subn(r"(postscript)( to <(?:em|span)[^>]*>| to toward the light)",
                        r'<a class="xref" href="postscript.html">\1</a>\2', seg, flags=re.I)
    n += cnt
    return seg2, n

def process_file(path, curvol, curq):
    s = open(path).read()
    parts = re.split(r"(<a\b.*?</a>)", s, flags=re.S)
    total = 0
    out = []
    for p in parts:
        if p.startswith("<a"):
            out.append(p)
        else:
            newp, n = process_text_segment(p, curvol, curq)
            out.append(newp)
            total += n
    open(path, "w").write("".join(out))
    return total

grand = 0
for f in sorted(glob.glob(f"{REPO}/book/qa[12]-*.html")):
    base = os.path.basename(f)
    curvol = "qa1" if base.startswith("qa1") else "qa2"
    curq = int(base.split("-")[1].split(".")[0])
    n = process_file(f, curvol, curq)
    grand += n
    if n:
        print(f"{base}: {n} links")
for f in ["doctrine-preface.html", "doctrine-paul.html", "doctrine-christ.html", "doctrine-loyola.html"]:
    n = process_file(f"{REPO}/book/{f}", "qa1", 0)
    grand += n
    if n:
        print(f"{f}: {n} links")
print("TOTAL:", grand)
