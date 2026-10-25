#!/usr/bin/env python3
"""Build the portfolio website from the LaTeX CV + portfolio.

    python3 build.py            # LaTeX -> data/*.json -> docs/ (the website)
    python3 build.py --no-extract   # skip LaTeX, build from data/*.json as they are
    python3 build.py --pdf      # also compile the public PDFs (no phone number)

Only the Python standard library is used (plus `sips` on macOS for thumbnails
and pdflatex for --pdf).  The output in docs/ is plain HTML/CSS/JS that works
from the folder (file://) and on GitHub Pages.
"""
import argparse
import datetime
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))
import latex_extract as L  # noqa: E402

DATA, SRC, OUT = ROOT / "data", ROOT / "src", ROOT / "docs"
LANGS = ("en", "de")

UI = {
    "nav_home": ("Home", "Start"), "nav_projects": ("Projects", "Projekte"),
    "nav_cv": ("CV", "Lebenslauf"), "all": ("All", "Alle"),
    "what": ("What?", "Was?"), "how": ("How?", "Wie?"), "results": ("Results", "Ergebnisse"),
    "videos": ("Videos", "Videos"), "gallery": ("Pictures", "Bilder"),
    "featured": ("Selected projects", "Ausgewählte Projekte"),
    "all_projects": ("All projects", "Alle Projekte"),
    "profile": ("Profile", "Profil"),
    "worked_with": ("Industry, research and competitions", "Industrie, Forschung und Wettbewerbe"),
    "download_cv": ("Download CV + portfolio (PDF)", "Lebenslauf + Portfolio herunterladen (PDF)"),
    "download_other": ("German version (PDF)", "Englische Version (PDF)"),
    "contact": ("Contact", "Kontakt"), "back": ("All projects", "Alle Projekte"),
    "prev": ("Previous", "Vorheriges"), "next": ("Next", "Nächstes"),
    "role": ("Role", "Rolle"), "projects_intro": (
        "Robotics, automation and design work from industry, research and competitions. "
        "Filter by topic or open a project for details, pictures and videos.",
        "Projekte aus Industrie, Forschung und Wettbewerben in Robotik, Automatisierung und "
        "Konstruktion. Nach Thema filtern oder ein Projekt für Details, Bilder und Videos öffnen."),
    "cv_intro": ("The same content as the PDF that I send with applications.",
                 "Derselbe Inhalt wie im PDF, das ich mit Bewerbungen versende."),
    "close": ("Close", "Schließen"), "lang_name": ("Deutsch", "English"),
    "built": ("Built from the same LaTeX source as my PDF portfolio.",
              "Erstellt aus derselben LaTeX-Quelle wie mein PDF-Portfolio."),
    "no_video": ("Your browser cannot play this video.", "Ihr Browser kann dieses Video nicht abspielen."),
    "count": ("projects", "Projekte"), "skip": ("Skip to content", "Zum Inhalt springen"),
}


def ui(key, lang):
    return UI[key][LANGS.index(lang)]


def esc(s):
    return html.escape(s or "", quote=True)


def strip_tags(s):
    """HTML fragment -> plain text (for alt text, titles and meta tags)."""
    return html.unescape(re.sub(r"<[^>]+>", "", s or ""))


def pdf_name(lang):
    return f"Suavi-Yildirim-CV-Portfolio-{lang.upper()}.pdf"


