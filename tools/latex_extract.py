"""Read the bilingual LaTeX CV + portfolio and turn it into plain data.

Every text in the LaTeX sources is written as \\tr{English}{Deutsch}.  This
module resolves those pairs into {"en": html, "de": html} dicts, so the
website can be generated from the same text as the PDF.

Only the macros used in the CV-Portfolio-LaTeX project are understood; an
unknown macro is dropped (its arguments are kept as text) and reported.
"""
import html
import re
import sys

LANGS = ("en", "de")
WARNINGS = set()


# ---------------------------------------------------------------- reading
def strip_comments(src):
    """Remove % comments (but keep escaped \\%)."""
    return re.sub(r"(?<!\\)%[^\n]*\n?[ \t]*", "", src)


def skip_ws(s, i):
    while i < len(s) and s[i] in " \t\n":
        i += 1
    return i


def read_group(s, i, open_="{", close="}"):
    """s[i] must be the opening char; return (content, index after close)."""
    assert s[i] == open_, (s[i:i + 40], open_)
    depth, j = 0, i
    while j < len(s):
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == open_:
            depth += 1
        elif c == close:
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1
    raise ValueError("unbalanced group near: " + s[i:i + 60])


def read_args(s, i, n, optional=True):
    """Read an optional [..] argument and n {..} arguments starting at s[i]."""
    opt = None
    j = skip_ws(s, i)
    if optional and j < len(s) and s[j] == "[":
        opt, i = read_group(s, j, "[", "]")
    args = []
    for _ in range(n):
        i = skip_ws(s, i)
        if i >= len(s) or s[i] != "{":
            # a single-token argument such as \pcell{1}x is not used here
            raise ValueError("missing argument near: " + s[i:i + 60])
        a, i = read_group(s, i)
        args.append(a)
    return opt, args, i


def find_macros(s, names):
    """Yield (name, start, end_of_name) for each top-level-or-nested \\name."""
    pat = re.compile(r"\\(" + "|".join(map(re.escape, names)) + r")(?![A-Za-z@])")
    for m in pat.finditer(s):
        if m.start() > 0 and s[m.start() - 1] == "\\":
            continue  # \\ followed by letters
        yield m.group(1), m.start(), m.end()


def split_top(s, sep=","):
    """Split at sep characters that are not inside braces."""
    out, depth, cur, i = [], 0, "", 0
    while i < len(s):
        c = s[i]
        if c == "\\" and i + 1 < len(s):
            cur += s[i:i + 2]
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        if c == sep and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += c
        i += 1
    out.append(cur)
    return [x.strip() for x in out if x.strip()]


def split_items(s):
    """Split a list body at top-level \\item."""
    parts, depth, last, i = [], 0, None, 0
    while i < len(s):
        c = s[i]
        if c == "\\":
            if depth == 0 and re.match(r"\\item(?![A-Za-z])", s[i:]):
                if last is not None:
                    parts.append(s[last:i])
                last = i + 5
                i += 5
                continue
            i += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        i += 1
    if last is not None:
        parts.append(s[last:])
    return [p.strip() for p in parts if p.strip()]


# ------------------------------------------------------- LaTeX -> HTML
SIMPLE = {
    "texttimes": "×", "times": "×", "sim": "~", "pi": "π", "textbullet": "•",
    "enspace": " ", "quad": " ", "qquad": " ", "%": "%", "&": "&amp;",
    "$": "$", "_": "_", "#": "#", "{": "{", "}": "}", ",": "\u202f",
    " ": " ", "@": "", "ldots": "…", "dots": "…", "LaTeX": "LaTeX",
    "noindent": "", "centering": "", "hfill": "", "par": " ", "small": "",
    "normalsize": "", "footnotesize": "", "rmfamily": "", "sffamily": "",
    "bfseries": "", "selectfont": "", "/": "", "-": "",
}
WRAP = {
    "textbf": ("<strong>", "</strong>"), "emph": ("<em>", "</em>"),
    "textit": ("<em>", "</em>"), "underline": ("", ""),
    "textsuperscript": ("<sup>", "</sup>"), "textsubscript": ("<sub>", "</sub>"),
    "boldsymbol": ("", ""), "mathrm": ("", ""), "text": ("", ""),
    "mbox": ("", ""), "textrm": ("", ""), "textsf": ("", ""),
}
DROP_WITH_ARGS = {"fontsize": 2, "vspace": 1, "hspace": 1, "color": 1, "fontseries": 1,
                  "includegraphics": 1, "rule": 2, "label": 1}


