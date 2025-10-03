# Repository Overview

## Project Description
- **What this project does**: Hosts a static site that digitizes Gran’s Country Cupboard, a collection of family recipes originally handwritten by Elizabeth M. McGinley.
- **Main purpose and goals**: Provide an online, searchable, and readable version of the historic cookbook so family members and hobby cooks can preserve and use the recipes.
- **Key technologies used**:
  - **Jekyll** (Ruby) – static site generator with the Minima remote theme.
  - **Markdown** – source format for recipes, chapters, and pages.
  - **Ruby gems** – `jekyll-relative-links`, `jekyll-sitemap`, `jekyll-titles-from-headings`, `jekyll-remote-theme`, `jekyll-github-metadata`, `jekyll-resize`, and `wdm` for Windows.
  - **Python utilities** – `_tools/format_recipes.py` normalises tables, fractions, and temperatures; `recipe_stats.py` generates statistics.
  - **Node.js + Wrangler** – builds `pages` and deploys to Cloudflare Pages.

## Architecture Overview
- **High‑level architecture**: Markdown source ➜ Jekyll build ➜ static assets in `_site` ➜ Cloudflare Pages hosting.
- **Main components**:
  1. **Source content** – `_book_recipes/`, `_book_pages/`, `_book_chapters/`, `categories/`, `ingredients/`.
  2. **Static site generator** – Jekyll, configured via `_config.yml` and remote Minima theme.
  3. **Pre‑processing tools** – Python scripts in `_tools/`.
  4. **Build & deploy** – `bundle exec jekyll build`, `bundle exec jekyll serve`; deployment via `wrangler publish`.
- **Data flow**: Authors edit markdown → optional formatting script runs → Jekyll generates HTML/CSS → Cloudflare Pages serves the static site.

## Directory Structure
| Directory | Purpose |
|-----------|---------|
| `/_config.yml` | Global Jekyll settings, collections, theme, plugins |
| `/_book_recipes` | Individual recipe markdown files (`layout: recipe`) |
| `/_book_pages` | Numbered pages that compose the book flow |
| `/_book_chapters` | Chapter markdown files |
| `/_includes`, `/_layouts` | Jekyll template files from the Minima theme |
| `/_tools` | Python scripts (`format_recipes.py`, `recipe_stats.py`) for content normalisation |
| `assets` | Images, CSS, JS resources |
| `categories`, `ingredients` | Auxiliary collections used for navigation |
| `Gemfile`, `Gemfile.lock` | Ruby dependencies |
| `package.json`, `package-lock.json` | Node dependencies (Wrangler, Octokit) |
| `wrangler.toml` | Cloudflare Pages deployment configuration |
| `site.webmanifest`, `favicon*` | Web‑app assets |
| `AGENTS.md` | This documentation file |
| `.continue` | Continue CLI configuration, including custom slash commands |

## Development Workflow
- **Setup**
  1. Install Ruby ≥ 2.7 and Bundler.
  2. Run `bundle install` to fetch Jekyll and plugins.
  3. Install Node.js ≥ 18 and run `npm install` to get Wrangler.
- **Local build / preview**
  - `bundle exec jekyll serve` – serves `http://localhost:4000`.
- **Content preprocessing (recommended)**
  - Run `python _tools/format_recipes.py <markdown‑files>` after editing markdown to normalise tables, fractions, and temperatures.
- **Testing**
  - Verify the local preview renders all pages correctly.
  - Use the formatter to spot any remaining formatting issues.
- **Deployment**
  - On pushes to `main`, GitHub actions automatically build and publish via Wrangler.
  - For manual deploy: `wrangler publish` after `bundle exec jekyll build`.
- **Lint / format**
  - Ruby: Jekyll build outputs warnings for missing front‑matter or invalid YAML.
  - Python: No linting currently, but run the formatter to keep the files tidy.
  - Node: Ensure `wrangler` is up‑to‑date (`^4.33.1`).

## Additional Notes
- The site uses Cloudflare Turnstile for form protection; keys are stored in `_config.yml` and `wrangler.toml` and could be moved to environment variables.
- The repository excludes generated files (`_site`, `node_modules`, `.recipe_stats`, `.continue`, etc.) via `.gitignore`.
- Custom slash commands are located under `.continue/rules` and can be executed in the terminal with `/review`.
