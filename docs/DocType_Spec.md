# California Burrito Maintenance — DocType Specification

Frozen domain model, 11 DocTypes. Hand this directly to the AI coding agent as the contract —
it should not make domain decisions while generating code.

Import order matters (each step depends on the previous): **Zonal Office → Outlet → Asset Type →
Technician → Asset → PM Program → Ticket Taxonomy → Spare Part → (seed initial PM Schedule rows)**

---

## 1. CB Zonal Office

| Field | Type | Required | Notes |
|---|---|---|---|
| zonal_office_name | Data | Yes | Autoname: `field:zonal_office_name` |
| city | Select | Yes | Options: NCR, BLR, HYD, CHN, PUN, MUM |

No unique constraint beyond name. ~6-7 rows total, static.

---

## 2. CB Outlet

| Field | Type | Required | Notes |
|---|---|---|---|
| outlet_code | Data | Yes | Autoname: `field:outlet_code`. Unique (3-letter code from source file) |
| city | Select | Yes | Same option set as Zonal Office |
| zonal_office | Link → CB Zonal Office | Yes | Derive from `city` on import (one zonal office per city in source data) |
| status | Select | Yes | Options: Active, Inactive. Default: Active |

**Import note:** `PM_Case_Outlets.xlsx` has 133 rows, clean. Direct import.

---

## 3. CB Technician

| Field | Type | Required | Notes |
|---|---|---|---|
| employee_no | Data | Yes | Autoname: `field:employee_no`. Unique |
| technician_name | Data | Yes | |
| job_title | Select | Yes | Options: Executive, Senior Executive, Assistant Manager, Maintenance Incharge, Lead, Maintenance Leader |
| department | Data | No | Default: "Maintenance" |
| email | Data (Email) | No | |
| mobile | Data | No | |
| zonal_office | Link → CB Zonal Office | Yes | Derived from `Home` column in source |
| reports_to | Link → CB Technician | No | Self-referential. Top of hierarchy = blank |
| user | Link → User | No | Optional tie to a Frappe login, for permission scoping |
| active | Check | Yes | Default: 1 |

**Import note — critical:** `Reports to` values in the CSV don't exact-match `Name` values
(`"Sujith H S"` vs actual name `"Sujith Kumar H S"`). Resolve with a two-pass import:
1. Exact match on name → link directly.
2. No exact match → attempt fuzzy match (e.g. token containment or `difflib`), but **do not
   auto-persist below a confidence threshold** — leave `reports_to` blank and log the candidate
   in the import summary for manual confirmation.

---

## 4. CB Asset Type

| Field | Type | Required | Notes |
|---|---|---|---|
| asset_type_name | Data | Yes | Autoname: `field:asset_type_name`. Unique, canonical (e.g. "Air Conditioner") |
| description | Small Text | No | |
| active | Check | Yes | Default: 1 |

**Import note:** Build the canonical list by hand from the alias clusters in `Before.xlsx`
(`AC` / `A/C Plant` / `Aircon Unit` / `Air Conditioner / AC Plant / FCU / AHU` → one canonical
type). Task text is already clean — no similar aliasing problem there.

---

## 5. CB Asset

| Field | Type | Required | Notes |
|---|---|---|---|
| asset_id | Data | Yes | Autoname: naming series, e.g. `AST-.#####` |
| asset_type | Link → CB Asset Type | Yes | |
| outlet | Link → CB Outlet | Yes | |
| model | Data | No | Free text, e.g. "2 Door Chiller Celfrost" — used for spare-part matching |
| status | Select | Yes | Options: Active, Under Repair, Decommissioned. Default: Active |
| installation_date | Date | No | |

**Note:** `Before.xlsx` doesn't give you real asset instances (it's a PM tracker export, not an
asset register) — you'll need to synthesize a reasonable asset list per outlet based on the
asset types that appear, or seed a representative subset. Document this assumption explicitly.

---

## 6. CB PM Program

*The reusable definition: what should happen, and how often. Applicability is derived logically
from `asset_type` — it is NOT scoped to whichever outlets happened to appear in the source Excel.*

| Field | Type | Required | Notes |
|---|---|---|---|
| program_name | Data | Yes | Autoname: `hash` (not user-facing identity — see uniqueness below) |
| asset_type | Link → CB Asset Type | **No** | Blank = outlet-level program (pest control, deep clean). Set = equipment-level |
| task_description | Data | Yes | |
| frequency | Select | Yes | Options: Weekly, Monthly, Quarterly, 6 Monthly, Yearly |
| active | Check | Yes | Default: 1 |

