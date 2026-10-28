# Portfolio website: Suavi Yildirim

A static bilingual (EN/DE) portfolio website. It is generated from the **same LaTeX source as the PDF**
(`../CV-Portfolio-LaTeX`), so the texts stay in sync. It is plain HTML/CSS/JS with no framework and no
CDN, so it works offline from the folder and on GitHub Pages.

```
portfolio-website/
├── build.py              # generator: LaTeX -> data/*.json -> docs/
├── tools/latex_extract.py  # reads \tr{EN}{DE}, \projectinfo, \whr, \picrow, cv.tex ...
├── data/
│   ├── site.json         # HAND-EDITED: website-only content (see below)
│   ├── projects.json     # generated from content/projects/*.tex (do not edit)
│   └── cv.json           # generated from content/cv.tex + main.tex (do not edit)
├── src/                  # style.css, main.js, favicon, fonts (Montserrat, OFL), videos
└── docs/                 # THE WEBSITE (generated; this is what GitHub Pages serves)
```

## View it locally

Open `docs/index.html` in a browser, or start a small server, which is closer to GitHub Pages:

```bash
python3 -m http.server 8765 -d docs
```

Then open <http://localhost:8765>. Pages: home, projects (with filters), one page per project, and the CV.
Every page has a German twin under `docs/de/`. The EN/DE button in the header switches between them.

## Update the content

1. Edit the texts in the LaTeX project as usual (`content/projects/*.tex`, `content/cv.tex`, `main.tex`).
2. Rebuild:

   ```bash
   python3 build.py          # pages only (fast)
   ```

   ```bash
   python3 build.py --pdf    # pages + the downloadable PDFs (runs pdflatex twice per language)
   ```

What comes from where:

| On the website | Source |
|---|---|
| Project list and order | the `\input{content/projects/...}` lines in `main.tex` (add or remove a line to add or drop a project) |
| Title, organisation, period, role, keywords, highlight | `\projecttitle` / `\projectinfo` |
| What? / How? / Results | `\whr{..}{..}{..}` and `\pfblock` |
| Pictures | every image used in `\picrow`, `\gridcols`, `\pcell`, `\pimg`, `\includegraphics` |
| CV page | `content/cv.tex`. The `\tagged{..}` bullets shown are set by `cv_tags` in `site.json` (default `mech` + `ai`) |
| Name, e-mail, LinkedIn, degrees | `main.tex` (**the phone number is never read**) |
| Hero text, profile, highlight figures, filter categories, cover pictures, videos, extra galleries | `data/site.json` |

`site.json`, per project (`"projects": {"<file name>": {...}}`):

- `categories`: any of `robotics`, `automation`, `design`, `ai-sim` (the filter buttons).
- `cover`: the picture on the card and at the top of the project page (default: its first picture).
- `videos`: `[{"file": "x.mp4", "poster": "picture-name", "caption": {"en": "..", "de": ".."}}]`. Put the MP4 in `src/video/`.
- `links`: buttons under the title, e.g. a live demo: `[{"href": "https://..." or {"en": "..", "de": ".."}, "label": {"en": "..", "de": ".."}}]`.
- `extra_images` / `extra_galleries`: pictures that are on the website but not in the PDF. They must be in
  `../CV-Portfolio-LaTeX/images/projects/`.

A new project without a `site.json` entry still appears; the build only notes that it has no categories.

### Videos

The hackathon clips in `src/video/` are copies of the expert-success clips in
`05_Projects/Siemens-Healthineers-Hackathon/report_data/PRESENTATION_VIDEOS/01_expert_success/`. They were
remuxed without re-encoding, with "fast start" so that they stream in the browser:

```bash
avconvert -s input.mp4 -p PresetPassthrough -o src/video/output.mp4 --replace
```

Keep clips under about 10 MB (GitHub's limit is 100 MB per file, but visitors on phones will thank you).

### PDFs and the phone number

`build.py --pdf` compiles the EN and DE PDFs in a temporary copy of the LaTeX project. In that copy it
removes `\Phone{..}` and the phone line from the CV header and the portfolio header. Your LaTeX files are not
changed. If the layout in `cvportfolio.sty` changes so that the phone line can no longer be removed cleanly,
the build stops instead of publishing it. To show the phone number anyway, set `"show_phone": true` in
`site.json`.

## Publish on GitHub Pages

Nothing has been published yet. These steps are yours to run:

1. Create a new **public** repository on GitHub, for example `portfolio` (or `<username>.github.io` for
   the shorter address `https://<username>.github.io/`).
2. In this folder:

   ```bash
   git init && git add . && git commit -m "Portfolio website"
   ```

   ```bash
   git branch -M main && git remote add origin https://github.com/<username>/portfolio.git && git push -u origin main
   ```

3. On GitHub: **Settings → Pages → Build and deployment → Deploy from a branch → `main` / `/docs` → Save**.
   After about a minute the site is live at `https://<username>.github.io/portfolio/`.
4. Put that address into `site.json` as `"base_url"` and rebuild. This adds the canonical, hreflang and
   **og:image** tags, so LinkedIn shows a preview picture when you share the link. Then commit and push again.
5. On LinkedIn: **Profile → Contact info → Website** and/or **Featured → Add a link**.

To update the live site later: `python3 build.py --pdf`, then `git add . && git commit -m "Update" && git push`.

Notes:

- `docs/.nojekyll` tells GitHub not to run Jekyll, so the folder is served exactly as it is.
- The repository holds your photo, the PDFs (about 8 MB each) and the videos. Anything in a public
  repository is public, so check `docs/` before you push.
- A private, non-commercial portfolio usually needs no *Impressum*. If you add one, keep your home address out
  of the repository history.

## Requirements

Python 3.12 or newer (it uses the newer f-string syntax), standard library only. `sips` (macOS) makes the thumbnails; on other systems the images
are copied at full size. `pdflatex` (MacTeX) is needed for `--pdf`.
In Firefox, pages opened directly from the folder (`file://`) may fall back to a system font. Use the local
server above, or the published site, to see Montserrat.
