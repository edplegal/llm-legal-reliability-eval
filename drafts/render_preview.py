"""Style the pandoc HTML of a draft for review: badge the markers.

Usage:
    pandoc -f gfm -t html -s --metadata title="Draft review copy" \
        drafts/substack_post.md | python3 drafts/render_preview.py \
        > drafts/substack_post.preview.html

Reads HTML on stdin, writes styled HTML on stdout. Preview files are
gitignored; the markdown stays the single source of truth.
"""

import re
import sys

CSS = """
<style>
:root { --bg:#fdfdfa; --fg:#1c1c1c; --muted:#6b6b6b; --accent:#2c5f8a;
        --table-border:#d8d5cc; --code-bg:#f0efe9; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#191a1c; --fg:#e6e4de; --muted:#9a988f; --accent:#7db3dd;
          --table-border:#3a3b3e; --code-bg:#26272a; }
}
html { background:var(--bg); }
body { max-width:46rem; margin:2rem auto 6rem; padding:0 1.2rem;
       font:18px/1.65 Charter, Georgia, serif; color:var(--fg); }
h1,h2,h3 { font-family:-apple-system, "Helvetica Neue", sans-serif;
           line-height:1.25; }
h1 { font-size:1.7rem; } h2 { font-size:1.35rem; margin-top:2.4rem;
     border-bottom:1px solid var(--table-border); padding-bottom:.3rem; }
h3 { font-size:1.1rem; }
code { background:var(--code-bg); padding:.1em .35em; border-radius:4px;
       font-size:.85em; }
blockquote { border-left:3px solid var(--accent); margin-left:0;
             padding-left:1rem; color:var(--muted); }
table { border-collapse:collapse; width:100%; margin:1rem 0;
        font-size:.85em; font-family:-apple-system, sans-serif; }
th,td { border:1px solid var(--table-border); padding:.4rem .6rem;
        text-align:left; }
th { background:var(--code-bg); }
hr { border:none; border-top:1px solid var(--table-border); margin:2.5rem 0; }
.badge { display:inline-block; font:600 .72em/1 -apple-system, sans-serif;
         padding:.25em .55em; border-radius:99px; vertical-align:middle;
         white-space:nowrap; max-width:100%; overflow:hidden;
         text-overflow:ellipsis; }
.badge.you    { background:#b45309; color:#fff; }
.badge.lw     { background:#6d28d9; color:#fff; }
.badge.cut    { background:transparent; color:var(--muted);
                border:1.5px dashed var(--muted); }
.badge.hot    { background:#b91c1c; color:#fff; }
.gen-banner { position:sticky; top:0; background:#b45309; color:#fff;
              font:600 .8rem/1.4 -apple-system, sans-serif; text-align:center;
              padding:.45rem .8rem; border-radius:0 0 8px 8px; z-index:9; }
</style>
"""

BANNER = (
    '<div class="gen-banner">GENERATED PREVIEW — edit the .md source,'
    " not this file. Regenerate: see drafts/render_preview.py docstring</div>"
)

BADGES = [
    (r"\[(YOU[^\]]*)\]", "you"),
    (r"\[(LW-ONLY:?[^\]]*)\]", "lw"),
    (r"\[(CUT-OK[^\]]*)\]", "cut"),
    (r"\[(PENDING[^\]]*)\]", "hot"),
    (r"\[(DRAFTED[^\]]*)\]", "hot"),
    (r"\[(REPO LINK[^\]]*)\]", "hot"),
    (r"\[(DRAFT v?\d*)\]", "hot"),
    (r"\[(not for publication)\]", "cut"),
]

html = sys.stdin.read()
for pattern, cls in BADGES:
    html = re.sub(pattern, rf'<span class="badge {cls}">\1</span>', html)
html = html.replace("</head>", CSS + "</head>", 1)
html = html.replace("<body>", "<body>" + BANNER, 1)
sys.stdout.write(html)
