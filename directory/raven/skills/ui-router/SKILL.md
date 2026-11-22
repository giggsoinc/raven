---
name: ui-router
description: "Thin UI/UX and frontend router. Detects framework (React, Vue, Angular, JavaScript) and design intent. Routes to the right specialist. Design default is v0.dev or AI canvas tool — Figma ONLY when user explicitly says \"figma\"."
---
# UI Router — Thin Layer v1.0

Detect framework and design intent. Load one specialist.

---

## DETECTION

| Message contains... | Specialist |
|---|---|
| `react` `jsx` `tsx` `next.js` `nextjs` `remix` `react native` `expo` | **[REACT]** |
| `vue` `nuxt` `pinia` `vuex` `composition api` `vue router` | **[VUE]** |
| `angular` `rxjs` `ngrx` `ng ` `angular cli` `standalone component` | **[ANGULAR]** |
| `vanilla js` `plain javascript` `no framework` `dom` `web components` `es modules` | **[JAVASCRIPT]** |
| `design` `wireframe` `mockup` `layout` `ux` `prototype` `design system` `tokens` | **[DESIGN]** |
| `figma` (explicit word only) | **[DESIGN]** with Figma allowed |

Framework + design mentioned together → lead with framework, surface design for visual work. Ambiguous → ask: "Building UI components or designing visuals?"

---

## ⚠️ DESIGN TOOL RULE — NON-NEGOTIABLE

```
DEFAULT:  v0.dev  OR  AI canvas / whiteboard tool of choice
FIGMA:    ONLY when user's message contains the literal word "figma"
NEVER:    Suggest Figma for general design, wireframe, layout, or component requests
```

---

## [REACT]

Expert: React — hooks-first, performance-aware, Next.js App Router, ecosystem.

**Gotchas:**
- Stale closures in `useEffect` — include all dependencies or use `useRef` for stable refs
- `key` prop must be stable and unique — index as key = bugs on reorder
- RSC can't use hooks or browser APIs — check the `use client` boundary
- Hydration mismatch — server/client render must match on first paint
- `useMemo`/`useCallback` — profile first, don't pre-optimize

**Stack defaults:** Zustand for state · TanStack Query for data fetching · React Hook Form + Zod · Tailwind CSS · Vitest + RTL

Opening: "Next.js App Router, Vite SPA, or React Native? What are you building?"

---

## [VUE]

Expert: Vue 3 — Composition API, Nuxt 3, Pinia, VueUse.

**Gotchas:**
- `reactive()` loses reactivity when destructured — use `toRefs()` or stick to `ref()`
- `v-for` + `v-if` on same element — `v-if` takes priority in Vue 3 (changed from Vue 2)
- Nuxt auto-imports can hide dependencies — use explicit imports in libraries/plugins
- `defineProps` with TypeScript defaults needs `withDefaults()` wrapper

**Key patterns:** `ref` for primitives · `reactive` for objects · `computed()` · Pinia: direct state mutation in actions is fine · `useFetch`/`useAsyncData` for SSR-aware data in Nuxt

Opening: "Vue 3 SPA or Nuxt 3? Composition API (`<script setup>`) or Options API?"

---

## [ANGULAR]

Expert: Angular — standalone components, signals, RxJS, enterprise-scale patterns.

**Gotchas:**
- Memory leaks from unsubscribed Observables — use `takeUntilDestroyed()`, `async` pipe, or `DestroyRef`
- Zone.js overhead — `OnPush` + signals removes most of it; signals are zone-free
- `ngOnInit` vs constructor — constructor for DI only, `ngOnInit` for initialization logic
- AOT compilation catches template errors at build time — don't ignore template type checking

**Key patterns:** `inject()` in standalone · Signals (`signal()`, `computed()`, `effect()`) for local state · Reactive Forms over Template-driven for complex forms

Opening: "Angular version? Standalone or NgModule? New feature or existing codebase?"

---

## [JAVASCRIPT]

Expert: Vanilla JS — browser APIs, ES modules, Web Components, framework-free patterns.

**Gotchas:**
- Event listener leaks — always `removeEventListener` or use `AbortController` signal
- `this` in callbacks — arrow functions or `.bind(this)` explicitly
- Never use `var` — always `const`/`let`
- Synchronous `localStorage` blocks main thread on large reads — use IndexedDB for > 5KB

**Key patterns:** Event delegation over per-element listeners · `Promise.all()` / `Promise.allSettled()` for parallel async · Web Workers for CPU-heavy work · `requestAnimationFrame` for animations

Opening: "Bundler (Vite/Webpack) or truly bundler-free? Target browser or Node?"

---

## [DESIGN]

Expert: UI/UX — wireframes, component specs, design tokens, layout guidance.

**Tool selection (enforces the rule above):**
- `v0.dev` → component generation, React/Next.js first, AI-driven
- AI canvas / whiteboard → rapid multi-screen flows and wireframes
- `Figma` → only if user said the word "figma"

**Workflow:** Clarify user goal → produce layout/mockup → output design tokens + component spec + a11y notes → dev handoff with CSS/Tailwind if needed

**Gotchas:**
- Mobile-first always — desktop is progressive enhancement
- Never use color alone to convey meaning — pair with icon or text
- Real content beats lorem ipsum — ask for actual copy before finalizing layouts
- Ask about existing design system / brand tokens before starting

Opening: "Single component, page layout, or multi-screen flow?"

---

## Cross-UI Rules

- **Accessibility:** Flag any pattern that breaks keyboard nav or screen reader flow
- **Performance:** Flag render-blocking patterns, unoptimized images, layout shift causes
- **Secrets:** API keys never in client-side code — env vars at build time or server-side proxy
- **Framework migration:** Map concepts explicitly (e.g., Vue `ref` ≈ React `useState`)
- **Design + dev handoff:** Design first → spec → implement — never skip the spec step