**Logical uniqueness:** `(asset_type, task_description, frequency)` — NOT `program_name`.
Enforce via a computed `Data` field (e.g. `program_key`) with `"unique": 1`, populated in
`before_insert` by concatenating the three values.

**Applicability (this is the part that must not be scoped to the import sample):**
```
asset_type is set   → applies to every active CB Asset where Asset.asset_type == this
asset_type is null  → applies to every active CB Outlet
```
A new store, or a new asset added to any store, must automatically become eligible for the
matching existing PM Programs — see the schedule-generation function under CB PM Schedule.

**Import logic (deterministic, no AI-invented values):**
```
Group Before.xlsx rows by (canonical_asset_type, task)
For each group:
    if all non-blank Freq values agree → create PM Program with that frequency
    if Freq values conflict → do not create; log as ambiguous (empirically: 0 conflicts exist)
    if no Freq value found anywhere in the group → do not create; log as unresolved (37 rows)
```
151 of 188 originally-blank rows resolve via another row in the same group; 37 stay genuinely
unresolved — exclude them from `PM Program` creation, list them in the import summary. Don't
build a review-status workflow for 37 rows.

**Note:** the raw `Before.xlsx` rows are used only to *derive* these Program definitions (task +
frequency per asset type). They are never used to decide which outlets/assets a Program applies
to — that's computed fresh from `CB Asset` / `CB Outlet` at generation time, so it automatically
covers all 133 outlets, not just the 10 that happened to appear in the sample.

---

## 7. CB PM Schedule

*A concrete obligation: this occurrence, at this outlet, is due on this date.*

| Field | Type | Required | Notes |
|---|---|---|---|
| pm_program | Link → CB PM Program | Yes | |
| outlet | Link → CB Outlet | Yes | |
| asset | Link → CB Asset | Conditional | **Required if `pm_program.asset_type` is set; must be blank if it isn't.** Enforce in `validate()`. |
| due_date | Date | Yes | |
| status | Select | Yes | Options: Scheduled, Due, Overdue, Completed, Cancelled. Default: Scheduled |
| generation_key | Data | Yes | Computed in `before_insert`: `f"{pm_program}|{outlet}|{asset or ''}|{due_date}"`. `"unique": 1` |

**Validation:** if `asset` is set, `asset.outlet` must equal `schedule.outlet` — catches
cross-outlet data-entry mistakes early.

**Idempotency:** Frappe has no native compound-field unique constraint, so uniqueness is
enforced on the single `generation_key` field above, not declared as a tuple.

**The one schedule-generation function — used for both seeding and reconciliation, never
duplicated under a different name:**
```python
def ensure_schedule(program, outlet, asset, due_date):
    key = build_generation_key(program, outlet, asset, due_date)
    try:
        return frappe.get_doc({
            "doctype": "CB PM Schedule", "pm_program": program,
            "outlet": outlet, "asset": asset, "due_date": due_date,
            "status": "Scheduled", "generation_key": key,
        }).insert()
    except frappe.UniqueValidationError:
        # concurrent insert already created it — the DB-level unique constraint on
        # generation_key is the actual protection here, not the pre-check
        return frappe.db.get_value("CB PM Schedule", {"generation_key": key}, "name")

def find_applicable_targets(program):
    if program.asset_type:
        return [(a.outlet, a.name) for a in frappe.get_all(
            "CB Asset", filters={"asset_type": program.asset_type, "status": "Active"},
            fields=["outlet", "name"])]
    return [(o.name, None) for o in frappe.get_all(
        "CB Outlet", filters={"status": "Active"}, fields=["name"])]
```
**Triggers (same functions, called from three places):**
- On import / initial setup: for each `PM Program`, `find_applicable_targets` → `ensure_schedule`
  with `due_date` = today (or a sensible first-due date).
- On `CB Asset.after_insert`: find Programs matching this asset's `asset_type`, `ensure_schedule`
  for this one asset.
- On `CB Outlet.after_insert`: find Programs with `asset_type` null, `ensure_schedule` for this
  one outlet.
