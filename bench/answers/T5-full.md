The queue is split and rendered client-side like this:

**Build the queue**
- `src/app/page.tsx` calls `buildWorkItems(activity.results)` and `summarize(workItems)` from `src/lib/activity-model.ts`, then passes `items`, `summary`, and `changedItems` to `QueueView`.

**Split into sections**
- `src/components/queue-view.tsx` (`QueueView`) calls `partitionWorkItems(items)` from `src/lib/activity-model.ts`.
- `partitionWorkItems` returns two arrays:
  - `waiting`: `items.filter((item) => item.needsYou)`
  - `inFlight`: `items.filter((item) => !item.needsYou)`
- `QueueView` renders each group under separate `<section>` headings — “Waiting on you” and “In flight” — with counts.

**Render each work item**
- Each item is rendered by `src/components/work-item.tsx` (`WorkItem`).
- It receives `item` and a `changed` boolean (from `changedItemSet`, built from `changedItems` in `QueueView`).
- `WorkItem` shows:
  - a colored dot driven by `statusTone(item.attention)`
  - repo name, branch name, title (pull title → first commit message → PR fallback)
  - status text from `statusLabel`
  - “Changed” badge, lines/files, age, and a diff-width bar
  - an action link to GitHub and a details toggle that expands commits and review facts

Files/functions involved:
- `src/app/page.tsx` — `Home`
- `src/components/queue-view.tsx` — `QueueView`
- `src/components/work-item.tsx` — `WorkItem`
- `src/lib/activity-model.ts` — `buildWorkItems`, `summarize`, `partitionWorkItems`, `sortWorkItems`, `inferAttention`

Nothing required for this question appears missing from the attached context.

I skipped unrelated views like `RepoList` and `RepoHistory`, and server-side fetching in `/api/github/dashboard`, since they don’t change how the queue is split or how a work item renders.