# ================================================================ extract
def extract(site):
    latex = (ROOT / site["latex_dir"]).resolve()
    person, order = L.parse_main((latex / "main.tex").read_text(encoding="utf-8"))
    projects = []
    for slug in order:
        p = L.parse_project((latex / "content/projects" / f"{slug}.tex").read_text(encoding="utf-8"), slug)
        projects.append(p)
    cv = L.parse_cv((latex / "content/cv.tex").read_text(encoding="utf-8"), site["cv_tags"])
    cv["person"] = person
    L.report_warnings()
    DATA.mkdir(exist_ok=True)
    for name, obj in (("projects.json", projects), ("cv.json", cv)):
        (DATA / name).write_text(json.dumps(obj, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"extract: {len(projects)} projects, {len(cv['sections'])} CV sections -> data/")


# ================================================================== pages
class Page:
    """Knows where a page lives so it can write relative links."""

    def __init__(self, lang, path):
        self.lang, self.path = lang, path            # path relative to the language root
        depth = path.count("/") + (1 if lang == "de" else 0)
        self.up = "../" * depth                      # to docs/
        self.home = "../" * path.count("/")          # to this language's root

    def asset(self, p):
        return self.up + "assets/" + p

    def link(self, p):
        return self.home + p

    def other(self):
        """Same page in the other language."""
        if self.lang == "en":
            return self.up + "de/" + self.path
        return self.up + self.path


def layout(page, site, cv, title, body, description="", active="", og_image=None):
    lang = page.lang
    person = cv["person"]
    name = person["name"]["en"]
    full_title = f"{title} – {name}" if title != name else name
    base = site.get("base_url", "").rstrip("/")
    head_extra = ""
    if base:
        canon = f"{base}/{'de/' if lang == 'de' else ''}{page.path}"
        en_url = f"{base}/{page.path}"
        de_url = f"{base}/de/{page.path}"
        head_extra += (f'<link rel="canonical" href="{canon}">\n'
                       f'<link rel="alternate" hreflang="en" href="{en_url}">\n'
                       f'<link rel="alternate" hreflang="de" href="{de_url}">\n'
                       f'<meta property="og:url" content="{canon}">\n')
        img = og_image or "img/photo.jpg"
        head_extra += f'<meta property="og:image" content="{base}/assets/{img}">\n'
    nav = "".join(
        f'<a href="{page.link(href)}"{' aria-current="page"' if active == key else ""}>{ui(key, lang)}</a>'
        for key, href in (("nav_home", "index.html"), ("nav_projects", "projects.html"),
                          ("nav_cv", "cv.html")))
    other = "de" if lang == "en" else "en"
    linkedin = person["linkedin"]["en"]
    email = person["email"]["en"]
    year = datetime.date.today().year
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(strip_tags(description))}">
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(full_title)}">
<meta property="og:description" content="{esc(strip_tags(description))}">
{head_extra}<link rel="icon" href="{page.asset('img/favicon.svg')}" type="image/svg+xml">
<link rel="stylesheet" href="{page.asset('style.css')}">
<script>document.documentElement.classList.add('js')</script>
</head>
<body data-lang="{lang}">
<a class="skip" href="#main">{ui('skip', lang)}</a>
<header class="site-header">
  <div class="wrap header-inner">
    <a class="brand" href="{page.link('index.html')}">{esc(name)}</a>
    <nav class="main-nav" aria-label="Main">{nav}</nav>
    <a class="lang-toggle" href="{page.other()}" hreflang="{other}" lang="{other}" data-set-lang="{other}"
       title="{ui('lang_name', lang)}"><span aria-hidden="true">{other.upper()}</span><span class="sr">{ui('lang_name', lang)}</span></a>
  </div>
</header>
<main id="main">
{body}
</main>
<footer class="site-footer">
  <div class="wrap footer-inner">
    <div>
      <strong>{esc(name)}</strong><br>
      <a href="mailto:{esc(email)}">{esc(email)}</a> ·
      <a href="https://{esc(linkedin)}" rel="noopener">LinkedIn</a>
    </div>
    <div class="muted">© {year} {esc(name)} · {ui('built', lang)}</div>
  </div>
