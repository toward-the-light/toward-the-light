#!/usr/bin/env python3
"""Generate toward-the-light.org pages for 'The Doctrine of Atonement and the
Shorter Road' from the extracted blocks JSON."""
import re, json

SP = "/home/eco/.lmstudio/scratchpads/6e7bb3694d49c3bc55f172e8c3684244"
REPO = "/home/eco/.lmstudio/apps/bionic/projects/eb7aa3af-1ac9-4dbb-b4ae-899ad090bc3c/workspace/site-preview"
D = json.load(open(SP + "/doctrine_blocks.json"))

BOOK = "The Doctrine of Atonement and the Shorter Road"

def fix_spacing(s):
    s = re.sub(r"</(span|em|strong)>(?=[A-Za-zÀ-ÿ])", r"</\1> ", s)
    s = re.sub(r"(?<=[A-Za-zÀ-ÿ])<(?=span class=\"sp\"|em|strong)", " <", s)
    s = re.sub(r" {2,}", " ", s)
    return s.strip()

def emit_fnrefs(s, used):
    def rep(m):
        n = int(m.group(1))
        used.add(n)
        return f'<sup><a href="#fn{n}" id="ref{n}">{n}</a></sup>'
    return re.sub(r"@@FNREF\{(\d+)\}@@", rep, s)

def is_divider(plain):
    return bool(re.match(r"^[—–\-]{3,}$", plain.strip()))

def plain(t):
    return re.sub(r"<[^>]+>", "", t)

def render_body(blocks, used):
    out = []
    first = True
    for kind, text in blocks:
        text = fix_spacing(text)
        p = plain(text).strip()
        if not p:
            continue  # drop empty filler paragraphs
        if kind == "right" and first:
            # epigraph: split trailing <em>scripture</em> as source
            text = emit_fnrefs(text, used)
            m = re.search(r"(<em>[^<]+</em>)\s*$", text)
            if m:
                quote = text[:m.start()].strip().rstrip("—").rstrip()
                src = m.group(1)
            else:
                quote, src = text, None
            ep = '  <div class="epigraph">\n    <p>' + quote + "</p>\n"
            if src:
                ep += '    <span class="source">— ' + src + "</span>\n"
            ep += "  </div>"
            out.append(ep)
        elif kind == "center":
            if is_divider(p):
                out.append('  <hr class="divider">')
            else:
                out.append(f'  <h2 class="csec">{emit_fnrefs(text, used)}</h2>')
        elif kind == "right":
            # signatures: no Sperrdruck on the name line
            text = re.sub(r'<span class="sp">(.*?)</span>', r"\1", text)
            out.append(f'  <p class="sig">{emit_fnrefs(text, used)}</p>')
        elif kind in ("h1", "h2", "h3"):
            continue  # used as page titles / END marker
        else:
            out.append(f"  <p>{emit_fnrefs(text, used)}</p>")
        first = False
    return "\n".join(out)

def render_fns(fns, used):
    notes = {n: fix_spacing(t) for n, t in fns}
    missing = [n for n in notes if n not in used]
    extra = [n for n in used if n not in notes]
    if missing: print("  WARNING unreferenced notes:", missing)
    if extra:   print("  WARNING refs without note:", extra)
    if not notes:
        return ""
    items = []
    for n in sorted(notes):
        t = emit_fnrefs(notes[n], set())
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
  <p class="crumbs"><a href="index.html">The Book</a> › <a href="doctrine.html">The Doctrine of Atonement and the Shorter Road</a></p>
{content}
  <nav class="pn">{nav}</nav>
</main>
<footer class="site"><p>toward-the-light.org — read the book online, free</p></footer>
</body>
</html>
"""

def nav(prev=None, nxt=None):
    parts = []
    parts.append(f'<a class="prev" href="{prev[1]}">← {prev[0]}</a>' if prev else "<span></span>")
    parts.append('<a class="toc" href="doctrine.html">Contents</a>')
    parts.append(f'<a class="next" href="{nxt[1]}">{nxt[0]} →</a>' if nxt else "<span></span>")
    return "".join(parts)

def write(fname, title, desc, heading, blocks, fns, prev, nxt):
    used = set()
    body = render_body(blocks, used)
    fnsec = render_fns(fns, used)
    content = f"  <h1>{heading}</h1>\n" + body
    if fnsec:
        content += "\n" + fnsec
    htmlout = SHELL.format(title=title, desc=desc, content=content,
                           nav=nav(prev, nxt))
    open(f"{REPO}/book/{fname}", "w").write(htmlout)
    print(f"wrote book/{fname} ({len(htmlout)} bytes)")

write("doctrine-preface.html",
      "Publisher's Preface – " + BOOK,
      "Publisher's preface to The Doctrine of Atonement and the Shorter Road, Copenhagen 1920 — a supplement to Toward the Light.",
      "Preface", D["preface"], [],
      None, ("Paul’s Discourse", "doctrine-paul.html"))

write("doctrine-paul.html",
      "Paul’s Discourse – " + BOOK,
      "Paul's discourse from The Doctrine of Atonement and the Shorter Road (1920): the origin of the doctrine of the atoning death of Jesus.",
      "Paul’s Discourse", D["paul"], D["paul_fns"],
      ("Preface", "doctrine-preface.html"), ("Christ’s Discourse", "doctrine-christ.html"))

write("doctrine-christ.html",
      "Christ’s Discourse – " + BOOK,
      "Christ's discourse from The Doctrine of Atonement and the Shorter Road (1920): an address to all who bear the name of Christian.",
      "Christ’s Discourse", D["christ"], D["christ_fns"],
      ("Paul’s Discourse", "doctrine-paul.html"), ("Loyola’s Discourse", "doctrine-loyola.html"))

write("doctrine-loyola.html",
      "Loyola’s Discourse – " + BOOK,
      "Loyola's discourse from The Doctrine of Atonement and the Shorter Road (1920): the Shorter Road and the Three Golden Fruits.",
      "Loyola’s Discourse", D["loyola"], D["loyola_fns"],
      ("Christ’s Discourse", "doctrine-christ.html"), None)

index = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Doctrine of Atonement and the Shorter Road – Toward the Light!</title>
<meta name="description" content="Read The Doctrine of Atonement and the Shorter Road (1920) online — a supplement to Toward the Light with discourses by Paul, Christ and Ignatius Loyola.">
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
  <h1>The Doctrine of Atonement and the Shorter Road</h1>
  <p class="lede">A message from the transcendental world to all who bear the name of Christian —
  published by Michael Agerskov, Copenhagen 1920. A companion volume to
  <em>Toward the Light!</em>, in which the origin of the church's doctrine of atonement is
  examined and the shorter road to the Father is shown.</p>
  <h2>Contents</h2>
  <ul>
    <li><a href="doctrine-preface.html">Publisher's Preface</a></li>
    <li><a href="doctrine-paul.html">Paul's Discourse</a></li>
    <li><a href="doctrine-christ.html">Christ's Discourse</a></li>
    <li><a href="doctrine-loyola.html">Loyola's Discourse</a></li>
  </ul>
</main>
<footer class="site"><p>toward-the-light.org — read the book online, free</p></footer>
</body>
</html>
"""
open(f"{REPO}/book/doctrine.html", "w").write(index)
print("wrote book/doctrine.html")
