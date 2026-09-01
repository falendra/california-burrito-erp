# Build progress

Update this after every phase. Keep entries short — this is a status log, not a diary.

## Phase 0 — Environment setup
- [x] frappe_docker cloned
- [x] Docker Compose services running (db, redis, backend), bind-mounted app directory
- [x] Site created, bare Frappe (no ERPNext), reachable and login confirmed
- [x] Confirmed host-side file edits reflect inside the container
- Site URL: http://development.localhost:8000 (macOS/most browsers resolve `*.localhost`
  to 127.0.0.1 automatically — no `/etc/hosts` edit needed. If it doesn't resolve for you,
  add `127.0.0.1 development.localhost` to `/etc/hosts`.)
- Login: `Administrator` / `admin`
- Status: Done. Frappe framework version-16 (16.32.0), Python 3.14.7, bare install —
  `installed_apps: ["frappe"]` only, no ERPNext. `bench doctor` clean; scheduler is
  disabled by default on a fresh site (fine — per `DocType_Spec.md` the core PM loop must
  work with the daily overdue job disabled; will enable explicitly in Phase 2+ when
  testing that job specifically).
- Blockers: none.

### How this was built
- Cloned `https://github.com/frappe/frappe_docker` into the project root (gitignored —
  see below).
- Used `frappe_docker/devcontainer-example/docker-compose.yml` as-is (mariadb 11.8,
  redis-cache, redis-queue, and a `frappe` service on `frappe/bench:latest` bind-mounting
  the whole `frappe_docker` repo to `/workspace`), invoked directly with
  `docker compose -p cb_erp up -d` instead of through VS Code's Dev Containers UI.
- Added `frappe_docker/devcontainer-example/docker-compose.override.yml` (one file, not
  upstream, not tracked by git since `frappe_docker/` is gitignored — exact contents below)
  to publish `8000:8000` — `devcontainer.json`'s `forwardPorts` is a VS Code-only mechanism
  and does nothing when the stack is driven by plain `docker compose`:
  ```yaml
  services:
    frappe:
      ports:
        - "8000:8000"
  ```
- Bootstrapped bench with `development/installer.py` (already in frappe_docker), passing
  an empty `apps-empty.json` (`[]`) instead of the default `apps-example.json` so it never
  clones ERPNext — bare Frappe only, per assignment.
- **Assumption/deviation from installer default:** pinned `--py-version 3.14.7`, not the
  more common 3.12. The `version-16` branch's `pyproject.toml` requires
  `Python>=3.14,<3.15`; 3.12.14 (also present in the image) fails dependency resolution.
  3.14.7 is already provisioned via pyenv in `frappe/bench:latest`, so no extra install
  needed.
- Site name: `development.localhost`, db root password `123` (frappe_docker's documented
  dev default, not a real secret), admin password `admin`.
- Bench and the site live on the host at
  `frappe_docker/development/frappe-bench/` (bind-mounted, not container-only) — confirmed
  a file written from the host appears inside the container instantly, and vice versa.
- Started the dev server with `bench start` (web + socketio + watch + worker + scheduler
  processes), run detached via `docker compose exec -d`, logging to
  `frappe_docker/development/bench_start.log` inside the bind mount.
- Verified reachability: `curl -H "Host: development.localhost" http://localhost:8000/login`
  → 200, and `curl http://development.localhost:8000/login` from the host (no explicit
  Host header) → 200, confirming it behaves the same as opening it in a browser.

### To bring the environment back up in a future session
```
cd frappe_docker/devcontainer-example
docker compose -p cb_erp up -d                      # starts db/redis/frappe container
docker compose -p cb_erp exec -d frappe bash -lc \
  "cd /workspace/development/frappe-bench && bench start > /workspace/development/bench_start.log 2>&1"
```
`bench start` is not part of the container's own entrypoint (the compose `frappe` service
just runs `sleep infinity`, matching the devcontainer-example pattern), so it must be
re-launched after every `docker compose up`/restart. Bench init and site creation are
one-time and already done — do not repeat them.

### Not committed to git
`frappe_docker/` (the cloned tooling repo, vendored Frappe framework, `node_modules`,
and MariaDB data volume) is gitignored — the assignment's deliverable is the custom app
only. The compose files needed to reproduce this are inside that gitignored tree; this
PROGRESS.md section is the record of how to regenerate it.

## Phase 1 — Master data
- [ ] App scaffolded, git initialized
- [ ] CB Zonal Office, CB Outlet, CB Asset Type, CB Asset, CB Technician created
- [ ] Manual fixture: 1 outlet, 2 assets, navigable Outlet → Assets
- Status:
- Blockers:

## Phase 2 — PM engine (fixture data only)
- [ ] CB PM Program, CB PM Schedule, CB PM Execution created
- [ ] `ensure_schedule()` implemented in `utils/schedule.py`
- [ ] Test 1 passes (asset applicability — matching asset type only)
- [ ] Test 2 passes (outlet-level applicability — all outlets)
- [ ] Test 4 passes (execution → next schedule)
- [ ] Test 5 passes (late execution doesn't cause drift)
- Status:
- Blockers:

## Phase 3 — Ticket workflow
- [ ] CB Ticket Taxonomy, CB Ticket created
- [ ] Test 6 passes (failed execution → ticket, atomic)
- [ ] Test 7 passes (duplicate submit rejected)
- [ ] Test 8 passes (cross-outlet asset validation)
- Status:
- Blockers:

## Phase 4 — Applicability hooks
- [ ] Test 3 passes (new asset → auto schedule)
- [ ] New outlet → outlet-level programs auto-scheduled
- [ ] Hero scenario manually verified (new outlet + 3 assets → correct partial PM coverage)
- Status:
- Blockers:

## Phase 5 — Import
- [ ] Asset alias normalization table built
- [ ] Frequency resolution (151 recovered / 37 logged unresolved) verified against actual counts
- [ ] Technician fuzzy-match with confidence threshold, unmatched logged
- [ ] All 4 source files imported in dependency order
- [ ] Import summary printed (counts + warnings)
- Status:
- Blockers:

## Phase 6 — Reports
- [ ] Due/overdue PM list view
- [ ] Open tickets by outlet/technician
- Status:

## Phase 7 — Deploy
- [ ] Hosted on Frappe Cloud, demo login created
- [ ] README written (what/why/cut/assumptions/AI usage/how to run)
- [ ] Public GitHub repo pushed (app folder only)
- [ ] Hero scenario clicked through on the live site
- Status:
