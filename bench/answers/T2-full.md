Maximum steps for this agent have been reached. I can answer from the provided context only.

## Where dashboard GitHub data is fetched

- **`src/app/page.tsx`** uses the client hook `useActivity()`; it does not fetch directly.
- **`src/hooks/use-activity.ts`**:
  - `loadRepositories()` fetches the available repo list from `fetch("/api/github/repos")`.
  - `fetchDashboard()` fetches the dashboard payload from `fetch(`/api/github/dashboard?${params}`)` with the selected repos.
- **`src/app/api/github/repos/route.ts`**: `GET()` calls `githubFetch<GitHubRepository[]>("/user/repos?...")`.
- **`src/app/api/github/dashboard/route.ts`**:
  - `GET()` validates the `repo` query params and calls `loadRepository()` for each.
  - `loadRepository()` calls `githubFetch()` (and `optional<T>()`) for `/repos/{fullName}`, branches, PRs, deployments, reviews, check runs, comparisons, and deployment statuses. It also calls `readLocalState()` from `@/lib/local-git`.
- **`src/lib/github.ts`**: `githubFetch()`, `githubFetchPage()`, and `githubRequest()` make the actual GitHub REST API calls using the sealed session token.

## How the client hook stores it

- **`src/hooks/use-activity.ts`**:
  - Keeps live data in React state: `availableRepos`, `selectedIds`, `results`, `newRepos`, `changedItems`, `session`, etc.
  - Persists the user’s selected repository IDs to `localStorage` via `writeIds()` / `readIds()` with key `agent-activity-repositories-v2`.
  - Persists “seen” repo SHAs via `writeSeen()` / `readSeen()` using `seenKey(login)` in `localStorage`.
  - Persists per-work-item seen snapshots via `writeSeen()` / `readSeen()` using `itemsSeenKey(login)` in `localStorage`.
  - `markSeen()` updates both seen records, clears `newRepos`/`changedItems`, and writes the new snapshots.
  - Uses refs (`resultsRef`, `reposRef`, `selectedRef`, `seenRef`, `itemsSeenRef`) to avoid stale closures during polling/refresh.

## What is missing

The context does not show a server-side persistent store or a shared client store (e.g., Context, Zustand, Redux). GitHub data is fetched fresh on each request; only selection and “seen” markers are persisted, and that persistence is `localStorage` inside `useActivity`.