</footer>
<script src="{page.asset('main.js')}"></script>
</body>
</html>
"""


def img_tag(page, file, alt="", cls="", thumb=False, lazy=True, sizes=None):
    folder = "thumbs" if thumb else "projects"
    src = page.asset(f"img/{folder}/{file}.jpg")
    w, h = IMAGE_SIZES.get((folder, file), (None, None))
    dims = f' width="{w}" height="{h}"' if w else ""
    return (f'<img src="{src}" alt="{esc(alt)}"{dims}'
            f'{' loading="lazy"' if lazy else ""}{f' class="{cls}"' if cls else ""}>')


def logo_tag(page, logo, alt):
    ext = ".svg" if (SRC / "logos" / f"{logo}.svg").exists() else ".png"
    return f'<img class="logo" src="{page.asset("img/logos/" + logo + ext)}" alt="{esc(alt)}">'


def cover_of(p, site):
    cfg = site["projects"].get(p["slug"], {})
    if cfg.get("cover"):
        return cfg["cover"]
    for g in p["galleries"]:
        if g["images"]:
            return g["images"][0]["file"]
    return None


def card(page, p, site):
    lang = page.lang
    cats = site["projects"].get(p["slug"], {}).get("categories", [])
    cover = cover_of(p, site)
    chips = "".join(f'<span class="chip">{site["categories"][c][lang]}</span>' for c in cats)
    meta = " · ".join(x for x in (p["org"][lang], p["period"][lang]) if x)
    logo = logo_tag(page, p["logos"][0], "") if p.get("logos") else ""
    return f"""<li class="card" data-cats="{' '.join(cats)}">
  <a href="{page.link('projects/' + p['slug'] + '.html')}">
    <div class="card-img">{img_tag(page, cover, strip_tags(p['title'][lang]), thumb=True) if cover else ''}</div>
    <div class="card-body">
      <div class="card-top"><span class="card-meta">{meta}</span>{logo}</div>
      <h3>{p['title'][lang]}</h3>
      {f'<p class="highlight">{p["highlight"][lang]}</p>' if p['highlight'][lang] else ''}
      <div class="chips">{chips}</div>
    </div>
  </a>
</li>"""


def build_home(lang, site, cv, projects):
    page = Page(lang, "index.html")
    person = cv["person"]
    by_slug = {p["slug"]: p for p in projects}
    figs = "".join(
        f'<li><span class="fig-value">{f.get("value_" + lang, f["value"]).replace("{count}", str(len(projects)))}</span>'
        f'<span class="fig-label">{f["label"][lang]}</span></li>' for f in site["figures"])
    featured = "".join(card(page, by_slug[s], site) for s in site["featured"] if s in by_slug)
    logos = "".join(f'<li>{logo_tag(page, l["file"], l["name"])}</li>' for l in site["logos"])
    email, linkedin = person["email"]["en"], person["linkedin"]["en"]
    body = f"""
<section class="band hero">
  <div class="wrap hero-inner">
    <div class="hero-text">
      <p class="eyebrow">{site['headline'][lang]}</p>
      <h1>{esc(person['name'][lang])}</h1>
      <p class="degrees">{person['degreea'][lang]}<br>{person['degreeb'][lang]}</p>
      <p class="lead">{site['tagline'][lang]}</p>
      <div class="actions">
        <a class="btn primary" href="{page.link('projects.html')}">{ui('nav_projects', lang)}</a>
        <a class="btn" href="{page.asset('pdf/' + pdf_name(lang))}" download>{ui('download_cv', lang)}</a>
        <a class="btn ghost" href="https://{esc(linkedin)}" rel="noopener">LinkedIn</a>
        <a class="btn ghost" href="mailto:{esc(email)}">E-Mail</a>
      </div>
    </div>
    <img class="portrait" src="{page.asset('img/photo.jpg')}" alt="{esc(person['name'][lang])}" width="{IMAGE_SIZES.get(('img', 'photo'), (480, 600))[0]}" height="{IMAGE_SIZES.get(('img', 'photo'), (480, 600))[1]}">
  </div>
</section>
<section class="wrap">
  <ul class="figures">{figs}</ul>
</section>
<section class="wrap profile">
  <h2 class="section-title">{ui('profile', lang)}</h2>
  <p>{site['profile'][lang]}</p>
</section>
<section class="wrap">
  <div class="section-head"><h2 class="section-title">{ui('featured', lang)}</h2>
    <a class="more" href="{page.link('projects.html')}">{ui('all_projects', lang)} ({len(projects)}) →</a></div>
  <ul class="cards">{featured}</ul>
</section>
<section class="band band-light">
  <div class="wrap">
    <h2 class="section-title">{ui('worked_with', lang)}</h2>
    <ul class="logo-row">{logos}</ul>
  </div>
