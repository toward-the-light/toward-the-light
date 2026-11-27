# Supplement generation pipeline

Scripts used to generate the English supplement pages in `book/`:

- **Questions and Answers I (1929)** → `qa1-01.html` … `qa1-71.html`
- **Questions and Answers II (1930)** → `qa2-01.html` … `qa2-73.html`
- **The Doctrine of Atonement and the Shorter Road (1920)** → `doctrine*.html`

## Source text

The source is the English text as published on toward-the-light.net
(Harry Prior's copy-edit of the 1979 official translation,
© International Foundation for Toward the Light). It was downloaded as
HTML and converted in two steps:

1. **Parse** source HTML into structured blocks:
   - `convert_qa.py` → `qa_blocks.json` (from `qa1.html`, `qa2.html`)
   - `convert_doctrine.py` → `doctrine_blocks.json` (from `doctrine.html`)
2. **Render** site-styled pages:
   - `gen_qa.py` → 148 Q&A pages + section indexes
   - `gen_doctrine.py` → 5 Doctrine pages

## Cross-links

`gen_links.py` adds the `class="xref"` hyperlinks in the supplements:

- *"Toward the Light, page N"* → the matching online chapter
- *"Question N"* → the Q&A page (across both volumes)
- *"Postscript"* → `postscript.html`

Page mapping comes from `page_map.json`, produced by `map_pages.py`,
which content-matches each cited page against the main-book PDF text
(the PDF follows the original/Danish-1939-style paging). Links are
chapter-level; the main book has no per-page anchors.

## Known issues / TODO

- **Pagination:** the page numbers printed in the Q&A / Doctrine texts
  follow the **1979 English edition**. Once the original 1929/30 print
  editions are available, the visible page numbers should be switched to
  the original 1929/30 pagination. Link targets are unaffected
  (chapter-level, content-matched).
- `qa2` footnote #44 has no text in the source; a placeholder is rendered.
- The Q&A publishers' prefaces and the Q&A I appendix (marriage /
  birth control) are not in the online source text; they exist in the
  1979 print edition and could be transcribed if the foundation agrees.
- `gen_qa.py` contains a `CONTENT_FIXES` table for known source
  mistranslations (verified against the Danish original,
  *Spørgsmål og Svar*).

## Notes

- The scripts contain absolute paths from the environment in which they
  were run; adjust the `REPO` / `SP` constants before re-running.
- `qa_blocks.json` / `doctrine_blocks.json` are intermediates and are
  not committed; regenerate them with the convert scripts if needed.
