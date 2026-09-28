# Cool People Have Dogs — static site

Plain static HTML generated from Markdown content files. No WordPress,
no Webflow — content and design are separate, and every edit is either
a prompt to Claude or a form on `/admin`.

## How it's organized

- `content/articles/*.md` — one file per article, front matter (title,
  category, meta description, hero image, FAQ, etc.) + the body below
  the `---` line.
- `content/pages/*.md` — Home, Library, About, 404.
- `templates/*.html` — Jinja2 templates (base layout, article layout,
  generic page layout).
- `static/css/style.css` — the whole design system in one file.
- `admin/` — Decap CMS, a free visual editor at `yoursite.com/admin`.
- `build.py` — reads `content/` + `templates/`, writes plain HTML into
  `output/`. That's what actually gets hosted.

## First-time setup (you, once)

1. **Create a GitHub repo** and push this folder to it.
2. **Connect it to Netlify**: New site from Git → pick the repo. Netlify
   reads `netlify.toml` automatically (build command + publish folder
   are already set — nothing to configure).
3. **Point your domain** at the Netlify site (Netlify's domain settings
   walk you through the DNS records).
4. **Turn on the visual editor** (optional but recommended): in Netlify,
   go to Site settings → Identity → enable, then enable Git Gateway
   under Identity → Services. Invite yourself as a user. Then
   `yoursite.com/admin` lets you log in and edit articles/photos/
   downloads with a form — no code.

## Ongoing edits

- **Ask Claude** — the normal way. Claude edits the files in
  `content/`, runs `python3 build.py` to confirm it renders, and pushes
  the change; Netlify redeploys automatically.
- **Edit it yourself** — go to `/admin`, log in, edit the article's
  text, swap the photo, or attach a new downloadable file, and publish.
  Same repo, same deploy pipeline either way.

## Local build (for Claude, or to preview before pushing)

```
pip install -r requirements.txt
python3 build.py
```

Output lands in `output/` — open `output/index.html` in a browser to
preview the whole site.

## What's ported from the original design vs. still a stand-in

- All 43 articles, Home, Library, About, and 404 are fully converted —
  same copy, same layout, same category colors.
- Every article currently shows an illustrated placeholder in place of
  a real photo (exactly like the original prototype did) — add real
  photos any time via `/admin` or by asking Claude, no template changes
  needed.
- Privacy Policy and Terms are still `#` placeholder links, same as in
  the original prototype — real pages can be added before launch.
- Newsletter/download signup forms render but don't submit anywhere
  yet — wire up an email service (ConvertKit, Mailchimp, or a Netlify
  Form) when ready to start collecting emails.
