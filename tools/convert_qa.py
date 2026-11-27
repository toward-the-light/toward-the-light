#!/usr/bin/env python3
"""Convert toward-the-light.net Word-HTML of 'Questions and Answers' I & II
(supplements to Toward the Light) into structured JSON for site generation."""
import re, html, json

SP = "/home/eco/.lmstudio/scratchpads/6e7bb3694d49c3bc55f172e8c3684244"

TITLES = {
    "toward the light", "greetings to denmark", "the second coming of christ",
    "some psychic experiences", "the doctrine of atonement and the shorter road",
    "the doctrine of atonement", "supplement i", "supplement ii",
    "first supplement", "second supplement", "questions and answers",
    "questions & answers", "memento",
}
SCRIPTURE_RE = re.compile(
    r"^(matthew|mark|luke|john|acts|romans|genesis|leviticus|psalms?|isaiah|"
    r"jeremiah|lamentations|ezekiel|daniel|hebrews|corinthians|galatians|"
    r"ephesians|revelation|numbers|deuteronomy|exodus)\b", re.I)

def convert_inline(inner):
    s = inner
    s = re.sub(r"<o:p>\s*</o:p>", "", s, flags=re.I)
    s = re.sub(r"<B\b[^>]*>\s*<SUP>\s*(\d+)\s*</SUP>(?:<SPAN[^>]*>\s*</SPAN>)?\s*</B>",
               r"@@FNREF{\1}@@", s, flags=re.I|re.S)
    # bare <SUP>n</SUP> refs (used in the question paragraphs)
    s = re.sub(r"<SUP>\s*(\d+)\s*</SUP>", r"@@FNREF{\1}@@", s, flags=re.I)
    s = re.sub(r"<I\b[^>]*>(.*?)</I>",
               lambda m: "\x01" + re.sub(r"<[^>]+>", "", m.group(1)) + "\x02",
               s, flags=re.I|re.S)
    s = re.sub(r"<B\b[^>]*>(.*?)</B>",
               lambda m: "\x03" + re.sub(r"<[^>]+>", "", m.group(1)) + "\x04",
               s, flags=re.I|re.S)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace("\xa0", " ")
    s = s.replace("&shy;", "").replace("\xad", "")
    s = s.replace("&", "&amp;")
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"(?<=\d) (?=\d)", "", s)
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

def load(fname):
    raw = open(fname, "rb").read().decode("cp1252", errors="replace")
    body = raw[raw.find("<BODY"):]
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
        # rawplain: pre-gluing plain text for structural detection
        rawplain = html.unescape(re.sub(r"<[^>]+>", " ", inner)).replace("\xa0", " ")
        rawplain = " ".join(rawplain.split())
        txt = convert_inline(inner)
        plain = re.sub(r"<[^>]+>", "", txt).strip()
        if not plain and not rawplain:
            continue
        blocks.append([kind, txt, plain, rawplain])
    return blocks