def to_html(s, lang, math=False):
    """Convert a LaTeX fragment to an HTML fragment in one language."""
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "\\":
            if i + 1 < len(s) and s[i + 1] == "\\":
                out.append("<br>")
                i += 2
                continue
            m = re.match(r"\\([A-Za-z@]+)\*?|\\(.)", s[i:])
            name = m.group(1) or m.group(2)
            j = i + m.end()
            if name == "tr":
                _, (en, de), j = read_args(s, j, 2, optional=False)
                out.append(to_html(en if lang == "en" else de, lang, math))
            elif name in ("whatlabel", "howlabel", "resultslabel"):
                out.append({"whatlabel": ("What?", "Was?"), "howlabel": ("How?", "Wie?"),
                            "resultslabel": ("Results", "Ergebnisse")}[name][LANGS.index(lang)])
            elif name == "enquote":
                _, (a,), j = read_args(s, j, 1, optional=False)
                q = ("“", "”") if lang == "en" else ("„", "“")
                out.append(q[0] + to_html(a, lang, math) + q[1])
            elif name in WRAP:
                _, (a,), j = read_args(s, j, 1, optional=False)
                o, cl = WRAP[name]
                out.append(o + to_html(a, lang, math) + cl)
            elif name in DROP_WITH_ARGS:
                _, _, j = read_args(s, j, DROP_WITH_ARGS[name])
            elif name in SIMPLE:
                out.append(SIMPLE[name])
                if name.isalpha():  # a control word eats the following space and {}
                    j = skip_ws(s, j)
                    if s.startswith("{}", j):
                        j += 2
            else:
                WARNINGS.add(name)
            i = j
        elif c == "{":
            g, i = read_group(s, i)
            out.append(to_html(g, lang, math))
        elif c == "}":
            i += 1
        elif c == "$":
            k = s.index("$", i + 1)
            out.append(to_html(s[i + 1:k], lang, math=True))
            i = k + 1
        elif math and c in "_^":
            i += 1
            if s[i] == "{":
                g, i = read_group(s, i)
            else:
                g, i = s[i], i + 1
            tag = "sub" if c == "_" else "sup"
            out.append(f"<{tag}>{to_html(g, lang, True)}</{tag}>")
        elif math and c == "-":
            out.append("−")
            i += 1
        elif math and c == " ":
            i += 1
        elif c == "~":
            out.append("\u00a0")
            i += 1
        elif s.startswith("---", i):
            out.append("—")
            i += 3
        elif s.startswith("--", i):
            out.append("–")
            i += 2
        elif c in "\n\t":
            out.append(" ")
            i += 1
        else:
            out.append(html.escape(c, quote=False))
            i += 1
    text = "".join(out)
    return re.sub(r"[ ]{2,}", " ", text)


def tr(s):
    """LaTeX fragment -> {"en": html, "de": html} (stripped)."""
    return {lang: to_html(s, lang).strip() for lang in LANGS}


def plain(s):
    """Same as tr() but without HTML tags (for titles, alt text, meta)."""
    return {k: re.sub(r"<[^>]+>", "", v) for k, v in tr(s).items()}


def items(s):
    return [tr(x) for x in split_items(s)]


# ------------------------------------------------------------ projects
IMG_MACROS = {"pcell": 2, "pimg": 2, "pimgh": 3, "includegraphics": 1}


def images_in(s):
    names = []
    for name, _, end in find_macros(s, list(IMG_MACROS)):
        _, args, _ = read_args(s, end, IMG_MACROS[name])
        names += split_top(args[-1]) if name == "pcell" else [args[-1].strip()]
    return names


