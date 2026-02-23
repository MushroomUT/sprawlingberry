# sprawlingberry.com (static)

This repo is a minimalist, writing-first **Hugo** site scaffold with optional **EN/ZH bilingual** support.

## Why Hugo (choice rationale)
- Fast builds, tiny runtime (static HTML).
- Built-in multilingual routing + translation linking.
- Low-maintenance (no database, no server).

## Local development

### 1) Install Hugo
- macOS (Homebrew):
  ```bash
  brew install hugo
  ```
- Or download: https://gohugo.io/getting-started/installing/

### 2) Run dev server
From the repo root:
```bash
hugo server -D
```
Open http://localhost:1313

### 3) Create new posts
English:
```bash
hugo new content/en/posts/my-story.md
```
Chinese:
```bash
hugo new content/zh/posts/my-story.md
```
To link translations, set the same `translationKey` in both files.

## Information Architecture (proposed)
- **Home**: latest posts, short intro.
- **Stories (Posts)**: reverse-chronological list.
- **Series** (optional): long-running story arcs.
- **Tags**: themes/genres/tropes.
- **About**: author bio + contact/social.
- (Optional) **Now**: what you’re working on.
- (Optional) **Newsletter/RSS**: RSS is automatic; newsletter depends on provider.

## Deployment options

### Option A — GitHub Pages (recommended if already on GitHub)
1. Create a GitHub repo.
2. Push this folder.
3. Add GitHub Actions workflow (see below) to build + deploy.
4. In GitHub Pages settings, set source = GitHub Actions.
5. Point DNS to GitHub Pages.

### Option B — Cloudflare Pages (recommended for easiest DNS/HTTPS)
1. Connect the repo in Cloudflare Pages.
2. Framework preset: **Hugo**.
3. Build command: `hugo --minify`
4. Output directory: `public`
5. Set custom domains (sprawlingberry.com + www).
6. Cloudflare will issue/renew TLS automatically.

## DNS + HTTPS best practices
- Prefer serving **HTTPS-only**; redirect HTTP → HTTPS.
- Canonicalize to *either* apex or www (pick one, redirect the other).
- If using Cloudflare: enable “Always Use HTTPS”, and set HSTS only after verifying redirects.
- Keep TTL moderate (e.g., 300–3600s) during migration.

## Next steps (inputs needed)
Please answer these so we can lock the final structure/theme:
1. **Brand/title**: keep “Sprawling Berry” or different site title (EN + optional ZH)?
2. **Sections**: Posts only, or also Series / Now / Links / Newsletter / Projects?
3. **Hosting preference**: GitHub Pages or Cloudflare Pages?
4. **URL style**: `/yyyy/mm/slug/` (current) vs `/slug/`?
5. **Bilingual**: fully bilingual, or “mostly EN with occasional ZH” (or vice versa)?