</section>
"""
    return page, layout(page, site, cv, person["name"]["en"], body,
                        description=site["tagline"][lang], active="nav_home")


def build_projects(lang, site, cv, projects):
    page = Page(lang, "projects.html")
    buttons = f'<button type="button" class="filter" data-filter="all" aria-pressed="true">{ui("all", lang)}</button>'
    for key, label in site["categories"].items():
        n = sum(key in site["projects"].get(p["slug"], {}).get("categories", []) for p in projects)
        buttons += (f'<button type="button" class="filter" data-filter="{key}" aria-pressed="false">'
                    f'{label[lang]} <span class="n">{n}</span></button>')
    cards = "".join(card(page, p, site) for p in projects)
    body = f"""
<section class="band page-head">
  <div class="wrap">
    <h1>{ui('nav_projects', lang)}</h1>
    <p class="lead">{ui('projects_intro', lang)}</p>
    <div class="filters" role="group" aria-label="Filter">{buttons}</div>
  </div>
</section>
<section class="wrap">
  <ul class="cards" id="project-grid">{cards}</ul>
</section>
"""
    return page, layout(page, site, cv, ui("nav_projects", lang), body,
                        description=ui("projects_intro", lang), active="nav_projects")


def build_project(lang, site, cv, projects, idx):
    p = projects[idx]
    page = Page(lang, f"projects/{p['slug']}.html")
    cfg = site["projects"].get(p["slug"], {})
    title = p["title"][lang]
    logos = "".join(logo_tag(page, l, "") for l in p.get("logos", []))
    if p.get("logo_text"):
        logos += f'<span class="logo-text">{esc(p["logo_text"])}</span>'
    info = []
    for label, val in ((None, p["org"][lang]), (None, p["period"][lang]), ("role", p["role"][lang])):
        if val:
            info.append(f'<span>{val}</span>')
    chips = "".join(f'<span class="chip">{k[lang]}</span>' for k in p["keywords"])
    cats = "".join(f'<a class="chip cat" href="{page.link("projects.html")}#{c}">{site["categories"][c][lang]}</a>'
                   for c in cfg.get("categories", []))

    def block(sec):
        head = sec["title"][lang] if sec["key"] == "custom" else ui(sec["key"], lang)
        lis = "".join(f"<li>{it[lang]}</li>" for it in sec["items"])
        return f'<div class="whr-block whr-{sec["key"]}"><h2>{head}</h2><ul>{lis}</ul></div>'

    main_secs = [s for s in p["sections"] if s["key"] != "custom"]
    extra_secs = [s for s in p["sections"] if s["key"] == "custom"]
    whr = "".join(block(s) for s in main_secs)

    cover = cover_of(p, site)
    hero = (f'<figure class="project-hero">{img_tag(page, cover, strip_tags(title), lazy=False)}</figure>'
            if cover else "")

    videos = ""
    if cfg.get("videos"):
        vs = ""
        for v in cfg["videos"]:
            poster = f' poster="{page.asset("img/projects/" + v["poster"] + ".jpg")}"' if v.get("poster") else ""
            vs += (f'<figure class="video"><video controls muted playsinline preload="metadata"{poster}>'
                   f'<source src="{page.asset("video/" + v["file"])}" type="video/mp4">{ui("no_video", lang)}</video>'
                   f'<figcaption>{v["caption"][lang]}</figcaption></figure>')
        videos = f'<section class="wrap"><h2 class="section-title">{ui("videos", lang)}</h2><div class="videos">{vs}</div></section>'

    galleries = ""
    extra_imgs = [{"file": f, "caption": None} for f in cfg.get("extra_images", [])]
    gals = [dict(g) for g in p["galleries"]]
    if extra_imgs:
        if gals:
            gals[0] = {**gals[0], "images": gals[0]["images"] + extra_imgs}
        else:
            gals = [{"heading": None, "images": extra_imgs}]
    gals += cfg.get("extra_galleries", [])  # website-only pictures from site.json
    for g in gals:
        heading = g["heading"][lang] if g.get("heading") else ui("gallery", lang)
        # an extra block ("Next step: ...") is shown next to its own pictures
        sec_html = (f'<ul class="gallery-text">{"".join(f"<li>{t[lang]}</li>" for t in g["text"])}</ul>'
                    if g.get("text") else "")
        for s in extra_secs:
            if g.get("heading") and s["title"][lang] == g["heading"][lang]:
                lis = "".join(f"<li>{it[lang]}</li>" for it in s["items"])
                sec_html = f'<ul class="gallery-text">{lis}</ul>'
                extra_secs = [x for x in extra_secs if x is not s]
        figs = ""
        for im in g["images"]:
            cap = im["caption"][lang] if im.get("caption") else ""
            alt = cap or strip_tags(title)
            figs += (f'<figure><a href="{page.asset("img/projects/" + im["file"] + ".jpg")}" class="zoom" '
                     f'data-caption="{esc(cap)}">{img_tag(page, im["file"], alt, thumb=True)}</a>'
                     f'{f"<figcaption>{cap}</figcaption>" if cap else ""}</figure>')
        small = " small" if all(IMAGE_SIZES.get(("projects", i["file"]), (999, 0))[0] < 400 for i in g["images"]) else ""
        galleries += (f'<section class="wrap"><h2 class="section-title">{heading}</h2>{sec_html}'
                      f'<div class="gallery{small}">{figs}</div></section>')
    leftover = "".join(block(s) for s in extra_secs)

    prev_p, next_p = projects[idx - 1], projects[(idx + 1) % len(projects)]
    pager = (f'<nav class="wrap pager" aria-label="Projects">'
             f'<a href="{prev_p["slug"]}.html"><span>← {ui("prev", lang)}</span><strong>{prev_p["title"][lang]}</strong></a>'
             f'<a href="{next_p["slug"]}.html" class="next"><span>{ui("next", lang)} →</span><strong>{next_p["title"][lang]}</strong></a></nav>')

    body = f"""