def parse_project(src, slug):
    s = strip_comments(src)
    p = {"slug": slug, "sections": [], "galleries": []}
    gallery = {"heading": None, "images": []}
    last_row = []

    def section(key, title, body):
        lst = items(body)
        for sec in p["sections"]:
            if sec["key"] == key and key != "custom":
                sec["items"] += lst
                return
        p["sections"].append({"key": key, "title": title, "items": lst})

    def pfblocks(body):
        for _, _, end in find_macros(body, ["pfblock"]):
            _, (label, content), _ = read_args(body, end, 2)
            lab = label.strip()
            key = {"\\whatlabel": "what", "\\howlabel": "how",
                   "\\resultslabel": "results"}.get(lab, "custom")
            section(key, None if key != "custom" else plain(lab), content)

    i = 0
    tops = ["projectinfo", "projecttitle", "projecttitlelogo", "picrow", "whr",
            "gridcols", "captionrow", "selectfont"]
    pat = re.compile(r"\\(" + "|".join(tops) + r")(?![A-Za-z])")
    while True:
        m = pat.search(s, i)
        if not m:
            break
        name, j = m.group(1), m.end()
        if name == "projectinfo":
            _, a, j = read_args(s, j, 5)
            p["org"], p["period"], p["role"] = plain(a[0]), plain(a[1]), plain(a[2])
            p["keywords"] = [plain(k) for k in split_top(a[3])]
            p["highlight"] = plain(a[4])
        elif name == "projecttitle":
            _, a, j = read_args(s, j, 3)
            p["title"], p["logos"] = plain(a[0]), [a[1].strip()]
        elif name == "projecttitlelogo":
            _, a, j = read_args(s, j, 2)
            p["title"] = plain(a[0])
            p["logos"] = images_in(a[1])
            extra = re.sub(r"<[^>]+>", "", to_html(a[1], "en")).strip()
            p["logo_text"] = extra or None  # e.g. "SONY" set in type
        elif name == "picrow":
            _, (_, body), j = read_args(s, j, 2)
            last_row = [{"file": f, "caption": None} for f in images_in(body)]
            gallery["images"] += last_row
            pfblocks(body)  # text can also sit inside a picture row
        elif name == "captionrow":
            _, (body,), j = read_args(s, j, 1)
            for img, cap in zip(last_row, split_top(body)):
                img["caption"] = plain(cap)
        elif name == "whr":
            _, (a, b, c), j = read_args(s, j, 3)
            section("what", None, a)
            section("how", None, b)
            section("results", None, c)
        elif name == "gridcols":
            _, (_, left, right), j = read_args(s, j, 3)
            last_row = [{"file": f, "caption": None} for f in images_in(left)]
            n_before = len(p["sections"])
            pfblocks(right)
            new = p["sections"][n_before:]
            if new and all(sec["key"] == "custom" for sec in new):
                # pictures next to an extra block ("Next step: ...") get their own gallery
                if gallery["images"]:
                    p["galleries"].append(gallery)
                gallery = {"heading": new[0]["title"], "images": []}
            gallery["images"] += last_row
        elif name == "selectfont":
            # a bold sub-heading: {\fontsize..\selectfont \tr{..}{..}} -> new gallery
            k = skip_ws(s, j)
            if s.startswith("\\tr", k):
                _, (en, de), j = read_args(s, k + 3, 2, optional=False)
                if gallery["images"]:
                    p["galleries"].append(gallery)
                gallery = {"heading": plain("\\tr{%s}{%s}" % (en, de)), "images": []}
        i = j
    if gallery["images"]:
        p["galleries"].append(gallery)
    for key in ("org", "period", "role", "highlight"):
        p.setdefault(key, {"en": "", "de": ""})
    p.setdefault("keywords", [])
    return p


# ------------------------------------------------------------------ CV
def parse_main(src):
    """Personal data, degrees, and the project order from main.tex.

    The phone number is deliberately NOT read: it stays out of the website.
    """
    s = strip_comments(src)
    info = {}
    for key in ("Name", "Email", "LinkedIn", "DegreeA", "DegreeB", "Place"):
        m = re.search(r"\\%s(?![A-Za-z])" % key, s)
        if m:
            _, (a,), _ = read_args(s, m.end(), 1)
            info[key.lower()] = plain(a)
    order = re.findall(r"\\input\{content/projects/([^}]+)\}", s)
    tags = re.search(r"\\SetTags\{([^}]*)\}", s)
    info["tags"] = split_top(tags.group(1)) if tags else []
    return info, order


def resolve_tagged(s, active):
    """Keep \\tagged{tags}{body} bodies whose tags are active, drop the rest."""
    out, i = [], 0
    for _, start, end in list(find_macros(s, ["tagged"])):
        if start < i:
            continue
        _, (tags, body), j = read_args(s, end, 2)
        out.append(s[i:start])
        if set(split_top(tags)) & set(active):
            out.append(resolve_tagged(body, active))
        i = j
    out.append(s[i:])
    return "".join(out)


def parse_cv(src, active_tags):
    s = resolve_tagged(strip_comments(src), active_tags)
    sections = []
    for m in re.finditer(r"\\section(?![A-Za-z])", s):
        _, (title,), j = read_args(s, m.end(), 1)
        nxt = re.compile(r"\\section(?![A-Za-z])|\\cvsignature").search(s, j)
        body = s[j:nxt.start() if nxt else len(s)]
        sec = {"title": plain(title), "entries": [], "items": [], "text": None}
        if "\\cventry" in body or "\\cvproject" in body:
            pat = re.compile(r"\\(cventry|cvproject)(?![A-Za-z])")
            ms = list(pat.finditer(body))
            for k, em in enumerate(ms):
                n = 4 if em.group(1) == "cventry" else 2
                _, a, e = read_args(body, em.end(), n)
                tail = body[e:ms[k + 1].start() if k + 1 < len(ms) else len(body)]
                bullets = re.search(r"\\begin\{cvbullets\}(.*?)\\end\{cvbullets\}", tail, re.S)
                entry = {"title": tr(a[0]), "right_top": plain(a[1]),
                         "subtitle": tr(a[2]) if n == 4 else None,
                         "right_bottom": plain(a[3]) if n == 4 else None,
                         "bullets": items(bullets.group(1)) if bullets else []}
                sec["entries"].append(entry)
        elif "\\begin{itemize}" in body:
            inner = re.search(r"\\begin\{itemize\}(?:\[[^\]]*\])?(.*?)\\end\{itemize\}", body, re.S)
            sec["items"] = items(inner.group(1))
        else:
            sec["text"] = tr(body)
        sections.append(sec)
    return {"sections": sections}


def report_warnings():
    if WARNINGS:
        print("latex_extract: ignored unknown macros:", ", ".join(sorted(WARNINGS)),
              file=sys.stderr)
