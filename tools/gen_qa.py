#!/usr/bin/env python3
"""Generate toward-the-light.org pages for 'Questions and Answers' I & II."""
import re, json

SP = "/home/eco/.lmstudio/scratchpads/6e7bb3694d49c3bc55f172e8c3684244"
REPO = "/home/eco/.lmstudio/apps/bionic/projects/eb7aa3af-1ac9-4dbb-b4ae-899ad090bc3c/workspace/site-preview"
D = json.load(open(SP + "/qa_blocks.json"))

VOLS = {
    "qa1": {"book": "Questions and Answers I", "suppl": "First Supplement", "year": "1929"},
    "qa2": {"book": "Questions and Answers II", "suppl": "Second Supplement", "year": "1930"},
}

# Corrections of errors in the .net source text, verified against the Danish
# original (Spørgsmål og Svar, H. Hagerup 1929/1930, electronic ed. 2019):
CONTENT_FIXES = {
    ("qa1", 4): [
        # Danish: "(Se iøvrigt Besvarelsen af det foregaaende Spørgsmaal.)"
        ("(See also the answer to Question 4.)",
         "(See also the answer to the preceding Question.)"),
    ],
}

def fix_spacing(s):
    s = re.sub(r"</(span|em|strong|sup)>(?=[A-Za-zÀ-ÿ])", r"</\1> ", s)
    s = re.sub(r"(?<=[A-Za-zÀ-ÿ])<(?=span class=\"sp\"|em|strong)", " <", s)
    s = re.sub(r" {2,}", " ", s)
    return s.strip()

def plain(t):
    return re.sub(r"<[^>]+>", "", t)

def is_divider(p):
    return bool(re.match(r"^[—–\-]{3,}$", p.strip()))

class FnMapper:
    """Maps global footnote numbers to per-page local numbers in order of use."""
    def __init__(self, fn_map):
        self.fn_map = {int(k): v for k, v in fn_map.items()}
        self.local = {}   # global -> local
        self.seen = {}    # local -> occurrence count
    def emit(self, s):
        def rep(m):
            g = int(m.group(1))
            if g not in self.local:
                self.local[g] = len(self.local) + 1
            n = self.local[g]
            self.seen[n] = self.seen.get(n, 0) + 1
            rid = f"ref{n}" if self.seen[n] == 1 else f"ref{n}-{self.seen[n]}"
            return f'<sup><a href="#fn{n}" id="{rid}">{n}</a></sup>'
        return re.sub(r"@@FNREF\{(\d+)\}@@", rep, s)
    def notes_html(self):
        if not self.local:
            return ""
        items = []
        for g, n in sorted(self.local.items(), key=lambda kv: kv[1]):
            t = fix_spacing(self.fn_map.get(g, "")) or "[Footnote text not present in the source edition.]"
            items.append(f'    <li id="fn{n}">{t}<a href="#ref{n}" class="fn-back">↩</a></li>')
        return ('  <section class="fn">\n    <h2>Notes</h2>\n    <ol>\n'
                + "\n".join(items) + "\n    </ol>\n  </section>")

SHELL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} – Toward the Light!</title>
<meta name="description" content="{desc}">
<link rel="stylesheet" href="../style.css">
</head>
<body>
<header class="site">
  <a class="brand" href="../index.html">🕯 <span>Toward the <em>Light</em>!</span></a>
  <nav class="main">
    <a href="../index.html">Home</a>
    <a href="../what-is-toward-the-light.html">What is it?</a>
    <a href="index.html" class="active">The Book</a>
    <a href="../start-here.html">Start here</a>
    <a href="../jesus.html">Jesus in the book</a>
    <a href="../nde.html">NDE &amp; science</a>
    <a href="../faq.html">FAQ</a>
  </nav>
</header>
<main class="chapter">
  <p class="crumbs"><a href="index.html">The Book</a> › <a href="{prefix}.html">{book}</a></p>
{content}
  <nav class="pn">{nav}</nav>
