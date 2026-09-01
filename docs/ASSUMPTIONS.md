# Assumptions and ambiguity decisions

Compiled from `PROGRESS.md` (Phases 1–5) and `docs/DocType_Spec.md`'s own notes. This
is the reviewable summary — one or two sentences per decision, the ambiguity and the
call, not the investigative narrative. `PROGRESS.md` remains the detailed record of
how each one was found and verified. This file is what `README.md`'s assumptions
section (Phase 7) will point to.

From Phase 6 onward, per `CLAUDE.md`, any new assumption or ambiguity call gets added
here directly, not just narrated in `PROGRESS.md`.

---

## 1. Data ambiguity resolved by assumption

- **The spec's stated 151/37 PM-frequency split doesn't match its own documented
  algorithm.** `docs/DocType_Spec.md` says to group by `(canonical_asset_type, task)`,
  but 151/37 is what you get grouping by the *raw, uncanonicalized* asset string
  instead. Followed the documented algorithm literally against the real file: **176
  resolved / 12 unresolved / 0 conflicts** (176+12=188, matches the total blank count
  exactly). Used the real number, not the spec's illustrative one.
- **12 genuinely unresolved PM Program groups** — no frequency anywhere in the group,
  so excluded from PM Program creation rather than guessed: `Ice Cube Machine /
  "Sanitize Water System & Ice Storage Bin"` (1 row), `Chest Freezer / "Clean
  Condenser"` (10 rows), `Air Conditioner / "Clean Air filter"` (1 row — a
  near-duplicate of `"Clean Air Filters"` that the spec's own "task text is already
  clean" note correctly stops from being merged).
- **Two Ticket Taxonomy rows excluded**: one exact duplicate after whitespace
  stripping (`Maintenance / PestoFlash / "Light Not Working"` appears twice), and one
  row with blank department/category (`Snags`, everything else empty) — `category` is
  required and there's nothing to fill it with.
- **Sanju V P / `COR` zonal office.** One technician's `Home` value, `"COR"`
  (Corporate Office), wasn't a covered `CB Zonal Office.city` option, so the first
  import pass excluded him rather than guess a city. Corrected: `"COR"` is a real
  value in the source file, not invented data, so the schema was extended (`COR`
  added as a Select option) instead of dropping the person. His own manager,
  `"Ashwith Shetty"`, never appears as an employee row at all and stays unresolved —
  a genuine gap, not something to paper over.
- **Fuzzy-match confidence threshold for `reports_to`** — token containment (unique
  candidate only) first, then a `difflib` ratio requiring both a 0.75 floor and a 0.1
  margin over the runner-up, chosen empirically from the real score spread (0.77/0.81
  for accepted matches vs. 0.67/0.40 for correctly-rejected ones). 4 of 41
  `reports_to` values are left blank and logged rather than guessed below that bar.
- **Frequency string aliasing**: `Qtrly` → `Quarterly`, `6 month` → `6 Monthly`;
  `Weekly`/`Monthly`/`Yearly` pass through unchanged.
- **Asset Type canonicalization** — 19 raw `Before.xlsx` values clustered into 12
  canonical types (one obvious source typo fixed: `Tortila Press` → `Tortilla
  Press`). Per the spec's own "task text is already clean" note, task strings were
  never fuzzy-merged, even where a near-duplicate looked tempting.

## 2. Domain modeling choices

- **`asset` is optional on `CB PM Schedule` and `CB Ticket`** — required exactly when
  the linked PM Program has an `asset_type` (equipment-level), must be blank
  otherwise (outlet-level). Cross-outlet validation: an asset's own `outlet` must
  match the schedule/ticket's outlet.
- **Execution-driven recurrence, not calendar generation.** `CB PM Execution.on_submit`
  is the only mechanism that creates the next `CB PM Schedule` — no rolling-horizon
  generator. An overdue schedule doesn't spawn its own successor; only a submitted
  execution advances the chain.
- **Fixed cadence from `due_date`, never `completed_on`** — next due date is always
  `schedule.due_date + frequency`, so a late execution doesn't drift the whole
  program's cadence forward.
- **`CB Ticket` is not submittable; `CB PM Execution` is** — a ticket's status needs
  to move backward (reopen), which doesn't fit the submit/cancel/amend model; an
  execution is a clean, audit-trail-style record that should lock once submitted.
- **Autoname choices the spec left silent on**: `hash` for `CB PM Program` (later
  given a `title_field`), `hash` for `CB PM Schedule`/`CB PM Execution` (no
  `title_field` — neither has one field that reads as a genuine label, and adding one
  would be purely cosmetic), `hash` for `CB Ticket Taxonomy` (given a computed
  `taxonomy_label` `title_field` once its Link-dropdown UX cost turned out to
  matter), naming series `TKT-.#####` for `CB Ticket` (tickets are human-referenced
  constantly, unlike the other four), `field:part_code` for `CB Spare Part` (already
  human-readable, per spec).
- **`show_title_field_in_link` must be set alongside `title_field`** for a Link field
  *elsewhere* to show the readable label instead of the raw docname — a separate
  DocType property, easy to miss (missed it twice, on `CB PM Program` and `CB Ticket
  Taxonomy`, before catching the pattern).
- **Compound uniqueness via computed hidden `Data` fields** (`program_key`,
  `generation_key`, `taxonomy_key`) — Frappe has no native compound-unique
  constraint, so each is built from its natural key's parts in `before_insert`.
- **Composite indexes via `on_doctype_update()` + `frappe.db.add_index()`** — DocType
  JSON has no way to declare a multi-column index directly.
- **PM-failure ticket taxonomy.** The spec's `on_submit` pseudocode doesn't say what
  `ticket_taxonomy` (required) a system-generated ticket should get. Picked a
  reasonable label (`Maintenance / Preventive Maintenance / PM Failure`) by reasoning
  about the domain, before the real taxonomy import existed — a PM failure isn't the
  same kind of thing as a hand-raised issue against one of the real categories. The
  real import later turned out to contain a row with those exact same four values;
  confirmed permanent, not a placeholder to revisit.
- **`CB PM Schedule.status`'s `Due` option is never actually set by any code path.**
  The spec defines the daily job as flipping `Scheduled`/`Due` → `Overdue`, but no
  mechanism anywhere transitions `Scheduled` → `Due` in the first place — it's a
  defined Select option nothing ever populates. Rather than build an un-asked-for
  mechanism to set it (out of scope — CLAUDE.md rules out any scheduler beyond the
  single daily job), the Phase 6 "Due and Overdue" report filters directly on
  `due_date <= today` (excluding `Completed`/`Cancelled`), independent of the status
  field — which also makes it correct regardless of whether the daily job has ever
  run (it's disabled by default).
- **Phase 6 reports built as Query Reports (SQL), not Report Builder saved filters.**
  A due/overdue view needs a date-relative condition (`due_date <= CURDATE()`), which
  a Report Builder's saved filter can't express (it stores literal values, evaluated
  once at save time, not a live expression). A Query Report's SQL is still a native,
  standard Frappe report type — not custom dashboard code — and its correctness is
  directly verifiable (ran the SQL and the actual `frappe.desk.query_report.run` API
  against real data before considering it done), unlike a hand-authored Report
  Builder JSON blob, which can't be visually verified without browser access.
- **A Query Report's Link-type columns don't auto-resolve `title_field`/
  `show_title_field_in_link`.** Those two properties only affect Link *field widgets*
  (forms, dropdowns, standard list views) — a Query Report's SQL returns whatever a
  column selects, with no automatic title lookup, confirmed by inspecting the
  frontend's report-rendering code and by a real screenshot showing the raw hash.
  Fixed by joining the target doctype in the SQL and selecting its readable field
  directly (`CB PM Program.program_name`, `CB Ticket Taxonomy.taxonomy_label`)
  instead of the raw Link value, with that column's `fieldtype` changed to `Data`
  accordingly (a `Link`-typed column showing a label instead of the real docname
  would route incorrectly if clicked).
- **Editing a standard module `Report`'s JSON doesn't take effect on `bench migrate`
  unless its `modified` timestamp is bumped past what's in the database** — unlike
  DocType JSON, which is re-synced based on a content hash regardless of the
  `modified` field. Every standard Report/Page-type JSON file in this app needs its
  `modified` field advanced on every real edit going forward, or `bench migrate` will
  silently skip the change (confirmed by reading `frappe/modules/import_file.py`'s
  sync logic, after a fix silently failed to apply on the first attempt).

## 3. Scope deliberately cut

Copied from `docs/DocType_Spec.md`'s own "not built" list, which remains the
authoritative version:

- Separate `Maintenance Task` doctype — collapsed into `PM Program.task_description`.
- Separate `Department` / `Category` / `Subcategory` doctypes — collapsed into one
  `Ticket Taxonomy` doctype, imported flat.
- A 90-day rolling-horizon schedule generator — replaced with execution-driven
  "create next occurrence on submit," which needs no generator loop at all.
- Manual-review workflow for unresolved frequencies — logged in the import summary,
  not modeled as a status.
- Spare-part recommendation engine — simple text match + user confirmation only
  (and, as of Phase 5, not yet wired up at all: `CB Ticket.suggested_spare_part`
  isn't in the schema yet either, deferred alongside it).
- Any of: microservices, Kafka, Kubernetes, event sourcing, CQRS, custom
  RBAC/scheduler/admin UI.

Also from `CLAUDE.md`'s hard rules:

- Any scheduler beyond the single daily job that flips `Scheduled`/`Due` → `Overdue`.
- Dashboards beyond native Frappe list/report views.

## 4. Data synthesized, not imported

Everything in this section is demo/fixture data, deliberately built to prove the
system works before or alongside the real import — **none of it is derived from
`data/source/`**, and it's called out explicitly here so it's never mistaken for
imported data later.

- **Phase 1 fixture**: `CB Zonal Office` "BLR Zonal Office", `CB Outlet` "BLR001",
  `CB Asset Type` "Air Conditioner"/"Walk-in Chiller", `CB Asset` `AST-00001`/
  `AST-00002` with hand-picked `model` values — built by hand to prove
  Program → Schedule → Execution → next Schedule before any real data existed.
- **Phase 2 fixture**: one `CB PM Program` ("Air Conditioner / Clean filter /
  Monthly") — hand-created before the real import; its task text was deliberately
  distinct enough not to collide with the real "Clean Air Filters" program derived
  in Phase 5.
- **Phase 4 hero-scenario data** (persistent, not a rolled-back test): `CB Asset Type`
  "Freezer" and "Fryer" (invented before the real import — "Freezer" has no real
  counterpart; the real canonical type turned out to be "Chest Freezer", so the two
  now coexist as separate types), `CB Outlet` "BLR134", `CB Asset` `AST-00003`/
  `AST-00004`/`AST-00005`, and `CB Ticket` `TKT-00001` from a full failed-PM-to-ticket
  walkthrough.
- **`DEMO-TECH-01`** — a `CB Technician` created solely to perform the hero-scenario
  execution; not from any import.
- **The 111 `CB Asset` rows synthesized in Phase 5** sit in a middle ground worth
  naming precisely: each one *is* directly evidenced by a real `(outlet, asset type)`
  pair actually appearing in `Before.xlsx`'s own rows — not invented from nothing —
  but `Before.xlsx` is a PM tracker export, not an asset register, so "one
  representative asset per pair, at the 10 outlets that file happens to track" is
  still a synthesis decision, not a real inventory count. The other 123 real outlets
  got zero synthesized assets from this phase.
