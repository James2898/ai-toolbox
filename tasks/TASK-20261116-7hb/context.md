## Context Bundle

### Relevant Files
| File | Why It's Relevant |
|------|------------------|
| `tools/build_site.py` | Compiles site pages (`docs/index.html`, `docs/changelog.html`, and will generate `docs/skills/<name>.html`), manages template substitution, JSON data, and deterministic `--check` validation. |
| `tools/site/template.html` | Defines the master design tokens, CSS styling, header, navigation, and client-side card rendering for the catalog index. |
| `tools/site/DESIGN.md` | Single source of truth for color palette, typography (Space Grotesk, Source Serif 4, Inter), elevation, 48rem reading container width, and component rules. |
| `tools/site_categories.yml` | Maps 42 skills into 9 categories; used for category filtering on index and breadcrumbs on skill detail pages. |
| `tools/site/changelog.html` | Reference template showing how secondary pages extract and reuse `/*STYLE*/` from `template.html` without style drift. |
| `claude/skills/*/SKILL.md` | Source Markdown files containing frontmatter and markdown documentation bodies for all 42 skills. |
| `docs/index.html` | Committed output catalog; must be updated deterministically alongside new skill pages. |

### Reuse Candidates
- `tools/build_site.py` (`frontmatter`, `read_skills`, `read_categories`, `as_json`, `render`) — Reuse frontmatter parsing, category mapping, skill reading (retaining `_body` for detail pages), and template style extraction logic.
- `tools/site/template.html` (`:root` CSS variables and badge classes) — Reuse `--canvas`, `--surface`, `--primary`, `--gold`, `--crimson`, `--serif`, `--display`, `--sans`, `--mono`, plus `.badge`, `.badge.user`, `.badge.ro`, `.badge.gold` directly.
- `tools/site/changelog.html` (`/*STYLE*/` injection pattern) — Direct blueprint for `tools/site/skill_template.html`: inject `style.group(1)` extracted from `template.html`, ensuring 100% style consistency with zero duplication.
- Python Standard Library (`re`, `html`, `pathlib`) — Lean change ladder: no external dependencies required for markdown parsing. Standard library handles regex parsing, HTML entity escaping, and file I/O within `python3 -I` sandbox.

### Patterns to Follow
- Single Source of Truth for Styles: See `tools/build_site.py` lines 346-349 & `tools/site/changelog.html` line 13 — Extract `<style>` from `template.html` and inject via `/*STYLE*/` token into secondary templates so styles never drift.
- Deterministic Build & Zero-Timestamp Output: See `tools/build_site.py` lines 10-13, 365-373 — Generated static files contain no timestamps, dates, or machine paths, ensuring `python3 -I tools/build_site.py --check` stays byte-for-byte stable.
- Reading Width Layout Constraint (48rem): See `tools/site/DESIGN.md` line 219 and `tools/site/template.html` line 130 (`.wf-panel { max-width: 48rem; }`) — For reading views (like skill detail pages), cap container width at `48rem` (768px).
- Stretched Link & Elevation Rules: See `tools/site/DESIGN.md` line 191 (flat tonal layering, L1 surface with 1px border, no drop shadows) and CSS stretched-link pattern (`.stretched-link::after { content: ''; position: absolute; inset: 0; }` on `.card { position: relative; }`) with `transform: translateY(-2px); border-color: var(--primary);` on hover.
- Category-Aware Breadcrumbs: See `tools/site_categories.yml` — Invert category mapping to render `Catalog > {Category} > /ai-toolbox:{skill_name}` breadcrumbs.

### Anti-Patterns Flagged
- External Markdown Library Dependency: Do NOT add `markdown`, `mistune`, or `commonmark` dependencies. `tools/build_site.py` runs with `python3 -I` (isolated environment) and must remain dependency-free using standard library only.
- Inconsistent Card Borders/Shadows: `tools/site/DESIGN.md` explicitly forbids box shadows on cards and pill shapes; avoid adding generic CSS box-shadows or border-radius pills for hover effects or badges.
- Modifying Generated Files Directly: `docs/index.html` and `docs/skills/*.html` are build artifacts. Do not edit `docs/` directly; modify `tools/site/template.html`, `tools/site/skill_template.html`, and `tools/build_site.py`.

### MEMORY.md Notes
- N/A (MEMORY.md does not exist in repository).