</main>
<footer class="site"><p>toward-the-light.org — read the book online, free</p></footer>
</body>
</html>
"""

def nav(prev=None, nxt=None, prefix=""):
    parts = []
    parts.append(f'<a class="prev" href="{prev[1]}">← {prev[0]}</a>' if prev else "<span></span>")
    parts.append(f'<a class="toc" href="{prefix}.html">Contents</a>')
    parts.append(f'<a class="next" href="{nxt[1]}">{nxt[0]} →</a>' if nxt else "<span></span>")
    return "".join(parts)

def esc_attr(s):
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")

def render_question_page(vol_key, q, prev, nxt):
    v = VOLS[vol_key]
    prefix = vol_key
    fm = FnMapper(D[vol_key]["fn_map"])
    qtext = fm.emit(fix_spacing(q["question"]))
    parts = ['  <div class="chapter-title">',
             f'    <p class="number">{q["num"]}.</p>',
             f"    <h1>{qtext}</h1>",
             "  </div>"]
    for kind, text in q["answers"]:
        for old, new in CONTENT_FIXES.get((vol_key, q["num"]), []):
            text = text.replace(old, new)
        text = fix_spacing(text)
        p = plain(text).strip()
        if not p:
            continue
        if kind == "center":
            if is_divider(p):
                parts.append('  <hr class="divider">')
            else:
                parts.append(f'  <h2 class="csec">{fm.emit(text)}</h2>')
        elif kind == "right":
            text = re.sub(r'<span class="sp">(.*?)</span>', r"\1", text)
            parts.append(f'  <p class="sig">{fm.emit(text)}</p>')
        elif kind in ("h1", "h2", "h3"):
            parts.append(f'  <h2 class="csec">{fm.emit(text)}</h2>')
        else:
            parts.append(f"  <p>{fm.emit(text)}</p>")
    fnsec = fm.notes_html()
    content = "\n".join(parts)
    if fnsec:
        content += "\n" + fnsec
    desc_plain = re.sub(r"@@FNREF\{\d+\}@@", "", q["question"])
    desc = esc_attr(plain(fix_spacing(desc_plain))[:155])
    title = f'Question {q["num"]} – {v["book"]}'
    htmlout = SHELL.format(title=title, desc=desc, content=content,
                           nav=nav(prev, nxt, prefix), prefix=prefix,
                           book=v["book"])
    fname = f"{prefix}-{q['num']:02d}.html"
    open(f"{REPO}/book/{fname}", "w").write(htmlout)
    return fname

INDEX_SHELL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{book} – {suppl} to Toward the Light!</title>
<meta name="description" content="Read {book} ({suppl} to Toward the Light, Copenhagen {year}) online — {count} questions on the origin of existence, life on Earth and our relationship to God, answered from the transcendental world.">
<link rel="stylesheet" href="../style.css">
</head>
<body>
<header class="site">
  <a class="brand" href="../index.html">🕯 <span>Toward the <em>Light</em>!</span></a>
  <nav class="main">
    <a href="../index.html">Home</a>
    <a href="../what-is-toward-the-light.html">What is it?</a>
    <a href="index.html" class="active">The Book</a>
    <a href="../start-here.html">Start here</a>
    <a href="../jesus.html">Jesus in the book</a>
    <a href="../nde.html">NDE &amp; science</a>
    <a href="../faq.html">FAQ</a>
  </nav>
</header>
<main>
  <p class="crumbs"><a href="index.html">The Book</a> › Supplements</p>
  <h1>{book}</h1>
  <p class="lede">{suppl} to <em>Toward the Light!</em> — published by Michael Agerskov,
  Copenhagen {year}. {count} questions posed by readers of the main work, answered from
  the transcendental world through Johanne Agerskov.</p>
  <h2>Contents</h2>
  <ul class="chapter-list">
{items}
  </ul>
</main>
<footer class="site"><p>toward-the-light.org — read the book online, free</p></footer>
</body>
</html>
"""

for vol_key in ("qa1", "qa2"):
    v = VOLS[vol_key]
    vol = D[vol_key]
    qs = vol["questions"]
    toc = {n: t for n, t in vol["toc"]}
    total = len(qs)
    for i, q in enumerate(qs):
        prev = (f"Question {qs[i-1]['num']}", f"{vol_key}-{qs[i-1]['num']:02d}.html") if i > 0 \
               else (v["book"], f"{vol_key}.html")
        nxt = (f"Question {qs[i+1]['num']}", f"{vol_key}-{qs[i+1]['num']:02d}.html") if i < total-1 \
              else None
        render_question_page(vol_key, q, prev, nxt)
    items = []
    for q in qs:
        n = q["num"]
        topic = toc.get(n, "")
        items.append(f'    <li><a href="{vol_key}-{n:02d}.html">{n}. {topic}</a></li>')
    index = INDEX_SHELL.format(book=v["book"], suppl=v["suppl"], year=v["year"],
                               count=total, items="\n".join(items))
    open(f"{REPO}/book/{vol_key}.html", "w").write(index)
    print(f"{vol_key}: {total} question pages + index written")
