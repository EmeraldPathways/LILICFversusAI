# Frontend UI Refinement Prompt: H&M 3-Agent Recommendation Artefact

## 0. Pre-Flight Safety & Research Protocol (MANDATORY — DO NOT SKIP)

> ⚠️ **CRITICAL**: You are ONLY permitted to modify frontend presentation-layer files. You must NOT change any backend API calls, data mapping logic, TypeScript types, or response handling. The goal is a pure visual/CSS/layout refactor.

### Step 0.1 — Clone and Inspect
```bash
git clone https://github.com/EmeraldPathways/LILICFversusAI.git
cd LILICFversusAI
git checkout artifacts
```

### Step 0.2 — Create Safety Branch
```bash
git checkout -b ui-refinement/artifact-demo-frontend-only
```

### Step 0.3 — Read-Only Analysis (perform before any edits)
Read these files in this exact order and take notes:
1. `frontend/app/globals.css` — Note ALL CSS custom properties and class names prefixed with `.artifact-`
2. `frontend/components/ArtifactDemoTabs.tsx` — Note the component structure, state hooks, and data flow. DO NOT change the data flow.
3. `frontend/app/layout.tsx` — Note the metadata and font imports.
4. `frontend/app/artifact-demo/page.tsx` — Note the server component data fetch.
5. `frontend/components/AppFrame.tsx` — Note the route conditional rendering.
6. `frontend/lib/api.ts` — Read but DO NOT MODIFY. Understand the data contracts for `ArtifactDemoWorkflowCase`, `ArtifactDemoMethodItem`, etc.
7. `3agentui.md` — Read the original UI specification.

### Step 0.4 — Backup Originals
Before touching any file, create `.bak` copies:
```bash
cp frontend/components/ArtifactDemoTabs.tsx frontend/components/ArtifactDemoTabs.tsx.bak
cp frontend/app/globals.css frontend/app/globals.css.bak
cp frontend/app/layout.tsx frontend/app/layout.tsx.bak
```

---

## 1. Project Context

This is a Next.js 15 (App Router) + React 19 academic demo. The `artifact-demo` route (`/artifact-demo`) displays a three-tab interface:
- **SVD** — Baseline collaborative filtering recommendations
- **3-Agent** — Preference → Evidence → Decision agent workflow
- **Hybrid** — Combined SVD + 3-Agent with explainability audit

The current implementation (the "bad" UI) is functional but visually inconsistent. The target design (the "good" UI) is a polished dark-theme interface with:
- A hero section with 3-agent stage explainer cards
- Clean user selection controls
- Horizontal bar charts for preference profiles
- Product image placeholder cards for evidence
- Prominent match-score badges for recommendations
- Consistent dark slate background with cyan/teal accents

**Stack**: No Tailwind, no shadcn, no MUI. Pure CSS via `globals.css` + inline `className` strings. No additional npm packages may be installed.

---

## 2. Visual Reference Mapping

Use the four provided screenshots as your north star:

| Screenshot | Content | Status |
|---|---|---|
| `3agents good.png` | **TARGET DESIGN** — Full 3-Agent flow (hero, preference, evidence, decision) | This is what the 3-Agent tab MUST look like |
| `3agents bad 2.png` | Current SVD tab | Restyle to match the target card language |
| `3agentsbad.png` | Current 3-Agent tab | Major overhaul needed |
| `3agentsbad3.png` | Current Hybrid tab | Restyle to match target card language |

### 2.1 Global Design Tokens (from the "good" reference)

Apply these tokens to ALL three tabs and the entire artifact route:

| Token | Value | Usage |
|---|---|---|
| Background | `#0a0e17` (very dark slate) | Page background |
| Card Background | `rgba(13, 20, 32, 0.85)` | All panels/cards |
| Card Border | `1px solid rgba(124, 154, 185, 0.15)` | Card outlines |
| Primary Text | `#e8f0f8` | Headings, labels |
| Muted Text | `#8a9bb0` | Descriptions, secondary info |
| Accent Cyan | `#4ecdc4` / `#7dd3c0` | Active tabs, badges, highlights |
| Accent Blue | `#56b7ff` | Score pills, selected states |
| Accent Warm | `#f2b880` | Eyebrow labels, warnings |
| Accent Purple | `#a78bfa` | Match score badges (Decision Agent) |
| Font Family | `Inter, system-ui, -apple-system, sans-serif` | All text (NO serif) |
| Border Radius | `16px` for cards, `999px` for pills/buttons/tabs | Consistent rounding |
| Shadow | `0 18px 50px rgba(0,0,0,0.35)` | Card elevation |
| Grid Gap | `18px` standard, `14px` compact | Between cards |
| Padding | `18px` inside cards, `16px` page gutters | Internal spacing |

