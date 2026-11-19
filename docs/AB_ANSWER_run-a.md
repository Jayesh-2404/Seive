Maximum steps for this agent have been reached, so I can only respond with text.

Flow from GitHub dashboard data to queue work items:

1. **Fetch dashboard data** — `src/app/api/github/dashboard/route.ts`
   - `GET` receives selected repos, calls `loadRepository(fullName)`.
   - `loadRepository` uses `githubFetch` to get branches, open PRs, reviews, check runs, deployments, and `readLocalState` for local clone state.
   - Returns an array of `RepositoryResult`.

2. **Load into the client** — `src/hooks/use-activity.ts`
   - `useActivity` → `fetchDashboard` calls `/api/github/dashboard?...` and stores `results` (`RepositoryResult[]`).

3. **Build work items** — `src/lib/activity-model.ts`
   - `src/app/page.tsx` passes `activity.results` into `buildWorkItems`.
   - `buildWorkItems` iterates each result, maps PRs by branch, creates a `WorkItem` per branch via `makeWorkItem`, and adds orphan PRs as synthetic branch items.
   - `makeWorkItem` calls `inferAttention` to classify attention state (`your-review`, `approved`, `checks-failing`, `draft`, etc.) and sets `needsYou`.
   - Items are sorted by `sortWorkItems`.

4. **Render the queue** — `src/components/queue-view.tsx`
   - Receives `items`, uses `partitionWorkItems` to split into “Waiting on you” and “In flight”.
   - Renders each item with `src/components/work-item.tsx`.

5. **Summary/counts** — `src/lib/activity-model.ts`
   - `summarize(workItems)` produces `QueueSummary`; `page.tsx` passes `summary.needsYou` to `AppShell` for the queue badge.

Skipped: I did not trace the auth/session refresh path or local-git branch detail logic.
Risk: This describes the happy path; any 401 from `githubFetch` forces sign-out via `useActivity`, and truncated repo data is only surfaced in the UI note, not reflected in counts.