<section class="band page-head project-head">
  <div class="wrap">
    <a class="back" href="{page.link('projects.html')}">← {ui('back', lang)}</a>
    <div class="title-row"><h1>{title}</h1><div class="logos">{logos}</div></div>
    <p class="info">{' <span class="sep">|</span> '.join(info)}</p>
    {f'<p class="highlight big">{p["highlight"][lang]}</p>' if p['highlight'][lang] else ''}
    <div class="chips">{cats}{chips}</div>
  </div>
</section>
<section class="wrap">
  {hero}
  <div class="whr">{whr}</div>
  {f'<div class="whr">{leftover}</div>' if leftover else ''}
</section>
{videos}
{galleries}
{pager}
"""
    desc = p["highlight"][lang] or strip_tags(title)
    og = f"img/projects/{cover}.jpg" if cover else None
    return page, layout(page, site, cv, strip_tags(title), body, description=desc,
                        active="nav_projects", og_image=og)


def build_cv(lang, site, cv):
    page = Page(lang, "cv.html")
    person = cv["person"]
    other = "de" if lang == "en" else "en"
    parts = []
    for sec in cv["sections"]:
        if sec["title"]["en"] == "Skills" and site.get("cv_skills"):
            sec = {**sec, "items": site["cv_skills"]}  # longer website-only list (the PDF keeps its own)
        inner = ""
        if sec["text"]:
            inner = f'<p class="cv-text">{sec["text"][lang]}</p>'
        for e in sec["entries"]:
            sub = ""
            if e["subtitle"]:
                sub = f'<div class="cv-row sub"><span>{e["subtitle"][lang]}</span><span>{e["right_bottom"][lang]}</span></div>'
            bullets = "".join(f"<li>{b[lang]}</li>" for b in e["bullets"])
            inner += (f'<div class="cv-entry"><div class="cv-row"><strong>{e["title"][lang]}</strong>'
                      f'<span>{e["right_top"][lang]}</span></div>{sub}'
                      f'{f"<ul>{bullets}</ul>" if bullets else ""}</div>')
        if sec["items"]:
            inner += "<ul class=\"cv-list\">" + "".join(f"<li>{i[lang]}</li>" for i in sec["items"]) + "</ul>"
        parts.append(f'<section class="cv-section"><h2>{sec["title"][lang]}</h2>{inner}</section>')
    body = f"""