---

## 3. Step-by-Step Implementation Guide

### PHASE A: Global Styles (`frontend/app/globals.css` + `frontend/app/layout.tsx`)

**Step A.1 — Update `layout.tsx` fonts**
- Add Google Font `Inter` import or use `next/font/google`.
- Apply `Inter` to the `<body>` element.
- Keep the existing `AppFrame` wrapper and metadata.
- **Safety check**: Do NOT remove the `AppFrame` import or change the children prop type.

**Step A.2 — Clean `globals.css` for the artifact route**
The current CSS has a split personality: warm light-theme variables (`--bg`, `--card`, `--ink`) AND dark artifact variables (`--artifact-*`). The artifact route must be 100% dark.

Actions:
1. Keep the `.artifact-route-shell` and `.artifact-route-container` shell classes but update their background to the dark slate gradient.
2. Remove or override any light-theme leakage into the artifact route (e.g., warm beige backgrounds, serif fonts).
3. Ensure ALL `.artifact-*` classes use the dark tokens from Section 2.1.
4. Add utility classes for the new design patterns:
   - `.artifact-bar-chart` — for horizontal bar charts
   - `.artifact-product-card` — for evidence/recommendation cards with image placeholder
   - `.artifact-match-badge` — for the purple match-score badge
   - `.artifact-stage-card` — for the 3-agent explainer cards
   - `.artifact-hero` — for the top hero section layout
5. **Preserve** all non-artifact classes (`.shell`, `.container`, `.hero`, `.nav`, etc.) for the OTHER routes. Do not break the overview, research-setup, comparison, evaluation, or explainability pages.

**Step A.3 — Verify no build errors**
```bash
cd frontend
npm run build
```
If errors, fix CSS syntax only. Do not change JS/TS logic.

---

### PHASE B: `ArtifactDemoTabs.tsx` — Component Structure Refactor

> ⚠️ **CRITICAL CONSTRAINT**: You may restructure JSX, add wrapper `div`s, change `className` strings, and add helper render functions. You may NOT change:
> - State variable names (`selectedCase`, `activeTab`, `isLoadingCases`, etc.)
> - The `useEffect` data loading logic
> - The `tabs` array definition
> - The data transformation helpers (`compactValueCounts`, `formatBoolean`, etc.)
> - Any API calls or prop types

**Step B.1 — Add Hero Section (applies to ALL tabs)**

Above the tab content, add a persistent hero section that renders regardless of which tab is active:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ EYEBROW: "H&M-STYLE MOCK MULTI-AGENT RECOMMENDER"                          │
│ TITLE:   "3-Agent Fashion Recommendation Demo"                              │
│ SUBTITLE: "This demo keeps the logic intentionally transparent..."           │
│                                                                             │
│ ┌─────────────────────┐  ┌─────────────────────────────────────────────┐   │
│ │ Mock User           │  │ Selected user: Sofia Andersson              │   │
│ │ [U002 - Sofia ▼]    │  │ Leans toward dresses, soft tones...         │   │
│ │                     │  │                                             │   │
│ │ Current User Request│  │                                             │   │
│ │ [I only want...   ] │  │                                             │   │
│ │                     │  │ [Run 3-Agent Recommendation] ← cyan button  │   │
│ └─────────────────────┘  └─────────────────────────────────────────────┘   │
│                                                                             │
│ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐                            │
│ │ 1. Preference│ │ 2. Evidence │ │ 3. Decision │                            │
│ │ Agent        │ │ Agent       │ │ Agent       │                            │
│ │ Analyze...   │ │ Retrieve... │ │ Score...    │                            │
│ └─────────────┘ └─────────────┘ └─────────────┘                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

Implementation notes:
- Use the existing `selectedCase` data to populate the "Selected user" summary card.
- The user selector dropdown and request input are **visual-only** for this phase (they exist in the target design). Wire them to the existing `selectedCase` state. Do NOT add new state for the request text; use a static placeholder or the existing `inferred_intent`.
- The 3 stage cards are static explainer cards (not interactive). Use the descriptions from the current `3agentui.md` spec.
- Style: dark card background, subtle border, `1.` `2.` `3.` prefix in cyan.

**Step B.2 — Redesign the SVD Tab (`activeTab === "svd"`)**

Current state: basic description + signal panel + grid of rank cards.