- On `PM Execution.on_submit`: `ensure_schedule` for the *same* target, one occurrence forward
  (see CB PM Execution below). This is the only mechanism that creates *future* occurrences —
  there is deliberately no 3-month horizon generator.

**Overdue is terminal until executed** — an overdue schedule does not itself spawn the next
occurrence. Only a submitted `PM Execution` advances recurrence. This is a stated design
assumption (obligation-based, not calendar-generation) — note it in the README.

**Daily scheduled job — its only job:**
```
CB PM Schedule where due_date < today and status in (Scheduled, Due) → set status = Overdue
```
Nothing else. The core PM loop works correctly with this job disabled — useful for demoing
without depending on background workers firing on schedule.

**Indexes:** `(outlet, status, due_date)`, `(asset, status)` — Frappe auto-indexes Link fields,
these composite indexes support the due/overdue report views specifically.

---

## 8. CB PM Execution

*What actually happened. Submittable doctype — locks the record, gives you a clean `on_submit` hook.*

| Field | Type | Required | Notes |
|---|---|---|---|
| pm_schedule | Link → CB PM Schedule | Yes | |
| performed_by | Link → CB Technician | Yes | |
| completed_on | Date | Yes | Default: today |
| result | Select | Yes | Options: Passed, Failed, Skipped |
| notes | Small Text | No | |
| generated_ticket | Link → CB Ticket | No | Auto-set if `result = Failed` and a ticket is created |

**`on_submit` hook (the core recurrence mechanism — no separate scheduling engine needed):**
```
1. Validate the linked PM Schedule isn't already Completed (guards against double-submit races).
2. Set linked PM Schedule.status = "Completed"
3. next_due = linked_schedule.due_date + pm_program.frequency   # NOT completed_on + frequency —
   using the fixed due_date (not the actual completion date) prevents cadence drift when
   executions run late.
4. ensure_schedule(pm_program, outlet, asset, next_due)
   — do this regardless of Passed/Failed; a failed inspection doesn't kill the recurring program.
5. If result == "Failed":
     Create CB Ticket, pre-filled with outlet, asset, source_pm_execution = this document
     Set this.generated_ticket to the new ticket
All of the above in one transaction.
```

---

## 9. CB Ticket

| Field | Type | Required | Notes |
|---|---|---|---|
| outlet | Link → CB Outlet | Yes | |
| asset | Link → CB Asset | No | Optional — same reasoning as PM Schedule |
| ticket_taxonomy | Link → CB Ticket Taxonomy | Yes | See doctype 11 |
| description | Small Text | No | |
| priority | Select | Yes | Options: Low, Medium, High. Default: Medium |
| status | Select | Yes | Options: Open, Assigned, In Progress, Resolved, Closed, Cancelled. Default: Open |
| assigned_to | Link → CB Technician | No | |
| source_pm_execution | Link → CB PM Execution | No | Set automatically when raised from a failed PM |
| suggested_spare_part | Link → CB Spare Part | No | Auto-suggested (see below) |
| resolved_on | Date | No | |

**Not submittable** — status needs to move backward (reopen) as well as forward, which the
submit/cancel/amend model doesn't fit well. Use plain status field + role-based permissions.

**Spare-part suggestion logic (simple lookup, not a recommendation engine):**
```
match Spare Part.equipment_model against Asset.model (or Asset.asset_type if model is blank)
AND Spare Part context implied by ticket_taxonomy.category / sub_category text
→ suggest the matching part_code, let the user confirm/override
```

**Indexes:** `(outlet, status)`, `(assigned_to, status)`.

---

## 10. CB Spare Part

| Field | Type | Required | Notes |
|---|---|---|---|
| part_code | Data | Yes | Autoname: `field:part_code`. Unique (e.g. "2DC01CF") |
| part_name | Data | Yes | e.g. "Gasket" |
| equipment_model | Data | Yes | e.g. "2 Door Chiller Celfrost" — matches Asset.model |
| active | Check | Yes | Default: 1 |

**Import note:** parsed directly from the `Spare Parts` department rows in
`PM_Case_Ticket_Buckets.xlsx` — the part code is embedded in the `Sub Category 1` text
(e.g. `"2DC01CF Gasket"`), split it into `part_code` + `part_name` on import.

---

## 11. CB Ticket Taxonomy

