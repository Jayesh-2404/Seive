GitHub dashboard data becomes queue work items through this file/function chain:

1. **`src/app/api/github/dashboard/route.ts`**
   - `GET()` receives selected repo IDs
   - `loadRepository()` calls `githubFetch()` (from `src/lib/github.ts`) for `/repos/{fullName}`, `/branches`, `/pulls`, and `/deployments`
   - Returns `RepositoryResult[]` containing `DashboardRepository` objects

2. **`src/hooks/use-activity.ts`**
   - `useActivity()` fetches the dashboard route, merges local git state, and exposes `activity.results: RepositoryResult[]`

3. **`src/app/page.tsx`**
   - `Home()` calls `buildWorkItems(activity.results)` and passes the result to `QueueView`

4. **`src/lib/activity-model.ts`**
   - `buildWorkItems(results)` iterates each repo, maps branches to open PRs, and calls `makeWorkItem()`
   - `makeWorkItem()` calls `repoRef()` and `inferAttention()` to compute attention state (`your-review`, `approved`, `checks-failing`, etc.)
   - `sortWorkItems()` orders the final `WorkItem[]`

5. **`src/components/queue-view.tsx`**
   - `QueueView()` calls `partitionWorkItems(items)` to split into `waiting`/`inFlight`
   - Renders `<WorkItem>` for each item

6. **`src/components/work-item.tsx`**
   - `WorkItem()` renders the queue card with status, lines, files, checks, and link

So the chain is:  
`dashboard/route.ts:GET/loadRepository` → `use-activity.ts:useActivity` → `page.tsx:Home/buildWorkItems` → `activity-model.ts:buildWorkItems/makeWorkItem` → `queue-view.tsx:QueueView/partitionWorkItems` → `work-item.tsx:WorkItem`.