Target state:
1. **Method Header Card**: "SVD BASELINE" eyebrow + "SVD Matrix Factorisation Baseline" title + description paragraph. Styled as a dark card with left border accent in cyan.
2. **User Selection Panel**: Reuse the same user selection panel pattern as the 3-Agent tab (compact grid of customer ID, training history, ground truth, candidate pool). Add "Ground truth in pool: Yes" and "SVD Hit at Top-10" badges.
3. **SVD Signal Panel**: Right-side summary card showing "SVD uses behavioural interaction patterns only..." + Ground Truth Article, Type, Group, Colour as key-value pills.
4. **Top-10 Recommendations Grid**: 4-column grid (responsive to 2-col on tablet, 1-col on mobile). Each card:
   - "RANK 1" label (muted, uppercase)
   - Article ID as title (bold)
   - "SVD SCORE" pill with value
   - 2×2 metadata grid: TYPE / GROUP / COLOUR / APPEARANCE
   - Clean borders, no excessive inner boxes

**Step B.3 — Redesign the 3-Agent Tab (`activeTab === "agentic"`)**

This is the most important tab. It must match the "good" screenshot as closely as possible.

**B.3.1 — Preference Agent Section**
- Header: "PREFERENCE AGENT" eyebrow (cyan, uppercase, small) + "User Preference Profile" title.
- Top-right badge: "Transactions Analysed: {count}" in a subtle pill.
- Summary paragraph: Use `selectedCase.preference_agent.inferred_intent`.
- Tag chips row: Map `preferred_product_types`, `preferred_colours`, etc. into small pill badges (e.g., "Often buys trouser items", "Spends most frequently in garment upper body"). If the data doesn't have these exact strings, generate descriptive chips from the available data.
- **Bar Chart Panels**: Four panels side-by-side (2×2 on smaller screens):
  - Preferred Product Types
  - Preferred Product Groups
  - Preferred Colours
  - Preferred Appearances

  Each panel:
  - Title (small, muted)
  - List of items with: label + percentage bar + percentage text
  - The bar is a horizontal div with a cyan fill and dark track.
  - Use `frequent_product_types`, `frequent_product_groups`, etc. from the API data. Calculate percentages from the `count` values.
  - If data is empty or "Not available", show a graceful empty state (centered text, muted color) instead of the raw "Not available" string.

**B.3.2 — Evidence Agent Section**
- Header: "EVIDENCE AGENT" eyebrow + "Candidate Evidence Set" title.
- Subtitle: "Retrieved {count} catalog candidates by matching soft preference signals against product metadata."
- **Product Card Grid**: 3-column grid of cards. Each card:
  - Top: Large gray image placeholder with "HM####" text centered (use `article_id` as the text).
  - Below image: Article ID + match count badge (e.g., "5 matches" in a small green/cyan pill).
  - Product name (bold) + one-line description.
  - Metadata tags: Group, Colour, Appearance as small pills.
  - Matched signals text: "Matched 5 preference signals: type:Trousers, group:Garment Lower body..."
  - Card background: dark, border subtle.

**B.3.3 — Decision Agent Section**
- Header: "DECISION AGENT" eyebrow + "Final Recommendations" title.
- Subtitle: "Ranked the evidence set with transparent weighted scoring and returned the top {N} items."
- **Recommendation Card Grid**: 2-column grid (responsive). Each card:
  - Top row: "Rank #1" (muted) + Match Score badge (purple background, white text, rounded, e.g., "0.467")
  - Product name + Article ID (e.g., "Coat · HM1015")
  - Metadata grid: Group / Colour / Appearance / Constraint Status
  - Score explanation paragraph
  - Signal tags at bottom (e.g., "type:Coat", "group:Garment Upper body")
  - Card background: dark with subtle left border accent.

**Step B.4 — Redesign the Hybrid Tab (`activeTab === "hybrid"`)**

Current state: dense flow diagram + signal panels + audit section.

Target state:
1. **End-to-End Path Header**: A horizontal flow diagram showing 5 layers (Evaluation Base → SVD Artifact → 3-Agent Artifact → Hybrid Formula → Hybrid Artifact) + Explainability Audit. Use the existing data but present it as clean connected cards with arrows.
2. **User Selection Panel**: Same compact grid pattern as SVD tab.
3. **Three Signal Columns**:
   - **SVD Behavioural Signal**: SVD rank, normalized score, ground truth status, product type/group tags.
   - **3-Agent Evidence Signal**: Normalized agentic score, product metadata tags, matched preference fields.
   - **Hybrid Formula**: Show the formula text in a code-like dark box + score breakdown pills.