| Field | Type | Required | Notes |
|---|---|---|---|
| department | Data | Yes | |
| category | Data | Yes | |
| sub_category_1 | Data | No | |
| sub_category_2 | Data | No | |

**Unique constraint:** `(department, category, sub_category_1, sub_category_2)`.

**Import note:** import the 844 rows of `PM_Case_Ticket_Buckets.xlsx` as-is — each row is
already a valid combination, so you get "category belongs to department" enforcement for free,
with no cascading-filter logic to write. No separate Department/Category/Subcategory doctypes.

---

## Relationship summary

```
Zonal Office 1──N Outlet
Outlet 1──N Asset
Asset Type 1──N Asset
Asset Type 1──N PM Program (optional — blank for outlet-level programs)
PM Program 1──N PM Schedule
Outlet 1──N PM Schedule          Asset 0..1──N PM Schedule
PM Schedule 1──N PM Execution
Outlet 1──N Ticket               Asset 0..1──N Ticket
PM Execution 0..1──N Ticket (source_pm_execution)
Technician 1──N Ticket (assigned_to)
Technician 0..1──N Technician (reports_to, self-referential)
Asset Type 1──N Spare Part (loosely, via equipment_model text match)
Ticket Taxonomy 1──N Ticket
```

## Acceptance tests

Write these as actual Frappe tests before considering any phase done — they're the operational
definition of "the architecture works," not optional polish.

| # | Scenario | Expected result |
|---|---|---|
| 1 | Program (AC, Clean filter, Monthly) + Assets AC-001, AC-002, Freezer-001 | Schedules created for AC-001, AC-002 only — not Freezer-001 |
| 2 | Program (null asset_type, Pest Control, Monthly) + Outlets BLR001, BLR002, HYD001 | 3 schedules, one per outlet |
| 3 | Create new Asset AC-003 (matching an existing Program's asset_type) | Matching schedule auto-created via `after_insert` |
| 4 | Schedule due Sep 1 → Execution Sep 1, Passed | Sep schedule → Completed; Oct schedule → Scheduled |
| 5 | Schedule due Sep 1 → Execution submitted Sep 8 | Next due date is Oct 1, not Oct 8 (fixed cadence, not drift) |
| 6 | Execution submitted with Result = Failed | Atomically: schedule → Completed, next schedule created, Ticket created, `execution.generated_ticket` set |
| 7 | Submit the same PM Execution twice | Second submission rejected |
| 8 | Schedule.outlet = BLR001, Schedule.asset belongs to HYD001 | Validation error on save |

**The hero scenario — this is the one to actually demo:** create a new Outlet (BLR-134) with
Assets AC-134, Freezer-134, Fryer-134. The system should automatically produce a schedule for
AC-134 under the existing "Clean filter" Program, but nothing for Freezer-134/Fryer-134 unless a
matching Program exists for their types. Then execute the AC-134 PM as Failed → confirm a Ticket
and the next PM Schedule are both created. This single walkthrough demonstrates applicability,
idempotent generation, execution-driven recurrence, and the PM→ticket link end to end.

## Build sequence (don't import real data first)

1. One Outlet, two Assets, one Asset Type, one PM Program, by hand. Prove `Program → Schedule →
   Execution → next Schedule` works (tests 1, 4, 5).
2. Add the Failed → Ticket path (test 6).
3. Add the new-Asset reconciliation hook (test 3).
4. Only then run the real 133-outlet import (Phase 4/5) — by this point the domain logic is
   already proven on a small fixture set, so import bugs are isolated to normalization/mapping,
   not tangled up with untested business logic.

This ordering exists specifically to avoid the failure mode where 11 DocTypes, real data, hooks,
and workflows all break at once and an AI coding agent spends hours chasing secondary errors
instead of the one real bug.

- Separate `Maintenance Task` doctype — collapsed into `PM Program.task_description`.
- Separate `Department` / `Category` / `Subcategory` doctypes — collapsed into one
  `Ticket Taxonomy` doctype, imported flat.
- A 90-day rolling-horizon schedule generator — replaced with execution-driven "create next
  occurrence on submit," which needs no generator loop at all.
- Manual-review workflow for unresolved frequencies — 37 rows, logged in the import summary,
  not modeled as a status.
- Spare-part recommendation engine — simple text match + user confirmation.
- Any of: microservices, Kafka, Kubernetes, event sourcing, CQRS, custom RBAC/scheduler/admin UI.
