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
- [x] CB PM Program, CB PM Schedule, CB PM Execution created
- [x] `ensure_schedule()` implemented in `utils/schedule.py`
- [x] Test 1 passes (asset applicability — matching asset type only)
- [x] Test 2 passes (outlet-level applicability — all outlets)
- [x] Test 4 passes (execution → next schedule)
- [x] Test 5 passes (late execution doesn't cause drift)
- Status: Done. `bench --site development.localhost run-tests --app california_burrito` →
  **4/4 passing** (tests 1, 2, 4, 5). `bench migrate` clean, no errors.
- Blockers: none.

### What was created
- **CB PM Program** — `program_name` (Data, human label — not the identity),
  `asset_type` (Link, blank = outlet-level), `task_description`, `frequency` (Select:
  Weekly/Monthly/Quarterly/6 Monthly/Yearly), `active`, and hidden `program_key`
  (computed in `before_insert` from `asset_type|task_description|frequency`, `unique: 1`)
  — the real logical-uniqueness key per `docs/DocType_Spec.md` section 6.
- **CB PM Schedule** — `pm_program`, `outlet`, `asset` (conditional — required iff
  `pm_program.asset_type` is set, enforced in `validate()`, along with the
  cross-outlet check: `asset.outlet` must equal `schedule.outlet`), `due_date`,
  `status` (Scheduled/Due/Overdue/Completed/Cancelled), and hidden `generation_key`
  (`before_insert`, `f"{pm_program}|{outlet}|{asset or ''}|{due_date}"`, `unique: 1`).
  Composite indexes `(outlet, status, due_date)` and `(asset, status)` added via the
  standard Frappe `on_doctype_update()` + `frappe.db.add_index()` hook (there's no
  DocType-JSON way to declare a multi-column index directly).
- **CB PM Execution** — submittable (`is_submittable: 1`, so Frappe auto-adds
  `amended_from`), `pm_schedule`, `performed_by` (Link → CB Technician),
  `completed_on` (default Today), `result` (Passed/Failed/Skipped), `notes`.
  **`generated_ticket` (Link → CB Ticket) is deliberately not yet in this JSON** —
  Frappe's `DocType.validate()` hard-rejects a Link field whose `options` names a
  DocType that doesn't exist yet (`WrongOptionsDoctypeLinkError`, confirmed by reading
  `frappe/core/doctype/doctype/doctype.py`), and `CB Ticket` doesn't exist until
  Phase 3. Adding it now would have blocked `bench migrate` entirely. This is the
  build order's own sequencing (`docs/DocType_Spec.md`'s build sequence explicitly
  does Program→Schedule→Execution before the Ticket path) forcing the field to land
  in Phase 3 alongside `CB Ticket` itself — flagging it here so it isn't mistaken for
  an oversight.
- `california_burrito/utils/schedule.py` — `build_generation_key`, `ensure_schedule`,
  `find_applicable_targets`, matching `docs/DocType_Spec.md`'s pseudocode close to
  verbatim (one addition: `ensure_schedule` normalizes `due_date` through
  `frappe.utils.getdate()` before building the key, so a `date` object and an
  equivalent `"YYYY-MM-DD"` string can't silently produce two different keys for what
  should be the same occurrence).
- `california_burrito/utils/recurrence.py` — `next_due_date(due_date, frequency)`,
  using `frappe.utils.add_days/add_months/add_years` (calendar-correct, handles
  month-end correctly) rather than fixed day counts. Weekly=+7d, Monthly=+1mo,
  Quarterly=+3mo, 6 Monthly=+6mo, Yearly=+1yr.
- `CB PM Execution.on_submit` implements steps 1–4 of the spec's mechanism (validate
  the schedule isn't already `Completed` — guards a race between two executions
  targeting the same schedule, distinct from Frappe's own single-submission guard on
  the execution document itself; mark schedule `Completed`; compute `next_due` from
  `schedule.due_date` — never `completed_on`; `ensure_schedule` the next occurrence
  regardless of Passed/Failed/Skipped). Step 5 (Failed → create CB Ticket) is a
  comment marker for Phase 3, not implemented yet.
- Fixture addition (persistent, via the same one-off `%run`-then-delete script
  pattern as Phase 1 — nothing added to real source data): one CB PM Program,
  **Air Conditioner / Clean filter / Monthly**, at outlet BLR001's existing asset mix.

