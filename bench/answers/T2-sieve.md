The dashboard’s GitHub data is fetched server-side, and the client hook only persists metadata/seen state in `localStorage`.

**Where the dashboard fetches GitHub data**

- **`src/app/api/github/dashboard/route.ts`**
  - `GET(request)` – the dashboard API route.
  - `loadRepository(fullName)` – called by `GET`; issues the GitHub calls.
  - `loadRepository` calls `githubFetch<T>` from **`src/lib/github.ts`** for:
    - `/repos/${fullName}`
    - `/repos/${fullName}/branches?per_page=100`
    - `/repos/${fullName}/pulls?state=open&per_page=100&sort=updated&direction=desc`
    - `/repos/${fullName}/deployments?per_page=1` (via `optional<Deployment[]>`)

- **`src/lib/github.ts`**
  - `githubFetch<T>(path)` / `githubRequest(...)` – perform the actual `https://api.github.com` requests.
  - `currentSession()` – loads/refreshes the OAuth token before each request.

**How the client hook stores it**

- **`src/hooks/use-activity.ts`**
  - `useActivity()` – the client hook.
  - Selected repositories are stored in `localStorage` under key `agent-activity-repositories-v2` (`REPOSITORIES_KEY`) via `readIds()` and `writeIds(ids)`.
  - Per-user “seen” state is stored under keys built by `seenKey(login)` and `itemsSeenKey(login)` via `readSeen(key)` and `writeSeen(key, snapshots)`.
  - `hasSeen(...)` checks whether an item has already been seen.

So the hook does **not** cache raw GitHub payloads in `localStorage`; it stores the selected repo ID list and seen-state snapshots.

**Missing from the context:** the body of `useActivity()` itself is truncated, so the exact `fetch('/api/github/dashboard...')` call and the React state wiring inside the hook are not shown. The full `GET` body in `src/app/api/github/dashboard/route.ts` is also cut off after the initial declarations.