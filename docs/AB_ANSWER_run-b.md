GitHub dashboard data becomes queue work items through this path:

1. **Fetch and combine data** ΓÇö `src/hooks/use-activity.ts` `useActivity()`  
   - Reads selected repository ids from `localStorage`, fetches each repo from `/api/github/dashboard`, and stores the combined `RepositoryResult[]` in `activity.results`.

2. **Build dashboard objects** ΓÇö `src/app/api/github/dashboard/route.ts` `GET()` and `loadRepository()`  
   - Calls the GitHub API and local state, returning `RepositoryResult` objects that contain a `DashboardRepository` (branches, pull requests, deployment) plus optional `local` / `localError`.

3. **Turn repositories into work items** ΓÇö `src/lib/activity-model.ts` `buildWorkItems()`  
   - Iterates every `RepositoryResult`.
   - Maps pull requests by branch, then calls `makeWorkItem(repo, branch, pull)` for each branch.

4. **Compute attention state** ΓÇö `src/lib/activity-model.ts` `inferAttention()` and `makeWorkItem()`  
   - `inferAttention()` derives `AttentionState` from the PRΓÇÖs draft/review/check state.
   - `makeWorkItem()` sets `needsYou`, `blocked`, `lines`, `files`, and `updatedAt`.

5. **Render the queue** ΓÇö `src/app/page.tsx` `Home()` and `src/components/queue-view.tsx` `QueueView()`  
   - `Home()` calls `buildWorkItems(activity.results)` and `summarize(workItems)`.
   - `QueueView()` calls `partitionWorkItems(items)` and renders `src/components/work-item.tsx` `WorkItem()` for each item.

Skipped / not checked: the full fetch/polling implementation inside `useActivity` is truncated in the context, and the GitHub API field mapping inside `loadRepository()` is only partially shown.  
Risk: if the dashboard route changes the shape of `DashboardRepository` or `PullRequest`, `inferAttention` and `makeWorkItem` may compute wrong attention states or miss branches.