<section class="band page-head">
  <div class="wrap cv-head">
    <div>
      <h1>{ui('nav_cv', lang)}</h1>
      <p class="lead">{ui('cv_intro', lang)}</p>
    </div>
    <div class="actions">
      <a class="btn primary" href="{page.asset('pdf/' + pdf_name(lang))}" download>{ui('download_cv', lang)}</a>
      <a class="btn" href="{page.asset('pdf/' + pdf_name(other))}" download>{ui('download_other', lang)}</a>
    </div>
  </div>
</section>
<article class="wrap cv">
  <header class="cv-person">
    <img src="{page.asset('img/photo.jpg')}" alt="" width="96" height="120">
    <div>
      <h2>{esc(person['name'][lang])}</h2>
      <p>{person['degreea'][lang]}<br>{person['degreeb'][lang]}</p>
      <p><a href="mailto:{esc(person['email']['en'])}">{esc(person['email']['en'])}</a> ·
         <a href="https://{esc(person['linkedin']['en'])}" rel="noopener">{esc(person['linkedin']['en'])}</a></p>
    </div>
  </header>
  {''.join(parts)}
</article>
"""
    summary = next((s["text"][lang] for s in cv["sections"] if s["text"]), "")
    return page, layout(page, site, cv, ui("nav_cv", lang), body, description=summary, active="nav_cv")


# ================================================================= assets
IMAGE_SIZES = {}


def image_size(path):
    """Width/height of a JPEG or PNG without third-party libraries."""
    b = path.read_bytes()
    if b[:8] == b"\x89PNG\r\n\x1a\n":
        return int.from_bytes(b[16:20], "big"), int.from_bytes(b[20:24], "big")
    i = 2
    while i < len(b):
        if b[i] != 0xFF:
            i += 1
            continue
        marker = b[i + 1]
        seg = int.from_bytes(b[i + 2:i + 4], "big")
        if marker in (0xC0, 0xC1, 0xC2):
            return int.from_bytes(b[i + 7:i + 9], "big"), int.from_bytes(b[i + 5:i + 7], "big")
        i += 2 + seg
    return None, None


def resize(src, dst, max_px):
    """Copy src to dst, scaled down to max_px (macOS sips; plain copy elsewhere)."""
    w, h = image_size(src)
    if w and max(w, h) > max_px and shutil.which("sips"):
        subprocess.run(["sips", "-Z", str(max_px), str(src), "--out", str(dst)],
                       check=True, capture_output=True)
    else:
        shutil.copy2(src, dst)


def copy_assets(site, projects):
    latex = (ROOT / site["latex_dir"]).resolve()
    a = OUT / "assets"
    for sub in ("img/projects", "img/thumbs", "img/logos", "video", "fonts", "pdf"):
        (a / sub).mkdir(parents=True, exist_ok=True)
    used = set()
    for p in projects:
        for g in p["galleries"]:
            used |= {i["file"] for i in g["images"]}
        cfg = site["projects"].get(p["slug"], {})
        used |= set(cfg.get("extra_images", []))
        used |= {i["file"] for g in cfg.get("extra_galleries", []) for i in g["images"]}
        used |= {v["poster"] for v in cfg.get("videos", []) if v.get("poster")}
        if cfg.get("cover"):
            used.add(cfg["cover"])
    for name in sorted(used):
        src = latex / "images/projects" / f"{name}.jpg"
        if not src.exists():
            print(f"warning: missing image {src}", file=sys.stderr)
            continue
        for folder, px in (("projects", 1600), ("thumbs", 760)):
            dst = a / "img" / folder / f"{name}.jpg"
            if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
                resize(src, dst, px)
            IMAGE_SIZES[(folder, name)] = image_size(dst)
    for logo in (latex / "images/logos").glob("*.png"):
        shutil.copy2(logo, a / "img/logos" / logo.name)
    photo = a / "img/photo.jpg"
    resize(latex / "images/photo.jpg", photo, 720)
    IMAGE_SIZES[("img", "photo")] = image_size(photo)
    for logo in (SRC / "logos").glob("*.*"):  # website-only logos (e.g. FAU)
        shutil.copy2(logo, a / "img/logos" / logo.name)
    for d in ("video", "fonts"):
        for f in (SRC / d).glob("*"):
            if f.is_file() and not f.name.startswith("."):
                shutil.copy2(f, a / d / f.name)
    for f in ("style.css", "main.js"):
        shutil.copy2(SRC / f, a / f)
    shutil.copy2(SRC / "favicon.svg", a / "img/favicon.svg")
    for lang in LANGS:
        if not (a / "pdf" / pdf_name(lang)).exists():
            print(f"note: {pdf_name(lang)} not built yet – run `python3 build.py --pdf`", file=sys.stderr)
    (OUT / ".nojekyll").write_text("")


# ==================================================================== PDF
def build_pdfs(site):
    """Compile EN + DE PDFs from a temporary copy of the LaTeX project, with the
    phone number removed (unless site.json says show_phone: true)."""
    latex = (ROOT / site["latex_dir"]).resolve()
    if not shutil.which("pdflatex"):
        sys.exit("pdflatex not found – install MacTeX or copy the PDFs to docs/assets/pdf/ by hand")
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "latex"
        shutil.copytree(latex, work, ignore=shutil.ignore_patterns("*.zip", "*.pdf", ".git"))
        if not site.get("show_phone"):
            main = (work / "main.tex").read_text(encoding="utf-8")
            main, n = re.subn(r"^\s*\\Phone\{[^}]*\}.*$", "", main, flags=re.M)
            sty = (work / "cvportfolio.sty").read_text(encoding="utf-8")
            sty, n1 = re.subn(r"\\cv@phone\\enspace\$\|\$\\enspace", "", sty)
            sty, n2 = re.subn(r"\\\\\[5pt\]\s*\\pf@contactline\{\\faPhone\*\}\{\\cv@phone\}", "", sty)
            if (n, n1, n2) != (1, 1, 1):
                sys.exit(f"could not remove the phone number cleanly ({n}, {n1}, {n2}); "
                         "the LaTeX layout changed – update build_pdfs() before publishing")
            (work / "main.tex").write_text(main, encoding="utf-8")
            (work / "cvportfolio.sty").write_text(sty, encoding="utf-8")
        out = OUT / "assets/pdf"
        out.mkdir(parents=True, exist_ok=True)
        for lang, tex in (("en", "main.tex"), ("de", "main-de.tex")):
            for _ in range(2):  # twice, for the clickable overview page numbers
                r = subprocess.run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex],
                                   cwd=work, capture_output=True, text=True)
                if r.returncode:
                    sys.exit(f"pdflatex failed for {tex}:\n" + r.stdout[-3000:])
            shutil.copy2(work / tex.replace(".tex", ".pdf"), out / pdf_name(lang))
            print(f"pdf: {pdf_name(lang)}")


# =================================================================== main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-extract", action="store_true", help="use data/*.json as they are")
    ap.add_argument("--pdf", action="store_true", help="also compile the public PDFs")
    args = ap.parse_args()

    site = json.loads((DATA / "site.json").read_text(encoding="utf-8"))
    if not args.no_extract:
        extract(site)
    projects = json.loads((DATA / "projects.json").read_text(encoding="utf-8"))
    cv = json.loads((DATA / "cv.json").read_text(encoding="utf-8"))

    for p in projects:
        if p["slug"] not in site["projects"]:
            print(f"note: {p['slug']} has no entry in site.json (no filter categories)", file=sys.stderr)

    OUT.mkdir(exist_ok=True)
    copy_assets(site, projects)
    if args.pdf:
        build_pdfs(site)

    count = 0
    for lang in LANGS:
        root = OUT if lang == "en" else OUT / "de"
        pages = [build_home(lang, site, cv, projects), build_projects(lang, site, cv, projects),
                 build_cv(lang, site, cv)]
        pages += [build_project(lang, site, cv, projects, i) for i in range(len(projects))]
        for page, text in pages:
            dst = root / page.path
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(text, encoding="utf-8")
            count += 1
    # remove pages of projects that were dropped from main.tex
    keep = {f"{p['slug']}.html" for p in projects}
    for d in (OUT / "projects", OUT / "de/projects"):
        for f in d.glob("*.html"):
            if f.name not in keep:
                f.unlink()
    print(f"build: {count} pages -> docs/  (open docs/index.html)")


if __name__ == "__main__":
    main()
