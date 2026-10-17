---
name: Sanctuary Psalter (ai-toolbox catalog)
colors:
  surface: '#f9f9fc'
  surface-dim: '#dadadc'
  surface-bright: '#f9f9fc'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f3f6'
  surface-container: '#eeeef0'
  surface-container-high: '#e8e8ea'
  surface-container-highest: '#e2e2e5'
  on-surface: '#1a1c1e'
  on-surface-variant: '#434653'
  inverse-surface: '#2f3133'
  inverse-on-surface: '#f0f0f3'
  outline: '#737784'
  outline-variant: '#c3c6d5'
  surface-tint: '#215abd'
  primary: '#00357f'
  on-primary: '#ffffff'
  primary-container: '#004aad'
  on-primary-container: '#a9c1ff'
  inverse-primary: '#b0c6ff'
  secondary: '#735c00'
  on-secondary: '#ffffff'
  secondary-container: '#fed65b'
  on-secondary-container: '#745c00'
  tertiary: '#6e1628'
  on-tertiary: '#ffffff'
  tertiary-container: '#8d2e3d'
  on-tertiary-container: '#ffacb3'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d9e2ff'
  primary-fixed-dim: '#b0c6ff'
  on-primary-fixed: '#001945'
  on-primary-fixed-variant: '#00429b'
  secondary-fixed: '#ffe088'
  secondary-fixed-dim: '#e9c349'
  on-secondary-fixed: '#241a00'
  on-secondary-fixed-variant: '#574500'
  tertiary-fixed: '#ffdadb'
  tertiary-fixed-dim: '#ffb2b8'
  on-tertiary-fixed: '#40000f'
  on-tertiary-fixed-variant: '#812535'
  background: '#f9f9fc'
  on-background: '#1a1c1e'
  surface-variant: '#e2e2e5'
typography:
  display-lg:
    fontFamily: Space Grotesk
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: 0.02em
  display-lg-mobile:
    fontFamily: Space Grotesk
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: 0.01em
  headline-number:
    fontFamily: Space Grotesk
    fontSize: 22px
    fontWeight: '700'
    lineHeight: 28px
    letterSpacing: 0.05em
  headline-title:
    fontFamily: Space Grotesk
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: 0.01em
  headline-title-mobile:
    fontFamily: Space Grotesk
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: 0.01em
  subheading-meta:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
    letterSpacing: 0.08em
  body-reading:
    fontFamily: Source Serif 4
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
  label-badge:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '700'
    lineHeight: 14px
    letterSpacing: 0.06em
  label-ui:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
  caption-meta:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1rem
  gutter-tablet: 1.5rem
  margin: 1rem
  margin-tablet: 2rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.25rem
  space-2xl: 3.5rem
---

# Catalog site design

The visual system for `docs/index.html`. `tools/site/template.html` implements it; the
CSS custom properties at the top of the template are the tokens below. Change a token here
and in the template together.

Source: the "Sanctuary Psalter" design system (a bilingual hymnal app), adapted for a tool
catalog. The hymn-specific parts (stanzas, refrains, language canvases, audio player) are
dropped; the palette, type pairing, shape scale and flat layering are kept.

## Brand & style

A printed reference book rather than a dashboard: warm paper canvas, flat bordered cards,
gold hairline rules, royal-blue anchors. No drop shadows on content, no gradients.

## Colors

**Light only.** The page always uses the light palette below, whatever the viewer's system
theme; the source system's dark mode (Vespers / Compline) is not used.