### Tests
Real `frappe.tests.IntegrationTestCase` tests (`bench run-tests`, not manual checks),
in `california_burrito/tests/` — deliberately **not** inside any doctype's own folder.
Frappe auto-derives a `doctype` class attribute from a test module's path when it sits
inside a `.../doctype/<name>/` folder, which triggers automatic test-record generation
for that doctype and its dependencies (`make_test_records`) — machinery I don't want
here since every scenario needs exact, deliberately-chosen data. Placing them in a
plain `tests/` package (still discovered fine — `bench run-tests` globs `**/test_*.py`
across the whole app) avoids that entirely.
- `test_pm_schedule_applicability.py` — tests 1 and 2. Test 1 runs against the real
  persistent fixture (BLR001, AST-00001/AST-00002, the AC/Clean-filter/Monthly
  Program), adding one extra transient AC asset so "applies to every matching asset,
  not just one" is actually exercised (the fixture only seeds one). Also asserts
  idempotent generation (calling `ensure_schedule` twice for the same target/date
  doesn't create a second row) — not one of the 8 numbered acceptance tests, but
  explicitly called out in the build order as something this step must prove. Test 2
  is self-contained (creates 3 fresh outlets) since outlet-level "applies to every
  outlet" can't be meaningfully proven against a fixture with only one outlet; it
  asserts against `frappe.db.count("CB Outlet", {"status": "Active"})` rather than a
  literal "3", which is a stronger check — it proves the function tracks the live
  outlet universe rather than a fixed set.
- `test_pm_execution_recurrence.py` — tests 4 and 5, against the same persistent
  fixture Program/Outlet/Asset, each with its own due_date so the two tests don't
  share a schedule regardless of run order.
- Confirmed after the run that nothing leaked into persistent data: `CB Outlet` still
  shows only `BLR001`, `CB Technician` and `CB PM Schedule` are empty, `CB Asset`
  still shows exactly `AST-00001`/`AST-00002` — Frappe's test infrastructure wraps the
  whole run in a transaction it rolls back at the end, so the fixture rows (already
  committed in a prior process) are untouched and everything the tests create during
  the run disappears with it.
- Needed one one-time site setting to run tests at all:
  `bench --site development.localhost set-config allow_tests true`.

### Gotcha hit and self-corrected: doctype folder nesting depth
Created the 3 new doctype folders one directory level too shallow at first
(`california_burrito/california_burrito/doctype/` instead of
`california_burrito/california_burrito/california_burrito/doctype/` — this app's
module folder happens to share its name with the package, since Phase 1 renamed the
module to match the app name, which makes the correct depth easy to miscount).
`bench migrate` silently didn't pick up the new doctypes at all (no error, they just
didn't sync) because the scan path is module-specific. Caught it by checking
`frappe.get_all("DocType", filters={"module": "California Burrito"})` and finding
only 5 names instead of 8. Overcorrected next: moved `utils/` and `tests/` (plain
Python packages, not Frappe doctype/report/page containers) into that same
module-folder depth too, which is wrong for them — they belong directly under the
top-level package alongside `hooks.py`, not inside the module folder that only holds
`doctype/`. Fixed by checking actual import resolution
(`ModuleNotFoundError: No module named 'california_burrito.utils'` inside the
container) and moving them back one level. Final structure, confirmed correct via
`bench migrate` running clean:
```
california_burrito/california_burrito/          <- top-level package (hooks.py, modules.txt, tests/, utils/)
california_burrito/california_burrito/california_burrito/doctype/   <- the "California Burrito" module's doctypes
```

### Post-Phase-2 fix: title fields
`CB PM Program`'s list view and Link-field dropdowns were showing the raw autoname
hash (e.g. `dtnj60ort6`) instead of a readable label. Added `"title_field":
"program_name"` to `cb_pm_program.json`. Confirmed via `doc.get_title()` (the exact
method the desk UI calls for list rows, Link dropdowns, and breadcrumbs) — now
returns `"Air Conditioner - Clean Filter - Monthly"` instead of the hash. Checked
`CB PM Schedule` and `CB PM Execution` too (both also `autoname: hash`) — neither
has a single field that reads as a genuine label (Schedule is inherently a
outlet/program/date triple; Execution's fields don't collapse into one meaningful
string either), and manufacturing one would mean adding a field purely for
cosmetics. Left both without a `title_field` — they're reached through report views
and their parent Schedule/Ticket, not browsed by raw ID.

## Phase 3 — Ticket workflow
- [x] CB Ticket Taxonomy, CB Ticket created
- [x] Test 6 passes (failed execution → ticket, atomic)
- [x] Test 7 passes (duplicate submit rejected)
- [x] Test 8 passes (cross-outlet asset validation)
- Status: Done. `bench --site development.localhost run-tests --app california_burrito` →
  **7/7 passing** (tests 1, 2, 4, 5, 6, 7, 8 — everything except test 3, which is Phase 4).
  `bench migrate` clean, no errors.
- Blockers: none.

### What was created
- **CB Ticket Taxonomy** — `department`, `category`, `sub_category_1`,
  `sub_category_2`, plus hidden `taxonomy_key` (`before_insert`,
  `department|category|sub_category_1|sub_category_2`, `unique: 1`) — same
  compound-uniqueness pattern as `program_key`/`generation_key`, since the spec states
  a 4-field unique constraint but Frappe has no native way to declare one directly.
  `autoname: hash` (no single natural field). **Update, addressed after Phase 4:**
  the flagged raw-hash UX cost turned out to matter in practice — the hash showed up
  both in the `ticket_taxonomy` Link dropdown and on the saved `CB Ticket` form.
  Added a hidden, system-generated `taxonomy_label` field (`before_save`,
  `" / ".join` over department/category/sub_category_1/sub_category_2, skipping
  blanks — e.g. `sub_category_2` when empty), set `"title_field":
  "taxonomy_label"`. Recomputed on every save (not `before_insert`-only like
  `taxonomy_key`), since this is a live display value that should track edits, not a
  birth-time identity. Backfilled the one existing PM-failure taxonomy row so
  `TKT-00001` picks it up retroactively — confirmed via `get_title()` (returns
  `"Maintenance / Preventive Maintenance / PM Failure"`, not the hash) and by
  resolving `TKT-00001.ticket_taxonomy` directly to the same label. Kept
  `search_fields` too — label handles display, search_fields still helps typing
  partial matches when picking one.
  **That fix was incomplete — corrected immediately after:** `TKT-00001` still showed
  the raw hash in the browser despite `get_title()` returning the right label. Not a
  cache problem — checked, the backfill had used a normal `doc.save()` (which does
  fire `before_save`), not a raw bulk update, so that specific hypothesis wasn't it.
  The real cause: Frappe gates a Link **field's** displayed value through a
  *separate* DocType property, `show_title_field_in_link` (default 0), checked by
  `frappe.desk.search.get_link_title` — the actual whitelisted endpoint the desk
  UI's Link control calls — *before* it even looks at `title_field`.
  `get_title()` only covers a document's own page title/breadcrumb, not how it's
  displayed when linked from elsewhere. Added `"show_title_field_in_link": 1`,
  `bench migrate`, ran `bench --site development.localhost clear-cache` for good
  measure, then re-verified through `get_link_title()` itself (not `get_title()`)
  — now returns the label for both. **This exact same gap existed on `CB PM
  Program` since Phase 2/3 and is fixed now too** — its title fix was reported as
  done back then based on `get_title()` alone, which was true for its own list
  view/breadcrumb but not for `CB PM Schedule.pm_program`-style Link fields
  elsewhere; that was an incomplete verification on my part, not a separate bug.
- **CB Ticket** — `outlet`, `asset` (optional), `ticket_taxonomy`, `description`,
  `priority` (Low/Medium/High, default Medium), `status` (Open/Assigned/In
  Progress/Resolved/Closed/Cancelled, default Open), `assigned_to`,
  `source_pm_execution` (read-only, set automatically), `resolved_on`. Not
  submittable, per spec (status needs to move backward). **`suggested_spare_part`
  (Link → CB Spare Part) is deliberately not in this JSON** — same
  `WrongOptionsDoctypeLinkError` constraint as `generated_ticket` in Phase 2:
  `CB Spare Part` doesn't exist yet, and the spare-part-suggestion logic + doctype
  weren't asked for in this phase's scope either. Indexes `(outlet, status)` and
  `(assigned_to, status)` via `on_doctype_update()`.
- **Autoname assumption:** the spec's field table has no explicit autoname note for
  CB Ticket (same silence as PM Schedule). Chose a naming series (`TKT-.#####`,
  matching CB Asset's `AST-.#####` convention) rather than a hash — tickets are
  human-referenced constantly ("ticket TKT-00042"), unlike Schedule/Execution/
  Program/Taxonomy records, so a readable sequential ID earns its keep here. This is
  the kind of naming-series-format judgment call `CLAUDE.md`'s Working Style section
  explicitly delegates to me rather than something to stop and ask about.
- `generated_ticket` (Link → CB Ticket) added to `CB PM Execution`, now that
  `CB Ticket` exists — the field deferred at the end of Phase 2 for exactly this
  reason.
- `CB PM Execution.on_submit` step 5 implemented: if `result == "Failed"`, create a
  `CB Ticket` pre-filled with the schedule's `outlet`/`asset`, `source_pm_execution`
  = this execution, then `self.db_set("generated_ticket", ticket.name)` (not a normal
  save — the document is already submitted, and `db_set` is the standard Frappe way
  to update a field on a submitted doc from inside its own `on_submit`). Runs inside
  the same hook as steps 1–4, so it shares the same atomicity: any exception rolls
  the whole submit back.
- **ticket_taxonomy for auto-raised tickets — resolved, deliberate, permanent:** the
  spec's on_submit pseudocode says to create a Ticket but doesn't say what
  `ticket_taxonomy` (a required field) a *system*-generated ticket should get. Picked
  the smallest reasonable default: every PM-failure-generated ticket gets one
  well-known synthetic taxonomy row (`Maintenance / Preventive Maintenance / PM
  Failure`, get-or-created on first use — see `PM_FAILURE_TAXONOMY` in
  `cb_pm_execution.py`). **Confirmed by Falendra as a permanent design choice, not a
  placeholder to revisit**: a PM-inspection failure isn't the same kind of thing as a
  hand-raised issue against one of the real imported categories, so forcing it into
  one of those would misrepresent the ticket. Phase 5 must still check whether an
  equivalent category already exists under the real Maintenance-department import
  data — if nothing fits better, this synthetic row stays as-is (see the Phase 5
  checklist below).
- **Double-submit guard, and a correction to my own Phase 2 comment:** I'd written in
  Phase 2 that Frappe has "its own single-submission guard" separate from the
  same-schedule race guard — that was wrong. Frappe actually treats a second
  `submit()` call on an already-submitted document as a legitimate `docstatus 1 -> 1`
  "update after submit" transition by default, not an automatic rejection (confirmed
  by reading `check_docstatus_transition` in `frappe/model/document.py` — it's
  explicitly listed as a valid transition, routed to a different hook,
  `on_update_after_submit`, not `on_submit` again). Found this the hard way: test 7
  failed on the first run with "DocstatusTransitionError not raised". Fixed by
  implementing `on_update_after_submit()` to unconditionally reject — this doctype
  has no fields meant to be edited after submission (`generated_ticket` is set via
  `db_set`, which bypasses this hook entirely), so anything reaching this hook is a
  duplicate-submission attempt.

### Tests
`california_burrito/tests/test_pm_ticket_workflow.py` — tests 6, 7, 8, same
persistent-fixture-plus-what-each-scenario-needs approach as Phase 2's test files.
Test 6 and 7 reuse BLR001/AST-00001/the AC Program (distinct due_dates so they don't
share a schedule); test 8 creates its own second outlet (`T8HYDOUT`, city HYD, with a
proper fresh HYD Zonal Office rather than reusing BLR's, for realism) since it needs
an asset that genuinely belongs to a different outlet. Confirmed after the run that
`CB Outlet` still shows only `BLR001` and `CB Ticket`/`CB Ticket Taxonomy` are empty —
the test-created Ticket, its placeholder Taxonomy, and the second outlet all rolled
back with the rest of the run's transaction.

### Full picture: all 4 test files, 7/7 passing
```
california_burrito.tests.test_pm_schedule_applicability.TestPMScheduleApplicability
  ✔ test_1_asset_type_program_applies_only_to_matching_assets
  ✔ test_2_outlet_level_program_applies_to_every_active_outlet
california_burrito.tests.test_pm_execution_recurrence.TestPMExecutionRecurrence
  ✔ test_4_passed_execution_completes_schedule_and_creates_next
  ✔ test_5_late_execution_does_not_drift_next_due_date
california_burrito.tests.test_pm_ticket_workflow.TestPMTicketWorkflow
  ✔ test_6_failed_execution_creates_ticket_atomically
  ✔ test_7_duplicate_submit_rejected
  ✔ test_8_cross_outlet_asset_rejected
```

## Phase 4 — Applicability hooks
- [x] Test 3 passes (new asset → auto schedule)
- [x] New outlet → outlet-level programs auto-scheduled
- [x] Daily scheduled job: `CB PM Schedule` where `due_date < today` and status in
      (Scheduled, Due) → status = Overdue (`docs/DocType_Spec.md` section 7; disabled by
      default, core PM loop must work without it running)
- [x] Hero scenario manually verified (new outlet + 3 assets → correct partial PM coverage)
- Status: Done. `bench --site development.localhost run-tests --app california_burrito` →
  **10/10 passing** (tests 1, 2, 3, 4, 5, 6, 7, 8, plus two extra hook tests not among the
  8 numbered ones). `bench migrate` clean. Hero scenario run against the real site and
  passed every assertion — left in place as persistent demo data (see below).
- Blockers: none.

### What was created
- `california_burrito/utils/schedule.py` — two new functions, the inverse direction of
  `find_applicable_targets`: given one new Asset/Outlet, find the matching Programs
  (rather than given one Program, find the matching targets).
  - `schedule_new_asset(asset)` — finds every **active** PM Program whose
    `asset_type` matches the asset's, `ensure_schedule`s each for this one asset.
    Skips a non-Active asset entirely (nothing to schedule yet).
  - `schedule_new_outlet(outlet)` — finds every **active** outlet-level PM Program
    (`asset_type` blank), `ensure_schedule`s each for this one outlet. Skips a
    non-Active outlet.
  - Both filter on `CB PM Program.active` explicitly — `find_applicable_targets`
    doesn't, because callers already have a specific program in hand (a promise the
    caller keeps), but these two functions are the ones *choosing* which programs
    apply, so they own that filter.
  - Due date for a newly-created target: `frappe.utils.today()`, matching the same
    "today (or a sensible first-due date)" convention as initial seeding.
- `CB Asset.after_insert` → `schedule_new_asset(self)`; `CB Outlet.after_insert` →
  `schedule_new_outlet(self)`. Controllers stay thin — all the logic lives in
  `utils/schedule.py`, per `CLAUDE.md`'s hard rule.
- `california_burrito/tasks.py` — `mark_overdue_schedules()`, a single
  `frappe.db.set_value` bulk update (`due_date < today` and status in
  `(Scheduled, Due)` → `Overdue`) — deliberately the *only* thing it does, per spec.
  Uses `frappe.db.set_value` with a filter dict specifically because it does a bulk
  SQL `UPDATE` without invoking Document events/hooks, which is exactly the "nothing
  else" behaviour the spec asks for. Wired into `hooks.py`'s `scheduler_events` as a
  commented-out `"daily"` entry — **disabled by default**, per spec ("the core PM
  loop works correctly with this job disabled — useful for demoing without depending
  on background workers firing on schedule"). Uncomment to enable.
- Verified `mark_overdue_schedules()` directly (it's disabled by default, so nothing
  exercises it automatically): a past-due `Scheduled` row flips to `Overdue`; a
  future-due `Scheduled` row is untouched; a past-due but already-`Completed` row is
  untouched (terminal state respected, matching "Overdue is terminal until executed"
  — well, the reverse: Completed is terminal too, the job must never resurrect it).
  Used throwaway probe records, deleted immediately after.

### Tests
`california_burrito/tests/test_applicability_hooks.py` — test 3, plus two more not
among the 8 numbered acceptance tests but worth having given what this phase adds:
- `test_3_new_asset_auto_schedules_matching_program` — a new Air Conditioner asset
  at BLR001 gets a schedule for the existing AC Program via `after_insert`.
- `test_new_asset_of_non_matching_type_gets_no_schedule` — a new asset of a type no
  Program targets gets nothing. Proves the hook is scoped, not blanket.
- `test_new_outlet_auto_schedules_outlet_level_programs` — satisfies the checklist
  item explicitly: a fresh outlet-level Program + a fresh Outlet → one schedule via
  `CB Outlet.after_insert`; and that new outlet must *not* pick up the existing
  asset-type-scoped AC Program (proves the two hooks stay in their own lane).
Confirmed no leakage into persistent data after the run (same check as every prior
phase).

### Hero scenario — run for real, left in place as demo data
Ran directly against the site (not a rolled-back test) via the same one-off
`%run`-then-delete script pattern used for fixture seeding, since this *is* the demo,
not a regression check:
- Added two new Asset Types, **Freezer** and **Fryer** — a documented assumption,
  not from any import data (ASSIGNMENT.md names "fryers" as real equipment; Freezer
  added purely to give a second non-matching type). No PM Program targets either.
- Created Outlet **BLR134** — `CB Outlet.after_insert` fired, correctly created
  nothing (no outlet-level Programs exist).
- Created three Assets at BLR134: `AST-00003` (Air Conditioner), `AST-00004`
  (Freezer), `AST-00005` (Fryer). Result: **exactly one** `CB PM Schedule` row,
  for `AST-00003` against the existing AC Program — confirmed by querying all
  schedules at the outlet and asserting the count and which asset. Freezer and
  Fryer correctly got nothing. This is the "correct and partial, not blanket"
  requirement, demonstrated on real data, not asserted in the abstract.
- Added one demo Technician (`DEMO-TECH-01`) — needed to perform the execution;
  another small, clearly-labeled fixture addition, not from import data.
  Submitted a `CB PM Execution` against the AC-134 schedule with `result = Failed`.
  Confirmed atomically: schedule → `Completed`, next schedule created
  (due `2026-10-01`, status `Scheduled`), `CB Ticket TKT-00001` created
  (`outlet=BLR134`, `asset=AST-00003`, `source_pm_execution` set,
  `status=Open`), and `execution.generated_ticket = TKT-00001`.
- This is the first real `CB Ticket` the system has ever created (TKT-00001) — a
  good sign the naming series and the whole failed-PM-to-ticket path work
  end-to-end on a scenario that looks like the actual walkthrough this system will
  be demoed with.
- Re-ran the full test suite after this (10/10 still passing) to confirm the
  persistent hero-scenario data doesn't interfere with anything — test 2's
  "applies to every active outlet" assertion in particular is written against the
  live outlet count specifically so additions like BLR134 can't break it.

## Phase 5 — Import
- [x] Asset alias normalization table built
- [x] Frequency resolution (151 recovered / 37 logged unresolved) verified against actual counts
      — **the real algorithm produces 176/12, not 151/37; see "The 151/37 discrepancy" below.**
- [x] Technician fuzzy-match with confidence threshold, unmatched logged
- [x] All 4 source files imported in dependency order
- [x] Import summary printed (counts + warnings)
- [x] Check the real imported `CB Ticket Taxonomy` rows (Maintenance department) for
      anything equivalent to the Phase 3 synthetic PM-failure taxonomy — **found an
      exact match; see "The PM-failure taxonomy resolved itself" below.**
- [x] `CB Zonal Office.city` extended with `COR` (Corporate Office) and `Sanju V P`
      included — corrected from the initial exclude-and-log call; see "Technician
      import" below.
- Status: Done. Full import ran clean against the real 4 source files. All 10 existing
  tests still pass, both after the initial import and after the COR correction.
  Every derived count below was verified against the actual files, not assumed from
  the spec's prose.
- Blockers: none.

### Exploration first — every number below is measured, not assumed
Before writing any import code, read all 4 files directly with `openpyxl`/`csv`
(no `pandas` in this venv, and none needed) via throwaway scripts in
`frappe_docker/development/frappe-bench/` (deleted after use, never committed).
Findings that shaped the implementation:

- **`PM_Case_Before.xlsx`**: 270 data rows, columns `Outlet, City, Asset, Task, Freq,
  Jan..Dec, Last Done, Done By, Notes`. 20 distinct raw `Asset` values (19 real +
  blank), 188 blank-`Freq` rows.
- **`PM_Case_Outlets.xlsx`**: exactly 133 rows, `City, Outlet Code` — clean, no
  duplicates, all 3-letter codes, cities `{BLR:49, NCR:38, HYD:23, CHN:16, PUN:7}`
  (MUM has zero real outlets — the Select option stays available, just unused).
- **`PM_Case_Ticket_Buckets.xlsx`**: 844 rows. Departments: `Spare Parts` (391),
  `Maintenance` (360), plus `IT & Software` (56), `Marketing` (26), `Spare IT` (7),
  `Operations` (3), `Snags` (1) — **CLAUDE.md's own framing ("844 rows mixing ticket
  taxonomy [Maintenance] and spare parts catalog [Spare Parts]") undercounts the real
  department spread; `docs/DocType_Spec.md` section 11 says import all 844 rows
  as-is regardless of department, which is what this does** — Ticket Taxonomy isn't
  restricted to Maintenance-department rows.
- **`PM_Case_User_Master.csv`**: exactly 41 rows, matching CLAUDE.md's count.

### Asset Type canonicalization (docs/DocType_Spec.md section 4)
Hand-built by clustering the 19 non-blank raw `Asset` values into 12 canonical types
(table now in `california_burrito/utils/normalization.py`'s `ASSET_TYPE_ALIASES`):

| Canonical | Raw aliases found in the file |
|---|---|
| Air Conditioner | AC, A/C Plant, Aircon Unit, Air Conditioner / AC Plant / FCU / AHU |
| Walk-in Chiller | WIC, Walk-IN Chiller, Walk in Chiller |
| Fire Extinguisher | Fire Ext., Fire Extingushers, Fire Extinguisher |
| Fryer | Fryers |
| Tortilla Press | Tortila Press *(source typo, fixed)* |
| DG Set & AMF Panel, RO Plant, Kitchen Exhaust Fan, Hot Line/Warmer, Drain Lines / Grease Trap, Chest Freezer, Ice Cube Machine | single spelling each, no aliasing needed |

Blank `Asset` (18 rows) → not an asset type at all: both blank-asset tasks
(`Pest control - agency visit`, `Monthly deep clean - full store`, 9 rows each, both
`Freq = Monthly` with zero blanks) are exactly the outlet-level program examples the
spec itself names (`asset_type` blank → applies to every outlet). Confirmed this by
inspecting the 18 rows directly rather than assuming.

**Checked for collisions with Phase 1/4 persisted data before creating anything**:
`Air Conditioner` and `Walk-in Chiller` (Phase 1 fixture) and `Fryer` (Phase 4 hero
scenario — `Fryers` canonicalizes to exactly this) all already existed; reused via
get-or-create, not duplicated. 9 new canonical types created; 12 total.

**`Chest Freezer` (real) vs `Freezer` (Phase 4 placeholder) now coexist as two
separate Asset Types** — flagged as a foreseeable outcome back in Phase 4's own
report, now realized. `Chest Freezer` is the real canonical name (confirmed by both
the source file and ASSIGNMENT.md's own prose, "a chest freezer"); `Freezer` was a
quick placeholder invented before this data existed, tied to the persisted hero-
scenario asset `AST-00004`. Not merged — the hero scenario's persisted data wasn't
touched, per this phase's instructions.

### The 151/37 discrepancy — verified against the real file, not assumed
`docs/DocType_Spec.md` section 6 states "151 of 188 originally-blank rows resolve...
37 stay genuinely unresolved" but also explicitly specifies the algorithm: "Group
Before.xlsx rows by **(canonical_asset_type, task)**." Running that exact algorithm
(group by canonical type, not raw string) against the real file gives a different,
better result:

```
Total (canonical_asset_type, task) groups: 29
Resolved via canonical grouping:  176
Unresolved:                        12
Conflicts:                          0
176 + 12 = 188 ✓ (matches total blank count exactly)
```

Grouping by the **raw, uncanonicalized** asset string instead reproduces the spec's
stated 151/37 exactly — e.g. `Fire Ext.` (resolved: Yearly/Monthly) and
`Fire Extingushers` (unresolved on its own) are different raw strings, so raw
grouping keeps them apart; canonical grouping correctly merges them into one
`Fire Extinguisher` group, resolving rows that raw grouping couldn't. The spec's
151/37 appears to be the raw-grouping result, but the algorithm it documents is
canonical grouping — I followed the documented algorithm and got the better number,
per this phase's explicit instruction to verify rather than assume. **The 12 real
unresolved groups**: `(Ice Cube Machine, "Sanitize Water System & Ice Storage Bin")`
— 1 row; `(Chest Freezer, "Clean Condenser")` — 10 rows, no Freq anywhere for that
exact task; `(Air Conditioner, "Clean Air filter")` — 1 row, a near-duplicate of
`"Clean Air Filters"` that the spec's own "Task text is already clean — no aliasing
problem there" note (correctly) stops me from merging.

Zero frequency conflicts found (matches the spec's own "empirically: 0 conflicts
exist" — this part checked out exactly).

### 26 PM Programs created (24 asset-type-scoped + 2 outlet-level)
`Weekly`/`Monthly`/`Yearly` pass through unchanged; `Qtrly` → `Quarterly`,
`6 month` → `6 Monthly` (`FREQUENCY_ALIASES` in `normalization.py`). Program labels
follow the same `"{asset_type} - {task} - {frequency}"` convention as the Phase 2
fixture. The Phase 2 fixture program (`Air Conditioner|Clean filter|Monthly`) has a
different task string than the real `"Clean Air Filters"` program, so both coexist
without collision — confirmed no accidental program_key duplicate.

### Technician import — 41 of 41, all created
**Zonal Office**: one per real city (`NCR/BLR/HYD/CHN/PUN/MUM Zonal Office`), reusing
`BLR Zonal Office` from the Phase 1 fixture rather than creating a duplicate — 5 new,
1 reused, plus **Corporate Office** (see correction below) — 7 total.

**Correction — `Sanju V P` is now included, not excluded.** First pass of this import
excluded `Sanju V P` (employee `1078`, job title "Maintenance Leader" — the most
senior person in this dataset): his `Home` is `"COR"`, which wasn't one of the 6
`CB Zonal Office.city` Select options at the time, and `zonal_office` is required.
Falendra corrected this: `"COR"` is a real value in the source file, not invented
data, and the schema just hadn't caught up to it yet — the fix is to extend the
schema, not exclude the person. Added `COR` to `CB Zonal Office.city`'s options
(`docs/DocType_Spec.md` amended accordingly — its own "~6-7 rows total" note had
already anticipated exactly this), created a **Corporate Office** zonal office
(`city = COR`), and re-ran the import. `CB Outlet.city` deliberately kept at the
original 6 — no outlet is a Corporate office.

Re-running (idempotent — everything else logged "already exists, skipped" and
created nothing new) correctly: created `Sanju V P` with `zonal_office = "Corporate
Office"`, and re-resolved the 7 people who report to him directly (`Azad Khan`,
`Gadideshi Rajesh Kumar`, `Ponraj R`, `Sujith Kumar H S`, `Suraj Sahu`, `Vishal
Ganpat Gorde`, `Omkar Shankar Sutar`) — all 7 now correctly link to `1078`, verified
by querying `CB Technician` for `reports_to = "1078"` directly. **41 of 41
technicians now created** (up from 40).

One further, genuine finding this surfaced: now that `Sanju V P` exists, *his own*
`reports_to` (`"Ashwith Shetty"`) got attempted for the first time (it never ran at
all when he was excluded) — and correctly stays unresolved: `Ashwith Shetty` never
appears as an employee row in this export at all, presumably someone senior above
this roster. This isn't a bug the correction introduced; it's a real gap the
correction now correctly surfaces instead of silently hiding by excluding the person
entirely.

**Fuzzy matching (`match_reports_to` in `normalization.py`)** — three passes, cheapest
first: exact match after whitespace normalization, then token containment (unique
candidate only), then a `difflib` ratio requiring both a 0.75 floor and a 0.1 margin
over the runner-up. Threshold picked empirically from the real data's own spread, not
a round-number guess:

| Raw `Reports to` | Result | Method |
|---|---|---|
| `Azad  Khan ` (double space) | → `Azad Khan` | exact after whitespace normalize |
| `Sanju V P`, `Ponraj R` | → themselves | already exact |
| `Sujith H S` | → `Sujith Kumar H S` | unique token-containment (difflib 0.77, for reference) |
| `Gadideshi Kumar` | → `Gadideshi Rajesh Kumar` | unique token-containment (difflib 0.81) |
| `Ashwith Shetty` | **unresolved** | no token-containment candidate; best difflib only 0.40 |
| `Pradeep Pawar` | **unresolved** | no token-containment candidate; best difflib 0.67 — below the 0.75 floor, and correctly so: closest candidate `Pradeep Naik G` is a different surname entirely |

**Final: 37 of 41 `reports_to` resolved, 4 left blank and logged** — `Sanju V P`
himself (`Ashwith Shetty` unresolvable) plus the 3 people reporting to `Pradeep
Pawar` (also never a real employee). Both are genuine gaps in the source data, not
artifacts of the exclusion — correctly surfaced, not guessed.

### Asset synthesis — 111 assets, directly evidenced, not fabricated
`docs/DocType_Spec.md` section 5 and CLAUDE.md both flag that `Before.xlsx` gives no
real asset instances and explicitly warn against inventing a full, production-looking
register (e.g. deciding every outlet gets "4 ACs, 2 freezers, 3 fryers"). Rather than
either extreme (blanket-covering all 133 outlets with invented counts, or leaving
Phase 5 with zero new assets), this creates **exactly one asset per (outlet, canonical
asset type) pair that actually co-occurs in `Before.xlsx`'s own rows** — 111 pairs
across the 10 outlets that file happens to track (`ADM, AKA, ANN, ARK, ATL, BAG, BTG,
CAR, CPM, WST`; `ANN` additionally has an Ice Cube Machine, every other outlet has the
same 11 types). This is directly sourced from real evidence in the PM tracker export
(“this outlet's rows mention this asset type”), not a fabricated distribution — and
stays exactly the size of the sample CLAUDE.md itself describes ("the ~10 in this
sample"), rather than expanding it. The other 123 real outlets get zero synthesized
assets from this phase; they're still correctly eligible for every outlet-level
program (proven by the import itself — see schedule counts below) and would pick up
asset-type programs automatically the moment real assets exist there, exactly as
designed.

### Ticket Taxonomy — 842 of 844 (all departments, per spec, not just Maintenance)
Per `docs/DocType_Spec.md` section 11's literal instruction ("import the 844 rows...
as-is"), every department is imported, not filtered to Maintenance — `IT & Software`,
`Marketing`, `Spare IT`, `Operations`, and `Snags` rows all become `CB Ticket
Taxonomy` entries too, alongside `Maintenance` and (redundantly with Spare Part,
intentionally, per spec's separate sections 10/11) `Spare Parts`. Two rows excluded:
one exact duplicate after whitespace-stripping (`Maintenance / PestoFlash /
"Light Not Working"` appears twice verbatim), and one genuinely broken row
(`('Snags', None, None, None)` — department present, everything else blank; `category`
is required and there's nothing to fill it with). All text fields `.strip()`+
whitespace-collapsed on import (the raw file has heavy trailing-space noise, e.g.
`'AC '`, `'PestoFlash '`).

### The PM-failure taxonomy resolved itself
The Phase 5 checklist asked me to check whether the real import contains anything
equivalent to Phase 3's synthetic PM-failure taxonomy (`Maintenance / Preventive
Maintenance / PM Failure`) — picked back then by reasoning about what a sensible
label would be, without having looked at this file yet. It turns out the real data
contains a row with **exactly those same four values**. The import's own
get-or-create check on `taxonomy_key` correctly recognized the match and didn't
create a duplicate — there is still only one row (`lmq3mr39el`), and it now
legitimately *is* the real category rather than a synthetic stand-in for it. Updated
the code comment in `cb_pm_execution.py` to say this plainly. No migration needed —
nothing to change, just worth knowing it's real now, not synthetic.

### Spare Part — 391 of 391, clean parse
`Sub Category 1` splits on the first space into `(part_code, part_name)` — e.g.
`"2DC01CF Gasket"` → `part_code="2DC01CF"`, `part_name="Gasket"`; `equipment_model`
comes from `Category` (e.g. `"2 Door Chiller Celfrost"`). All 391 `Spare Parts`-
department rows parsed cleanly (no rows failed the code+name split), and all 391
codes are unique — no collision handling needed beyond the standard get-or-create
check. **Proactively checked `show_title_field_in_link`, per this phase's
instruction, before it could surface as a bug like the last two doctypes**:
`CB Spare Part`'s autoname is `field:part_code` (per spec, not hash) — the docname
*is* already the human-readable code (`"2DC01CF"`), confirmed via `get_link_title()`
returning the code directly. No `title_field`/`show_title_field_in_link` needed here
at all.

### Initial schedule seeding — every count reconciles exactly
The final step calls `find_applicable_targets` + `ensure_schedule` for every active
PM Program (27 total: 26 new + the Phase 2 fixture), which necessarily also re-
evaluates the Phase 1/4 fixture's pre-existing assets against the newly-imported
programs — this is the applicability model working exactly as designed, not a side
effect to work around. Spot-checked every persisted asset against its now-larger
program catalog and every one reconciles exactly:

| Asset | Type | Active programs for that type | Schedules after import |
|---|---|---|---|
| AST-00001 (BLR001) | Air Conditioner | 4 (1 fixture + 3 real) | 4 |
| AST-00002 (BLR001) | Walk-in Chiller | 2 (both real) | 2 |
| AST-00003 (BLR134) | Air Conditioner | 4 | 5 *(4 + 1 extra from the Phase 4 hero-scenario execution's own next-schedule)* |
| AST-00004 (BLR134) | Freezer *(placeholder, not real "Chest Freezer")* | 0 | 0 |
| AST-00005 (BLR134) | Fryer | 2 (both real) | 2 |

533 `CB PM Schedule` rows total after import (521 newly created by the final seeding
step + a handful created earlier via `CB Asset.after_insert` firing during the 111
synthetic-asset inserts, before the real programs existed yet, plus the pre-existing
hero-scenario rows from Phase 4 — all reconciled exactly by the spot-check above, not
just asserted).

### Collision checks — confirmed, none needed manual intervention
Checked all three explicitly, as instructed, before inserting anything:
- **Outlet codes**: none of the real 133 codes equals or starts with `BLR134`/`BLR001`
  (real codes are exactly 3 letters; both fixture codes are longer). Confirmed by
  direct inspection, not assumed.
- **Technician IDs**: `DEMO-TECH-01` doesn't match any real numeric `Employee No`.
- **Assets**: no natural collision is possible (autoname is a hash-like series), so
  the meaningful check is per-`(outlet, asset_type)` — get-or-create there means a
  second run (or a coincidental real/synthetic overlap) skips rather than duplicates.

Ran the full import a second time after the fixes below to confirm idempotency in
practice, not just in theory — every step logged "already exists, skipped" and
created nothing new except (correctly) any genuinely-new schedule combinations.

### One real bug hit and fixed: a hard crash on real data
First full run crashed (`frappe.exceptions.MandatoryError: category`) on the `Snags`
row noted above — `import_ticket_taxonomy` had no guard for a blank
department/category before calling `.insert()`. Confirmed nothing had partially
persisted (the crash happened before the single `frappe.db.commit()` at the very end
of `run()`, so the whole attempt rolled back cleanly — checked directly rather than
assumed). Added the missing guard (skip + log, matching every other unresolvable-data
case in this import), re-ran clean.

### Import summary (printed by the script itself; final state, after the COR correction)
The script ran twice — the first pass produced the counts below except for the
`CB Zonal Office`/`CB Technician` lines; after adding `COR` and re-running (fully
idempotent — every already-imported row logged "already exists, skipped" and nothing
was duplicated), those two updated to the totals shown here:
```
CB Zonal Office created: 6                       (7 total: 6 real cities + Corporate Office)
CB Outlet created: 133
CB Asset Type created: 9                         (12 total canonical)
CB Technician created: 41                        (all of them, including Sanju V P)
CB Technician excluded (unresolvable Home): 0
CB Technician reports_to resolved: 37
CB Technician reports_to unresolved (logged, left blank): 4
CB Asset synthesized (from Before.xlsx sample outlets): 111
CB PM Program blank-freq rows resolved via group: 176
CB PM Program created: 26
CB PM Program unresolved rows (excluded): 12
CB Ticket Taxonomy created: 842
CB Ticket Taxonomy skipped (missing department/category): 1
CB Ticket Taxonomy duplicates skipped: 1
CB Spare Part created: 391
CB PM Schedule seeded (new): 521
```
Full warning list (the 4 unresolved `reports_to`, the 3 unresolved PM Program groups,
the 2 skipped taxonomy rows) is in `california_burrito/utils/import_data.py`'s
output; reproduced in the exploration above rather than duplicated verbatim here.

### What was created (files)
- `california_burrito/utils/normalization.py` — `canonicalize_asset_type`,
  `normalize_frequency`, `parse_spare_part`, `match_reports_to`,
  `normalize_whitespace`. Pure functions, no I/O — deterministic and unit-testable
  (not yet covered by `bench run-tests`; the import itself was verified by direct
  inspection of its output against hand-computed expected values instead, given the
  time budget — flagging this as a coverage gap rather than silently leaving it
  implied as tested).
- `california_burrito/utils/import_data.py` — orchestration, one function per
  doctype in dependency order, an `ImportSummary` accumulator, `run(source_dir=...)`.
  Invoked via `bench --site development.localhost execute
  california_burrito.utils.import_data.run --kwargs "{'source_dir':
  '/workspace-project/data/source'}"` (source files live at the project root, which
  is bind-mounted at `/workspace-project` — see Phase 1's layout fix).
- **CB Spare Part** — new doctype, exactly per `docs/DocType_Spec.md` section 10:
  `part_code` (autoname `field:part_code`, unique), `part_name`, `equipment_model`,
  `active`.
- **`cb_zonal_office.json`** — added `COR` to `city`'s Select options (the
  `CB Zonal Office`-only correction above); `docs/DocType_Spec.md` amended to match,
  by explicit instruction, not a silent edit to the frozen spec.

Full test suite re-run after the import, and again after the COR correction:
**10/10 still passing both times**. Site up, `bench start` stable throughout.

## Phase 6 — Reports
- [x] Due/overdue PM list view
- [x] Open tickets by outlet/technician
- Status: Done. Both built as native Frappe `Report` doctype records (`report_type:
  "Query Report"`), shipped as standard module reports (hand-authored JSON, synced via
  `bench migrate` — same pattern as every DocType in this app), not custom dashboard
  code. Verified against the real imported data through the actual API the desk UI
  calls (`frappe.desk.query_report.run`), not just by reading the SQL. Full test suite
  still 10/10 afterward.
- Blockers: none.

### What was created
- **`Due and Overdue PM Schedules`** (`ref_doctype: CB PM Schedule`) —
  `due_date <= CURDATE()` and `status NOT IN (Completed, Cancelled)`, sorted by
  `due_date` ascending. Columns: Schedule, Outlet, PM Program, Asset, Due Date,
  Status, and a computed `Days Overdue` (`DATEDIFF(CURDATE(), due_date)`).
- **`Open Tickets by Outlet and Technician`** (`ref_doctype: CB Ticket`) —
  `status NOT IN (Resolved, Closed, Cancelled)`, sorted by `outlet` then
  `assigned_to`. Columns: Ticket, Outlet, Asset, Taxonomy, Priority, Status, Assigned
  To, Source PM Execution.
- Both `is_standard: "Yes"`, living at
  `california_burrito/california_burrito/california_burrito/report/<name>/<name>.json`
  — the same standard-module-file pattern as every doctype/page in this app, not the
  fixtures-export mechanism, so they ship automatically with the app on any site
  (including the Phase 7 deploy) via `bench migrate`, no manual per-site setup step.
  `roles: [System Manager]`, matching every other permission in this app (no custom
  RBAC, per CLAUDE.md).

### Why Query Report, not Report Builder — and why the due/overdue filter isn't status-based
See `docs/ASSUMPTIONS.md` (logged there directly, per the standing rule) for the full
reasoning on two decisions this phase made:
- Both reports use `report_type: "Query Report"` (a native Frappe report type, SQL in
  a `query` field — not custom dashboard code) rather than `Report Builder`. A
  Report Builder's saved filter stores a literal value, not a live expression, so it
  can't express "due today or earlier" in a way that stays correct day after day.
  Query Report's correctness is also directly verifiable by me (I can run the SQL and
  the real execution API myself); a hand-authored Report Builder JSON blob can't be
  visually confirmed without browser access, which this environment doesn't have.
- The due/overdue report filters on `due_date`, not `status`, because **`status`'s
  `Due` option is never set by any code path in this system** — the spec only ever
  defines `Scheduled` → `Overdue` (the daily job) and `Scheduled`/`existing` →
  `Completed` (execution submit); nothing transitions to `Due`. Building a
  status-based report would also have shown **zero rows** in the current demo data
  regardless: the daily job is disabled by default (per spec) and every currently
  due-or-overdue schedule still shows `status = "Scheduled"`.

### Verified against real data, not just technically present
```
Due and Overdue PM Schedules:        531 rows  (frappe.desk.query_report.run)
Open Tickets by Outlet and Technician: 1 row   (frappe.desk.query_report.run)
```
Ran both through `frappe.desk.query_report.run(...)` — the exact backend function the
desk UI's report view calls — not just the raw SQL, so column labels, Link-field
handling, and permission checks are all exercised for real. Confirmed both reports
are correctly linked to their `ref_doctype` and not disabled
(`frappe.get_all("Report", filters={"ref_doctype": ...})`), which is what makes them
appear in that doctype's native list-view "Switch To Report" dropdown — the
discovery path a reviewer would actually use, not something requiring a bookmark or
direct URL.

**531 is a large number because of how Phase 5 seeded demo data, not a report bug**:
almost every schedule was seeded with `due_date = today` (`2026-09-01`), so almost
all of them are "due today" simultaneously — a real production system's due dates
would be spread across the calendar. All 531 currently show `status = "Scheduled"`
(none `Overdue`) since nothing in the persisted data has a `due_date` before today —
confirmed by checking directly rather than assuming; didn't artificially backdate
anything just to show an `Overdue` row in the demo, since that would be inventing
data to make a screenshot look better.

Full test suite re-run after adding both reports: **10/10 still passing**. Site up,
`bench start` stable throughout.

### Post-Phase-6 fix #1: PM Program (and Ticket Taxonomy) columns showed raw hashes
Falendra confirmed via screenshot: `Due and Overdue PM Schedules`' PM Program column
showed the raw hash (`dtnj60ort6`), not the readable name, despite `CB PM Program`
having `title_field`/`show_title_field_in_link` set. Root cause, confirmed by reading
the frontend's report-rendering code (`get_linked_doctypes()` in
`query_report.js` — only used for the opt-in "add column" feature, not automatic
rendering): a Query Report's SQL just returns whatever a column selects; the
Link-widget title-resolution machinery (`get_link_title`) never runs on a report
grid at all. Also affected `Open Tickets by Outlet and Technician`'s Taxonomy column
for the identical reason. Fixed both: `LEFT JOIN`ed the target doctype in the SQL and
selected its readable field directly (`CB PM Program.program_name`,
`CB Ticket Taxonomy.taxonomy_label`), changing those columns' `fieldtype` from `Link`
to `Data` (a `Link`-typed column holding a label instead of the real docname would
route to the wrong place if clicked). `source_pm_execution` in the ticket report was
deliberately left as a raw-hash `Link` — `CB PM Execution` has no `title_field` by
design (Phase 2), so there's no better label to substitute. Logged in
`docs/ASSUMPTIONS.md` directly, per the standing rule.

**That fix silently didn't apply on the first `bench migrate`** — a second, distinct
bug. Standard module JSON for non-`DocType` doctypes (like `Report`) is re-synced
based on comparing the file's declared `modified` timestamp against the database
row's, not a content hash the way `DocType` JSON is (confirmed by reading
`frappe/modules/import_file.py`). Every report JSON in this app used the same
static `"2026-09-01 00:00:00.000000"` `modified` value, which never advanced between
edits, so `bench migrate` kept deciding nothing had changed and skipped re-importing
— confirmed directly by checking the DB's `query` field still held the old SQL after
a "successful" migrate. Fixed by bumping `modified` to `"2026-09-02"` in both report
JSON files; re-migrated, confirmed the DB `query` field actually updated this time.
**Lesson for every future edit to a standard Report/Page JSON in this app**: bump
`modified`, or the edit silently won't take effect — logged in `docs/ASSUMPTIONS.md`.

Re-verified through `frappe.desk.query_report.run(...)` (the real API, not just
re-reading the SQL) after both fixes:
```
Due and Overdue PM Schedules → pm_program: "Air Conditioner - Clean Filter - Monthly"  (was: dtnj60ort6)
Open Tickets by Outlet and Technician → ticket_taxonomy: "Maintenance / Preventive Maintenance / PM Failure"  (was: lmq3mr39el)
```

### Post-Phase-6 fix #2: a latent test bug, exposed by the sandbox's clock advancing
Re-running the full suite after the report fix, `test_2_outlet_level_program_applies_
to_every_active_outlet` failed (`AssertionError: 2 != 1`) — a test that had passed
consistently through every prior phase. Root cause had nothing to do with the report
fix: the sandbox's date advanced overnight (`2026-09-01` → `2026-09-02`, per the
session's own date notice), exposing a latent issue in
`test_pm_schedule_applicability.py`. Both `test_1` and `test_2` create an active PM
Program, *then* insert new Outlets/Assets — each insert fires `after_insert`
(`schedule_new_outlet`/`schedule_new_asset`), which calls `ensure_schedule(...,
today())` immediately. Both tests *also* separately called `ensure_schedule(...,
"2026-09-01")` (a hardcoded literal) shortly after. For the entire project so far,
`today()` genuinely equaled `"2026-09-01"` in this sandbox, so both calls produced
the *same* `generation_key` and `ensure_schedule`'s idempotency silently absorbed the
second call — an untested coincidence, not a verified property. Once `today()`
became `"2026-09-02"`, the two calls diverged, producing 2 distinct schedule rows for
each new outlet/asset instead of 1. `test_1` has the identical redundant-schedule
issue but never asserts an exact count for the affected asset, so it stayed green;
`test_2` does assert an exact count, so it caught it. Fixed by replacing every
hardcoded `"2026-09-01"` in `test_pm_schedule_applicability.py` with
`frappe.utils.today()`, so the explicit `ensure_schedule` calls are now genuinely
(not coincidentally) idempotent against whatever the `after_insert` hooks already
did. Audited the other 3 test files for the same pattern (create-new-target
after-an-active-program, then explicit `ensure_schedule` with a hardcoded date) —
none of them have it: they either use hardcoded dates that are deliberately
*distinct* from `today()` for test isolation (a different, correct use of hardcoded
dates), or only assert existence/membership, not exact counts, so a redundant row
wouldn't be visible even if one existed. Full suite: **10/10 passing**, confirmed
stable regardless of which real day it's run on.

## Post-Phase-6: Spare-part suggestion (deferred from Phase 3, then Phase 5)
ASSIGNMENT.md's chosen "go further" direction is "PM failure → ticket → spare-part
suggestion → technician assignment." The spare-part-suggestion link — `CB Ticket.
suggested_spare_part` and its matching logic, per `docs/DocType_Spec.md` section 9 —
was deferred twice (Phase 3: `CB Spare Part` didn't exist yet; Phase 5: out of that
phase's scope) and never circled back to. Implemented now, before Phase 7.

### What was created
- **`CB Ticket.suggested_spare_part`** (Link → CB Spare Part), added at the field
  position the spec's own table already specifies (between `source_pm_execution` and
  `resolved_on`). Editable, not read-only — the spec explicitly says the user
  confirms or overrides the suggestion, so it must stay changeable.
- **`california_burrito/utils/spare_parts.py`** — `suggest_spare_part(asset_name,
  ticket_taxonomy_name)`: substring-matches `CB Spare Part.equipment_model` against
  the asset's `model` (or `asset_type` if `model` is blank); if that yields more than
  one candidate, narrows by keyword overlap between the taxonomy's
  category/sub-category text and each candidate's `part_name`; if still tied (or no
  taxonomy given), picks deterministically (sorted by part code). Returns `None` if
  nothing matches or there's no asset to match against. Pure function, no side
  effects — matches the `normalization.py`/`schedule.py` pattern of keeping matching
  logic testable and out of the controller.
- **`CB Ticket.validate()`** calls it, but only recomputes (and overwrites
  `suggested_spare_part`) when the ticket is new or its `asset`/`ticket_taxonomy`
  actually changed since the last save (checked via `get_doc_before_save()`) — not on
  every save. This is what lets a manually confirmed/overridden suggestion survive an
  unrelated edit (e.g. moving the ticket from Open to Assigned) instead of being
  silently reset back to the auto-suggestion each time.
- No `docs/DocType_Spec.md` changes — the implementation matches its section 9
  description faithfully (substring match is a necessary reading of "match... against",
  not a deviation from it: `equipment_model` values are always brand-suffixed, e.g.
  `"Chest Freezer Celfrost"`, so exact equality against a bare asset type or model
  would never match anything). Two implementation-judgment calls the spec left open
  (the exact narrowing/tie-break algorithm; which real ticket to demonstrate it on)
  are logged in `docs/ASSUMPTIONS.md` directly, per the standing rule — not spec
  deviations, just filled-in specifics.

### Confirmed against real data — the exact ASSIGNMENT.md scenario exists
Checked `TKT-00001` first, as asked. It's an Air Conditioner ticket (`AST-00003`,
`model` blank) with the PM-failure taxonomy — resaving it retroactively (to trigger
the new `validate()` logic on an existing record) correctly leaves
`suggested_spare_part` blank: the real Spare Part catalog has no `equipment_model`
containing the literal phrase "Air Conditioner" (AC parts are catalogued under brand
names like `"Dsw Ac Commercial Aircon"` instead). This is a real gap in the catalog,
not a bug — no false-positive guess.

The real data does have a clean, exact equivalent to ASSIGNMENT.md's own illustrative
example ("A ticket says 'Gasket Broken' on a chest freezer. The spare-parts catalog
has a part code for exactly that."):
- Real taxonomy row: `Maintenance / ChestFreezer / "Gasket Broken"`.
- Real spare part: `CF01CF`, `part_name = "Gasket"`, `equipment_model = "Chest
  Freezer Celfrost"` (one of 8 real parts cataloged for that equipment).
- Real asset: `AST-00007`, a Chest Freezer at outlet ADM — one of the 111 assets
  Phase 5 synthesized directly from `Before.xlsx`'s own outlet/asset-type pairs.

Created one new ticket, `TKT-00002`, against these three real records (outlet ADM,
asset `AST-00007`, the real gasket taxonomy) — a genuinely new record (nothing like
it existed before), but everything it *references* is real, imported data, not
fabricated. Confirmed: `suggested_spare_part` was set to `CF01CF` automatically on
insert, with no manual intervention. This is also the first ticket in the system
raised through the *manual* path (a technician directly filing a reactive ticket)
rather than the automatic PM-failure path `TKT-00001` came from — a nice bonus, since
it exercises the other ticket-creation route ASSIGNMENT.md's "reasonable v1" list
names ("Raise a reactive ticket against an asset at a store").

### Tests
`california_burrito/tests/test_spare_part_suggestion.py` — 5 tests, all against real
imported data:
- `test_chest_freezer_gasket_broken_suggests_the_real_gasket_part` — the exact
  ASSIGNMENT.md scenario.
- `test_suggestion_narrows_by_taxonomy_when_equipment_has_several_parts` — without a
  taxonomy hint, any of the 8 real "Chest Freezer Celfrost" parts is an acceptable
  answer (not an error, not nothing); with the gasket-specific taxonomy, it must be
  exactly the gasket.
- `test_no_asset_means_no_suggestion` — an outlet-level ticket (no asset) gets no
  suggestion.
- `test_no_matching_equipment_means_no_suggestion` — `TKT-00001`'s real situation
  (Air Conditioner, no catalog match) reproduced directly against `suggest_spare_part`.
- `test_manual_override_survives_an_unrelated_save` — override the suggestion, save
  for an unrelated reason (status change) → override survives; then change the asset
  (a relevant change) → the suggestion refreshes to match the new asset.

Full suite: **15/15 passing** (10 existing + 5 new). Confirmed no test-data leakage —
`CB Ticket` shows exactly `TKT-00001` and `TKT-00002` afterward, nothing extra. Site
up, `bench start` stable throughout.

### Post-fix: CB Spare Part's dropdown showed raw part codes
Falendra caught it before it needed a screenshot this time: `part_code` alone isn't
identifiable to a human picking manually, and `part_name` alone is ambiguous —
verified exactly 15 spare parts share the literal name "Gasket" across different
equipment models (Chest Freezer, 2/4 Door Chiller, 2/4 Door Freezer, Under Counter
Freezer/Chiller, Back Bar, Visi Cooler — each Celfrost/Trufrost variant its own row).
Applied the exact same pattern as `CB Ticket Taxonomy.taxonomy_label` (Phase 3):
added a hidden, system-generated `part_label` field (`before_save`,
`f"{part_name} — {equipment_model} ({part_code})"`), set `title_field: "part_label"`
and `show_title_field_in_link: 1`, and widened `search_fields` to
`part_code,part_name,equipment_model` so a technician can type "gasket" or "chest
freezer" and find it, not just the exact code. Backfilled all 391 existing rows via
`frappe.db.set_value` (391 rows, deterministic formula — a full `doc.save()` per row
wasn't necessary). Confirmed via `get_link_title()` (not just `get_title()`, per the
Phase 6 lesson):
```
get_link_title("CB Spare Part", "CF01CF")  -> "Gasket — Chest Freezer Celfrost (CF01CF)"
get_link_title("CB Spare Part", "2DC01CF") -> "Gasket — 2 Door Chiller Celfrost (2DC01CF)"
```
Confirms the exact disambiguation this was for — two different "Gasket" parts now
show distinct, identifiable labels. `TKT-00002.suggested_spare_part` re-checked and
still resolves correctly through the same call. Full suite: **15/15 still passing**.
No new `docs/ASSUMPTIONS.md` entry — this applies an already-logged pattern
(Phase 6's `show_title_field_in_link` finding) to a new doctype, not a new judgment
call.

### Post-fix: field description jargon audit
Falendra caught `CB Ticket.suggested_spare_part`'s description still naming internal
field references (`Spare Part.equipment_model`, `asset_type`) instead of plain
end-user language, and asked whether any others were missed. They were — grepped
every `"description"` across all 11 doctypes and found 4 more on **visible** fields
with the same problem, worst being `CB Zonal Office.city`'s, which named `Phase 5`,
`PROGRESS.md`, and the raw source filename `PM_Case_User_Master.csv` directly in a
field tooltip an end user would see while picking a city. Fixed all 5:

| Field | Before | After |
|---|---|---|
| `CB Ticket.suggested_spare_part` | named `Spare Part.equipment_model`/`asset_type` | "Auto-suggested based on the equipment and issue — confirm or pick a different part." |
| `CB Spare Part.equipment_model` | named `CB Asset.model` | "...should match the equipment's model exactly." |
| `CB PM Program.program_name` | named the hidden `Program Key` field + a field-name tuple | "A short, readable name for this program, e.g. ..." |
| `CB Zonal Office.city` | named Phase 5, PROGRESS.md, the raw CSV filename | "The city this zonal office covers. Use COR for the Corporate Office..." |
| `CB PM Schedule.asset` | said "Enforced in `validate()`" | "Required when the PM Program targets a specific Asset Type; leave blank for outlet-level programs." |
| `CB Ticket.asset` | cross-referenced "PM Schedule" by name | "Optional — leave blank when the issue isn't specific to one piece of equipment." |

**Deliberately left alone**: descriptions on **hidden** fields (`program_key`,
`generation_key`, `taxonomy_key`, `taxonomy_label`, `part_label`) — these are never
shown to an end user in the normal form view (only visible via Customize Form to
someone with developer access), so developer-facing implementation language there is
appropriate, not a bug. Flagging this distinction explicitly in case Falendra wants
those cleaned up too. Verified all 6 fixed descriptions live via `frappe.get_meta()`
(not just re-reading the JSON). Full suite: **15/15 still passing**.

## Phase 7 — Deploy
- [ ] Hosted on Frappe Cloud, demo login created
- [ ] README written (what/why/cut/assumptions/AI usage/how to run)
- [ ] Public GitHub repo pushed (app folder only)
- [ ] Hero scenario clicked through on the live site
- Status:
