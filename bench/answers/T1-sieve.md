Maximum steps for this agent have been reached; tools are disabled.

From the provided context, a GitHub repository becomes a work item in the dashboard queue through this chain:

1. The dashboard fetches GitHub repository data via `src/app/api/github/dashboard/route.ts` (summarized as the API route that produces repository/branch/pull-request shapes).

2. `src/hooks/use-activity.ts` → `useActivity` loads/updates `RepositoryResult[]` and stores the user’s selected repository IDs in `localStorage` using `readIds`/`writeIds` (key `agent-activity-repositories-v2`). It passes the results into the view layer.

3. `src/app/page.tsx` → `Home` calls `buildWorkItems(activity.results)` and `summarize(workItems)` from `src/lib/activity-model.ts`, then renders `QueueView` with the resulting items.

4. `src/lib/activity-model.ts` → `buildWorkItems(results: RepositoryResult[]): WorkItem[]` is the key transformation:
   - It iterates each `RepositoryResult`.
   - Skips results with no `repository`.
   - Maps pull requests by branch.
   - For each branch in `repo.branches`, calls `makeWorkItem(repo, branch, pull)`.
   - `makeWorkItem` builds a `WorkItem` with attention state from `inferAttention(pull)`, plus fields for needsYou/blocked/lines/files/updatedAt.
   - It also adds work items for orphaned PRs that have no matching local branch.

5. `src/lib/activity-model.ts` → `inferAttention(pull)` decides the attention state: `draft`, `checks-failing`, `agent-revising`, `approved`, `in-review`, `your-review`, `no-pull-request`, or `unknown`.

6. `src/components/queue-view.tsx` → `QueueView` receives the `WorkItem[]`, calls `partitionWorkItems(items)`, and renders each through `src/components/work-item.tsx` → `WorkItem`.

So the exact path is:

- `src/app/api/github/dashboard/route.ts` (server-side GitHub fetch)
- `src/hooks/use-activity.ts` → `useActivity`
- `src/app/page.tsx` → `Home` → `buildWorkItems`
- `src/lib/activity-model.ts` → `buildWorkItems`, `makeWorkItem`, `inferAttention`
- `src/components/queue-view.tsx` → `QueueView` → `partitionWorkItems`
- `src/components/work-item.tsx` → `WorkItem`

What the provided context is missing:
- Full body of `src/app/api/github/dashboard/route.ts` (only a summary is shown; the actual fetch/query logic is cut off).
- Full body of `src/hooks/use-activity.ts` after `writeSeen` (sync/fetch logic is truncated).
- Full body of `src/lib/activity-model.ts` after the start of `buildWorkItems` (the rest of the function and helper internals are truncated).
- Any backend persistence or queue-state storage beyond localStorage; it appears the “queue” is purely derived from live GitHub data plus local selection/seen state.

Recommended next step: inspect the full contents of `src/app/api/github/dashboard/route.ts`, `src/hooks/use-activity.ts`, and `src/lib/activity-model.ts` to confirm the complete data flow and any additional filtering/sorting rules.