#!/usr/bin/env python3
"""Map English-1979 page citations -> online chapter files, by content matching
against ttl.pdf (English text, 1939-style pagination) + repo chapter texts."""
import re, glob, os, json

REPO = "/home/eco/.lmstudio/apps/bionic/projects/eb7aa3af-1ac9-4dbb-b4ae-899ad090bc3c/workspace/site-preview"
SP = "/home/eco/.lmstudio/scratchpads/6e7bb3694d49c3bc55f172e8c3684244"

def nospace(s):
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"[^a-z0-9]+", "", s.lower())
    return s

# ---- online chapter corpus ----
chapters = {}   # fname -> space-free text
for f in glob.glob(f"{REPO}/book/*.html"):
    base = os.path.basename(f)
    if base.startswith(("qa", "doctrine")) or base == "index.html":
        continue
    chapters[base] = nospace(open(f).read())
print("chapters:", len(chapters))

# ---- pdf page corpus ----
pdf_pages = open("/tmp/ttl.txt", errors="replace").read().split("\f")
pdf_ns = [nospace(p) for p in pdf_pages]
def printed_no(i):
    lines = [l.strip() for l in pdf_pages[i].splitlines() if l.strip()]
    for l in lines[:2]:
        if re.match(r"^\d{1,3}$", l):
            return int(l)
    return None
printed = {printed_no(i): i for i in range(len(pdf_pages)) if printed_no(i)}

def shingles(s, size=60, count=6):
    if len(s) < size:
        return [s] if s else []
    step = max(1, (len(s) - size) // count)
    return [s[i:i+size] for i in range(0, len(s) - size, step)][:count]

def chapter_for_pdfpage(pdf_i):
    """Vote chapters by shingle membership for a given pdf page index."""
    votes = {}
    for sh in shingles(pdf_ns[pdf_i]):
        if len(sh) < 30:
            continue
        for name, text in chapters.items():
            if sh in text:
                votes[name] = votes.get(name, 0) + 1
    if not votes:
        return None, 0
    best = max(votes.items(), key=lambda kv: kv[1])
    return best

def map_english_page(x):
    """Try candidate printed pages around offset 15-19."""
    results = []
    for off in (16, 17, 18, 15, 19):
        pn = x - off
        if pn in printed:
            name, score = chapter_for_pdfpage(printed[pn])
            results.append((off, pn, name, score))
    return results

# ---- collect cited pages ----
cited = set()
for f in glob.glob(f"{REPO}/book/qa[12]-*.html") + glob.glob(f"{REPO}/book/doctrine-*.html"):
    s = re.sub(r"<[^>]+>", " ", open(f).read())
    for m in re.finditer(r"page[s]?\s+(\d+)", s):
        cited.add(int(m.group(1)))
cited.discard(0)
print("distinct cited pages:", len(cited))

mapping = {}
review = []
for x in sorted(cited):
    res = map_english_page(x)
    # majority vote across offsets
    votes = {}
    for off, pn, name, score in res:
        if name and score >= 2:
            votes[name] = votes.get(name, 0) + score
    if votes:
        best = max(votes.items(), key=lambda kv: kv[1])
        mapping[x] = best[0]
        review.append((x, best[0], best[1], res))
    else:
        mapping[x] = None
        review.append((x, None, 0, res))

for x, name, score, res in review:
    alt = ",".join(f"-{o}:p{p}→{n}({s})" for o, p, n, s in res[:3])
    print(f"eng {x:>3} -> {str(name):28} [{score}] {alt}")
json.dump({str(k): v for k, v in mapping.items()}, open(SP + "/page_map.json", "w"), indent=0)
print("saved page_map.json")