4. **Hybrid Top-10 Recommendations**: Same card pattern as Decision Agent, but each card shows:
   - Hybrid Score (prominent)
   - SVD Score (secondary)
   - Agentic Score (secondary)
   - Diversity Bonus (secondary)
   - Ground Truth badge (if applicable)
5. **Explainability Audit**: Clean 2-column grid of key-value pills (Selected Article, Groundedness, Hybrid Rank, SVD Rank, Rank Shift, Hit Status, Preference Trace, Product Name). Then the explanation text paragraph below.

**Step B.5 — Responsive Behavior**
- Desktop (1200px+): Full multi-column grids as described.
- Tablet (860px): 2-column grids, hero stacks vertically.
- Mobile (<700px): Single column, full-width cards, hero stacks fully.
- Ensure text never overflows; use `word-break: break-word` where needed.

---

### PHASE C: `AppFrame.tsx` — Artifact Route Wrapper

The artifact route currently uses `artifact-route-shell` and `artifact-route-container`. Ensure:
1. The dark background is applied correctly.
2. No `TopNav` is rendered inside the artifact route (the current code already does this — preserve it).
3. The shell has no extra padding that conflicts with the new hero design.

---

## 4. Safety Checklist (Verify Before Committing)

For EVERY file you modify, run through this checklist:

- [ ] **No functional changes**: All API calls, data transformations, and state logic remain identical.
- [ ] **No type changes**: No modifications to `frontend/lib/api.ts` or any TypeScript interfaces.
- [ ] **No new dependencies**: Do not run `npm install`. Use only existing CSS and React.
- [ ] **No broken routes**: Verify `/research-setup`, `/comparison`, `/evaluation`, etc. still render correctly (they should be unaffected since you only changed `.artifact-*` classes and `ArtifactDemoTabs.tsx`).
- [ ] **Build passes**: `npm run build` exits with 0 errors.
- [ ] **No `.bak` files committed**: Remove `.bak` files before final commit, or add them to `.gitignore`.
- [ ] **Git diff review**: Run `git diff` and confirm every change is either CSS or JSX `className`/structure. No logic changes.

---

## 5. Acceptance Criteria

The agent must verify the following before declaring completion:

1. **SVD Tab** visually matches the layout density and card style of `3agents bad 2.png` but with the polished dark theme, clean typography, and consistent spacing of the target design.
2. **3-Agent Tab** visually matches `3agents good.png`:
   - Hero with eyebrow, title, user selector, request input, cyan CTA button, and 3 stage cards.
   - Preference section has horizontal bar charts for the four preference dimensions.
   - Evidence section has image-placeholder product cards with match counts and metadata.
   - Decision section has prominent match-score badges and clean recommendation cards.
3. **Hybrid Tab** visually matches the density and structure of `3agentsbad3.png` but with the polished card language, spacing, and typography of the target design.
4. **All three tabs** share the same dark background, font family, border radius, shadow, and accent color system.
5. **No console errors** in the browser DevTools.
6. **No 404s** or failed API calls.
7. **Mobile layout** is readable and cards stack correctly.

---

## 6. File Inventory (What You May Touch)

| File | Permission | Notes |
|---|---|---|
| `frontend/components/ArtifactDemoTabs.tsx` | ✅ MODIFY | Restructure JSX, update classNames, add helper render functions. Preserve all hooks and data logic. |
| `frontend/app/globals.css` | ✅ MODIFY | Update `.artifact-*` classes, add new utility classes. Preserve non-artifact classes. |
| `frontend/app/layout.tsx` | ✅ MODIFY | Add Inter font import only. |
| `frontend/app/artifact-demo/page.tsx` | ❌ DO NOT MODIFY | Server component; no visual logic. |
| `frontend/components/AppFrame.tsx` | ⚠️ MINIMAL | Only adjust artifact route wrapper styles if needed. |
| `frontend/lib/api.ts` | ❌ DO NOT MODIFY | Data contracts must remain unchanged. |
| `frontend/components/TopNav.tsx` | ❌ DO NOT MODIFY | Used by other routes. |
| Any backend file | ❌ DO NOT MODIFY | Out of scope. |

---

## 7. Deliverables

When complete, provide:
1. A summary of every file modified and what changed.
2. A `git diff --stat` output showing the scope of changes.
3. Confirmation that `npm run build` passes.
4. Confirmation that the other routes (`/`, `/research-setup`, `/comparison`, `/evaluation`, `/explainability-evidence`) are visually unaffected.
5. Any notes on data-driven limitations (e.g., "Bar charts use frequent_product_types which may be empty for some users — graceful empty state shown").
