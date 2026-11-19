A GitHub repository becomes a dashboard queue work item through this pipeline, using only the code in the attached context:

1. **Selection and fetch**
   - `src/hooks/use-activity.ts` → `useActivity()` → `commitSelection(ids)` saves the chosen repository IDs and triggers `fetchDashboard(ids, repoList, false)`.
   - `fetchDashboard` builds the query string and calls `GET /api/github/dashboard?repo=owner/name`.

2. **Server-side GitHub load**
   - `src/app/api/github/dashboard/route.ts` → `GET(request)` validates the repo names, then calls `loadRepository(fullName)` for each.
   - `loadRepository` fetches repository metadata, branches, open pull requests, checks, reviews, deployments, and local state, returning a `DashboardRepository` embedded in a `RepositoryResult`.

3. **Transform into work items**
   - `src/app/page.tsx` calls `buildWorkItems(activity.results)` from `src/lib/activity-model.ts`.
   - `src/lib/activity-model.ts` → `buildWorkItems(results)` iterates each `RepositoryResult`, joins branches to their pull requests by branch name, and calls `makeWorkItem(repo, branch, pull)`.
   - `makeWorkItem` uses `inferAttention(pull)` to decide the attention state (`your-review`, `approved`, `checks-failing`, `draft`, etc.) and whether it `needsYou`.
   - `buildWorkItems` then calls `sortWorkItems(items)` to order waiting/blocked/larger changes first.

4. **Render in queue**
   - `src/app/page.tsx` passes `workItems` to `<QueueView items={workItems} ... />` in `src/components/queue-view.tsx`.
   - `QueueView` calls `partitionWorkItems(items)` (also in `src/lib/activity-model.ts`) to split into “Waiting on you” and “In flight”, then renders each as a `<WorkItem>` in `src/components/work-item.tsx`.

Key functions and files:
- `src/hooks/use-activity.ts` — `useActivity`, `commitSelection`, `fetchDashboard`
- `src/app/api/github/dashboard/route.ts` — `GET`, `loadRepository`
- `src/lib/activity-model.ts` — `buildWorkItems`, `makeWorkItem`, `inferAttention`, `sortWorkItems`, `partitionWorkItems`
- `src/app/page.tsx` — `workItems = useMemo(() => buildWorkItems(activity.results), ...)`
- `src/components/queue-view.tsx` — `QueueView`
- `src/components/work-item.tsx` — `WorkItem`

No context is missing for the repository-to-work-item flow; all steps are present in the attached files.