| Role | Value | Used for |
|---|---|---|
| Canvas (L0) | `#FBF9F5` | page background |
| Surface (L1) | `#FFFFFF` | cards, panels, tables, inputs |
| Subtle tint | `#F5EFE6` | table headers, inactive chips, PM steps in the diagram |
| Border | `#E6DFD5` | card and panel borders |
| Hairline rule | `#EAE3D9` | table row rules |
| Input border | `#D1C7B7` | search field (focus: primary) |
| Outline | `#737784` | dashed border of conditional steps |
| Primary (royal blue) | `#004AAD` | title, command names, active category, links, counts |
| Secondary (gold / brass) | `#D4AF37` rules, `#735C00` text | header double rule, active tab underline, copy buttons, version tag, "has extras" badges, diagram arrows |
| Tertiary (crimson) | `#6B1426` on `#FFDADB` | the *User-only* badge and the fix-loop rule (rubrics: instructions about how things run) |
| Foreground | `#1B1D1F` | body text |
| Muted | `#434653` | leads, captions, counts |
| Code block | `#2F3133` / `#F0F0F3` | install commands, diagram start and end markers |

Gold `#D4AF37` is used only for rules and borders: as text on the canvas it does not reach
4.5:1, so gold text uses `#735C00`.

## Typography

- **Space Grotesk** — display and headings: page title (`display-lg`, mobile
  `display-lg-mobile`), section headings (`headline-title`), stat numbers
  (`headline-number`), command names on cards.
- **Source Serif 4** — reading text: skill, agent and rule descriptions, section leads
  (`body-reading`, 16/26).
- **Inter** — interface and metadata: tabs, buttons, sidebar, badges (`label-badge`,
  uppercase), category titles and table headers (`subheading-meta`, uppercase, 0.08em),
  captions (`caption-meta`).
- Monospace (system stack) for commands, paths and profile keys.

## Layout & spacing

- Mobile (< 640px): one column, `1rem` side margin; the sidebar becomes a wrap of chips
  above the list.
- Tablet (640–1024px): `1.5rem` margin; sidebar stacks above the content below 820px.
- Desktop (> 1024px): centred container up to 1180px, 230px sidebar plus card grid. (The
  source system caps reading width at 768px; the catalog is an index, not a reading view,
  so it keeps the wider grid and caps description text by the card width instead.)
- Section spacing `space-2xl`; card gap `space-sm`–`space-md`.

## Elevation

Flat tonal layering only: L0 canvas, L1 white surfaces with a 1px border. No shadows on
cards. The only shadow is the L2 overlay value `0 8px 24px -4px rgba(0, 74, 173, 0.12)`,
reserved for floating elements (none on the page today).

## Shapes

- Badges, tags, buttons, inputs: `rounded` (4px).
- Cards, panels, tables, code blocks: `rounded-lg` (8px).
- No pill shapes.

## Components

- **Header** — title in primary, version tag (gold border, gold text), tagline in Source
  Serif, closed by a 3px double gold rule.
- **Stats** — L1 cards, number in `headline-number` primary, label in uppercase caption.
- **Install panel** — L1 panel; tabs in `label-ui`, active tab with a 2px gold underline;
  commands in a code block with an outlined gold *Copy* button (secondary action).
- **Sidebar** — `subheading-meta` group labels; category buttons, active state filled
  primary with white bold text (the segmented-toggle active state).
- **Search** — 1px input border, primary border on focus, no shadow.
- **Skill / agent / rule cards** — L1, 8px; command name in Space Grotesk primary;
  description in Source Serif; badges: *User-only* crimson, *Read-only tools* primary
  outline, *Edits files* / *All tools* neutral outline, *Uses subagents* / *+ references/*
  gold.
- **Tables** (hooks, profile) — L1 with hairline rules, tinted header row in uppercase meta.
- **Orchestration diagram** — content from `tools/site/workflow.json`. Tier tabs are L1
  cards (tier number in `headline-number` primary, name in Space Grotesk, size in gold
  `label-badge`); the selected one gets a primary border. The flow is one vertical column,
  capped at 48rem (the source system's reading width): numbered nodes (step number in gold
  Space Grotesk), gold connector arrows, start and end markers in the code-block colours.
  Agent nodes are L1 and link to the agent's card; the PM's own steps use the subtle tint;
  conditional steps have a dashed `outline` border and a gold *Conditional* badge. Agents
  that run together sit in a gold-bordered tinted group labelled "In parallel". The fix loop
  uses the source system's refrain box: a 2px crimson left rule with italic serif text.
  Below 640px the parallel pairs stack.
