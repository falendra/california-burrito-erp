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
  upstream, not tracked by git since `frappe_docker/` is gitignored — exact contents below,
  kept up to date here whenever it changes): publishes `8000:8000` (`devcontainer.json`'s
  `forwardPorts` is a VS Code-only mechanism and does nothing when the stack is driven by
  plain `docker compose`), and bind-mounts the project root at `/workspace-project` — the
  `california_burrito` app lives there (see Phase 1), and this is what lets the bench's
  `apps/california_burrito` symlink resolve inside the container:
  ```yaml
  services:
    frappe:
      ports:
        - "8000:8000"
      volumes:
        - ..:/workspace:cached
        - "/Users/falendrabandhe/Desktop/california_burrito :/workspace-project:cached"
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
- [x] App scaffolded, git initialized
- [x] CB Zonal Office, CB Outlet, CB Asset Type, CB Asset, CB Technician created
- [x] Manual fixture: 1 outlet, 2 assets, navigable Outlet → Assets
- Status: Done. All 5 field lists/autonames verified via `frappe.get_meta()` against
  `docs/DocType_Spec.md` sections 1–5, exact match. `bench migrate` synced clean, no errors.
- Blockers: none.

### What was created
- `california_burrito` lives at the project root (`california_burrito/`, alongside
  `CLAUDE.md`), tracked directly in this repo — no separate git repo for the app. Inside the
  bench, `frappe_docker/development/frappe-bench/apps/california_burrito` is a symlink to
  this location, created from inside the `frappe` container so its target resolves there
  (`/workspace-project/california_burrito` — the project root is bind-mounted into the
  container for exactly this). The symlink is container-only: viewed from the host it looks
  broken, because `/workspace-project/...` isn't a real host path — that's expected, nothing
  on the host needs to follow it, only `bench` running inside the container does, and it does.
- **One naming fixup before creating any DocTypes:** the app-title prompt ("California
  Burrito Maintenance") made `bench new-app`'s cookiecutter derive a module named "California
  Burrito Maintenance" (folder `california_burrito_maintenance`) instead of the conventional
  single-module-matches-app-name layout. Uninstalled the (empty) app, renamed the module
  folder + `modules.txt` to "California Burrito", reinstalled — before any DocTypes existed,
  so no migration cost. Purely cosmetic file-layout call, not a domain decision.
- 5 master DocTypes, hand-authored as JSON under
  `california_burrito/california_burrito/doctype/<name>/` (the standard Frappe pattern —
  `developer_mode=1` is set, so `bench migrate` syncs hand-written doctype JSON straight into
  the DB) and synced with `bench --site development.localhost migrate`:
  - **CB Zonal Office** — `zonal_office_name` (autoname), `city` (Select).
  - **CB Outlet** — `outlet_code` (autoname, unique), `city`, `zonal_office` (Link), `status`.
  - **CB Asset Type** — `asset_type_name` (autoname, unique), `description`, `active`.
  - **CB Technician** — `employee_no` (autoname, unique), `technician_name`, `job_title`,
    `department` (default "Maintenance"), `email`, `mobile`, `zonal_office` (Link),
    `reports_to` (self-referential Link, blank for top of hierarchy), `user` (Link, optional),
    `active`.
  - **CB Asset** — `asset_id` (autoname `AST-.#####`), `asset_type` (Link), `outlet` (Link),
    `model`, `status`, `installation_date`.
  - Added one small UX primitive not spelled out in the spec but implied by the relationship
    summary: a `links` (Connections) entry on **CB Outlet** pointing at **CB Asset** via the
    `outlet` field — this is what makes "navigate Outlet → Assets" a real desk-UI affordance
    (sidebar "Assets" connection with a count) rather than something you can only get to via
    a manual list filter.
- Manual fixture (one Python script run once via `bench console`'s `%run`, then deleted —
  not committed, this is throwaway seeding, not an import script):
  - CB Zonal Office `BLR Zonal Office` (city BLR)
  - CB Outlet `BLR001` (city BLR, zonal_office → BLR Zonal Office, status Active)
  - CB Asset Type `Air Conditioner`, CB Asset Type `Walk-in Chiller`
  - CB Asset `AST-00001` (Air Conditioner, model "1.5 Ton Split AC Voltas") at BLR001
  - CB Asset `AST-00002` (Walk-in Chiller, model "2 Door Chiller Celfrost") at BLR001

### Navigation check (Outlet → Assets)
Confirmed at the exact API layer the desk UI's form sidebar uses:
`frappe.desk.form.linked_with.get_linked_doctypes("CB Outlet")` →
`{'CB Asset': {'fieldname': ['outlet']}}`, and `get_linked_docs("CB Outlet", "BLR001", ...)`
→ returns both `AST-00001` and `AST-00002`. This is the same call the "Connections" sidebar
on the Outlet form fires — confirms the addition of `links` above actually wires up the
navigation, not just that the data is queryable.

I also attempted a literal click-through via the browser automation tool, but it runs in a
network context that cannot reach this machine's Docker containers (it loads public sites
fine but times out identically on both `development.localhost:8000` and `127.0.0.1:8000` —
not a DNS issue, a network-reachability one). That's outside what I can fix from here; the
API-level check above exercises the identical backend code path the UI calls, so I'm
treating this as verified, but if you want to eyeball it yourself: open
`http://development.localhost:8000/app/cb-outlet/BLR001` after logging in, and the "Assets"
connection should show 2.

### Gotcha: `bench start` must be restarted after adding a new app
`bench start`'s long-running worker processes fix `sys.path` at interpreter startup. If
`bench start` was already running before `california_burrito` was created/installed, the
next scheduler tick hits `ModuleNotFoundError: No module named 'california_burrito'`, and
`bench start`'s process manager (honcho) tears down the whole process group when any one
member dies. Fix: relaunch `bench start` fresh — it then picks up the installed app.
**Lesson for future phases:** restart `bench start` after any `bench new-app` /
`bench get-app` / `bench install-app`, not just after `bench migrate`.

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
