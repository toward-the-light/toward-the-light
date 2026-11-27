#!/usr/bin/env python3
"""Convert toward-the-light.net Word-HTML of 'The Doctrine of Atonement and the
Shorter Road' into structured blocks JSON for site page generation."""
import re, html, json

SP = "/home/eco/.lmstudio/scratchpads/6e7bb3694d49c3bc55f172e8c3684244"
SRC = SP + "/ttl/doctrine.html"

raw = open(SRC, "rb").read().decode("cp1252", errors="replace")
body = raw[raw.find("<BODY"):]

TITLES = {
    "toward the light", "greetings to denmark", "the second coming of christ",
    "some psychic experiences",
}
SCRIPTURE_RE = re.compile(
    r"^(matthew|mark|luke|john|acts|romans|genesis|leviticus|psalms?|isaiah|"
    r"jeremiah|lamentations|ezekiel|daniel|hebrews|corinthians|galatians|"
    r"ephesians|revelation|numbers|deuteronomy|exodus)\b", re.I)

def convert_inline(inner):
    s = inner
    s = re.sub(r"<o:p>\s*</o:p>", "", s, flags=re.I)
    # footnote refs: <B ...><SUP>n</SUP></B> (optional trailing <SPAN> </SPAN>)
    s = re.sub(r"<B\b[^>]*>\s*<SUP>\s*(\d+)\s*</SUP>(?:<SPAN[^>]*>\s*</SPAN>)?\s*</B>",
               r"@@FNREF{\1}@@", s, flags=re.I|re.S)
    # italics -> sentinel \x01..\x02 ; bold -> \x03..\x04 (protect from tag strip)
    s = re.sub(r"<I\b[^>]*>(.*?)</I>",
               lambda m: "\x01" + re.sub(r"<[^>]+>", "", m.group(1)) + "\x02",
               s, flags=re.I|re.S)
    s = re.sub(r"<B\b[^>]*>(.*?)</B>",
               lambda m: "\x03" + re.sub(r"<[^>]+>", "", m.group(1)) + "\x04",
               s, flags=re.I|re.S)
    # strip everything else
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace("\xa0", " ")
    s = s.replace("&shy;", "").replace("\xad", "")  # print-era soft hyphens
    s = s.replace("&", "&amp;")
    s = re.sub(r"\s+", " ", s).strip()
    # fix print letterspacing artifacts in numbers: "1 1-12" -> "11-12"
    s = re.sub(r"(?<=\d) (?=\d)", "", s)
    # replace sentinels, moving boundary spaces outside the tags
    def mkital(m):
        t = m.group(1)
        lead, trail = t[:1] == " ", t[-1:] == " "
        t = t.strip()
        if not t:
            return " " if (lead or trail) else ""
        key = t.strip(" .,;:\"").lower()
        if key in TITLES or SCRIPTURE_RE.match(t):
            tag = ("<em>", "</em>")
        else:
            tag = ('<span class="sp">', "</span>")
        return (" " if lead else "") + tag[0] + t + tag[1] + (" " if trail else "")
    s = re.sub(r"\x01(.*?)\x02", mkital, s)
    def mkstrong(m):
        t = m.group(1)
        lead, trail = t[:1] == " ", t[-1:] == " "
        t = t.strip()
        if not t:
            return " " if (lead or trail) else ""
        return (" " if lead else "") + "<strong>" + t + "</strong>" + (" " if trail else "")
    s = re.sub(r"\x03(.*?)\x04", mkstrong, s)
    return s

# ---------- block extraction ----------
blocks = []
for m in re.finditer(r"<(H[1-4]|P)\b([^>]*)>(.*?)</\1>", body, re.S|re.I):
    tag, attrs, inner = m.group(1).upper(), m.group(2), m.group(3)
    a = attrs.lower()
    if "text-align: center" in a or "align=center" in a:
        kind = "center"
    elif "text-align: right" in a:
        kind = "right"
    elif tag in ("H1", "H2", "H3"):
        kind = tag.lower()
    else:
        kind = "p"
    txt = convert_inline(inner)
    if not txt or txt == "&nbsp;":
        continue
    blocks.append((kind, txt))

def find_idx(pred, start=0):
    for i in range(start, len(blocks)):
        if pred(blocks[i]):
            return i
    return -1

def is_text(b, t):
    plain = re.sub(r"<[^>]+>", "", b[1]).strip().lower()
    return plain == t.lower()

i_preface = find_idx(lambda b: is_text(b, "PREFACE"))
i_paul    = find_idx(lambda b: is_text(b, "Paul’s Discourse"))
i_christ  = find_idx(lambda b: is_text(b, "Christ’s Discourse"))
i_loyola  = find_idx(lambda b: is_text(b, "Loyola’s Discourse"))
i_end     = find_idx(lambda b: is_text(b, "END"), i_loyola)

def slice_footnotes(seg):
    fn_start = None
    for i, (k, t) in enumerate(seg):
        plain = re.sub(r"<[^>]+>", "", t).strip().upper()
        if plain in ("FOOTNOTES", "FOOTNOTE"):
            fn_start = i
            break
    if fn_start is None:
        return seg, []
    body = seg[:fn_start]
    notes = []
    for k, t in seg[fn_start+1:]:
        plain = re.sub(r"<[^>]+>", "", t).strip()
        m = re.match(r"^(\d+)\)\s*(.*)$", plain, re.S)
        if m:
            # strip "N)" marker in any wrapping: <strong>7)</strong>, <strong>7</strong>), or plain 7)
            inner = re.sub(r"^<strong>\s*\d+\s*\)?\s*</strong>\s*\)?\s*", "", t)
            if inner == t:
                inner = re.sub(r"^\d+\s*\)\s*", "", t)
            notes.append((int(m.group(1)), inner.strip()))
    return body, notes

preface_seg = blocks[i_preface+1:i_paul]
paul_seg    = blocks[i_paul+1:i_christ]
christ_seg  = blocks[i_christ+1:i_loyola]
loyola_seg  = blocks[i_loyola+1:i_end if i_end > 0 else len(blocks)]

paul_body, paul_fns     = slice_footnotes(paul_seg)
christ_body, christ_fns = slice_footnotes(christ_seg)
loyola_body, loyola_fns = slice_footnotes(loyola_seg)

json.dump({"preface": preface_seg, "paul": paul_body, "paul_fns": paul_fns,
           "christ": christ_body, "christ_fns": christ_fns,
           "loyola": loyola_body, "loyola_fns": loyola_fns},
          open(SP + "/doctrine_blocks.json", "w"),
          indent=1, ensure_ascii=False)
print("preface:", len(preface_seg), "blocks")
print("paul:", len(paul_body), "blocks,", len(paul_fns), "footnotes")
print("christ:", len(christ_body), "blocks,", len(christ_fns), "footnotes")
print("loyola:", len(loyola_body), "blocks,", len(loyola_fns), "footnotes")
print("--- footnote markers stripped? ---")
for n, t in paul_fns + christ_fns + loyola_fns:
    print(n, "|", t[:70])