def convert_volume(fname, vol):
    blocks = load(fname)
    fn_i = next(i for i, b in enumerate(blocks) if b[3].upper() == "FOOTNOTES")
    end_i = next(i for i, b in enumerate(blocks) if b[3].upper() == "END")

    # ---- questions ----
    questions = []
    cur = None
    expected = 1
    for kind, txt, plain, rawplain in blocks[:fn_i]:
        m = re.match(r"^(\d{1,3})(?:\s+\d+)?$", rawplain) if kind == "center" else None
        if m and int(m.group(1)) == expected:
            cur = {"num": expected, "question": None, "answers": []}
            questions.append(cur)
            expected += 1
            continue
        if cur is None:
            continue
        if cur["question"] is None and kind == "p":
            cur["question"] = txt
        elif cur["question"] is not None:
            cur["answers"].append((kind, txt))
    print(f"  vol{vol}: {len(questions)} questions (expected {expected-1})")

    # ---- footnotes: flat global-number -> text map ----
    fn_map = {}
    for kind, txt, plain, rawplain in blocks[fn_i+1:end_i]:
        m = re.match(r"^(\d+)\s*(?:twice\s*)?\)\s*(.*)$", plain)
        if m:
            gnum = int(m.group(1))
            inner = txt
            # marker wrapped in a leading tag: <strong>6)</strong> / <span class="sp">6)</span>
            mtag = re.match(r"^(<(?:strong|span)\b[^>]*>)\s*\d+\s*(?:twice\s*)?\s*\)?\s*(</(?:strong|span)>)\s*\)?\s*", inner)
            mopen = None if mtag else re.match(r"^(<(?:strong|span)\b[^>]*>)(\s*\d+\s*(?:twice\s*)?\s*\))\s*", inner)
            if mtag and (')' in mtag.group(0) or 'twice' in mtag.group(0)):
                inner = inner[mtag.end():]
            elif mopen:
                # digits+paren at start INSIDE the tag: <span class="sp">7) Toward...
                inner = mopen.group(1) + inner[mopen.end():]
            else:
                # plain marker: 6) or 1 twice )
                inner2 = re.sub(r"^\d+\s*(?:twice\s*)?\s*\)\s*", "", inner)
                if inner2 != inner:
                    inner = inner2
                else:
                    # marker split: plain number, paren inside tag: 1 <span...>)
                    inner = re.sub(r"^\d+\s*(?:twice\s*)?\s*((?:<[^>]+>|\s)*)\)\s*", r"\1", inner)
            # leftover lone paren at start (possibly after tags)
            inner = re.sub(r"^((?:<[^>]+>|\s)*)\)\s*", r"\1", inner)
            fn_map[gnum] = inner.strip()
    print(f"  vol{vol}: {len(fn_map)} footnote texts (max #{max(fn_map) if fn_map else 0})")

    # ---- table of contents (after END) ----
    toc = []
    SKIP = {"toward the light", "first supplement", "second supplement",
            "questions & answers", "copy-edited by harry prior", "contents"}
    for kind, txt, plain, rawplain in blocks[end_i+1:]:
        m = re.match(r"^(\d{1,3})\s*(?:\.\s*|\s+[a-d]\s*\)\s*)(.*)$", plain)
        if m and 1 <= int(m.group(1)) <= expected-1:
            n = int(m.group(1))
            topic = m.group(2).strip()
            if topic and n not in [x[0] for x in toc]:
                toc.append((n, topic))
            continue
        if toc and plain and not re.match(r"^\d", plain) and plain.lower() not in SKIP:
            toc[-1] = (toc[-1][0], toc[-1][1] + " " + plain)
    print(f"  vol{vol}: {len(toc)} toc entries")
    toc_nums = {t[0] for t in toc}
    missing_toc = [q["num"] for q in questions if q["num"] not in toc_nums]
    if missing_toc:
        print(f"  vol{vol}: toc missing for questions: {missing_toc}")

    # ---- verification: refs vs texts ----
    all_refs = set()
    for q in questions:
        src = (q["question"] or "") + " " + " ".join(t for _, t in q["answers"])
        all_refs.update(int(x) for x in re.findall(r"@@FNREF\{(\d+)\}@@", src))
    missing = sorted(r for r in all_refs if r not in fn_map)
    if missing:
        print(f"  vol{vol}: WARNING refs without footnote text: {missing}")
    unused = sorted(g for g in fn_map if g not in all_refs)
    if unused:
        print(f"  vol{vol}: note: unreferenced footnote texts: {unused[:10]}{'...' if len(unused)>10 else ''}")

    return {"vol": vol, "questions": questions, "fn_map": fn_map, "toc": toc}

out = {"qa1": convert_volume(SP + "/ttl/qa1.html", 1),
       "qa2": convert_volume(SP + "/ttl/qa2.html", 2)}
json.dump(out, open(SP + "/qa_blocks.json", "w"), indent=1, ensure_ascii=False)
print("\nJSON written.")
