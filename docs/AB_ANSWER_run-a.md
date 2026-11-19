Maximum steps for this agent have been reached. No further tool calls can be made.

**Summary:** I can answer your question from the provided context.

## How GitHub dashboard data becomes work items

1. **Fetch dashboard data** ΓÇö `src/app/api/github/dashboard/route.ts`  
   `GET` ΓåÆ `loadRepository(fullName)` calls GitHub for repo metadata, branches, open PRs, checks, reviews, deployments, and merges in local state via `readLocalState`.

2. **Return repository results** ΓÇö `loadRepository` returns a `DashboardRepository` shape; the route wraps it in `RepositoryResult` objects (`repository`, `local`, `localError`, `error`).

3. **Store results in the UI** ΓÇö `src/hooks/use-activity.ts`  
   `fetchDashboard()` calls `/api/github/dashboard` and stores the results in `resultsRef` / React state.

4. **Build work items** ΓÇö `src/app/page.tsx`  
   Uses `useMemo(() => buildWorkItems(activity.results), [activity.results])`.

5. **Transform into work items** ΓÇö `src/lib/activity-model.ts`  
   `buildWorkItems(results)`:
   - Iterates each `RepositoryResult`.
   - Maps PRs by branch name.
   - Creates a `WorkItem` for each branch (via `makeWorkItem`) and joins it with its PR.
   - Falls back to a synthetic branch for PRs with no matching branch row.
   - Filters out branches that are not ahead and have no PR.
   - Sorts via `sortWorkItems`.

6. **Infer attention state** ΓÇö `src/lib/activity-model.ts`  
   `inferAttention(pull)` decides whether the item is `your-review`, `approved`, `checks-failing`, `draft`, etc.

7. **Partition and render** ΓÇö `src/components/queue-view.tsx`  
   `partitionWorkItems(items)` splits into `waiting` and `inFlight`, then renders `<WorkItem>` components.

**Key files and functions:**
- `src/app/api/github/dashboard/route.ts` ΓÇö `GET`, `loadRepository`
- `src/hooks/use-activity.ts` ΓÇö `fetchDashboard`
- `src/app/page.tsx` ΓÇö `buildWorkItems(activity.results)`
- `src/lib/activity-model.ts` ΓÇö `buildWorkItems`, `makeWorkItem`, `inferAttention`, `sortWorkItems`, `partitionWorkItems`
- `src/components/queue-view.tsx` ΓÇö `partitionWorkItems`, `<WorkItem>`
- `src/components/work-item.tsx` ΓÇö renders individual work items

**Remaining tasks:** None ΓÇö this is a pure explanation request and the context contains the full pipeline.

**Recommendation:** If you want, I can next explain how attention state maps to queue sections, or how local-git state is folded into the dashboard response.