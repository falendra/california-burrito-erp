# Copyright (c) 2026, Falendra Bandhe and contributors
# For license information, please see license.txt

"""Reproducible demo/fixture data: the Phase 1 fixture, the Phase 4 hero
scenario, and the manual chest-freezer-gasket ticket (TKT-00002) -- all of
which, until now, only ever existed as ad hoc console scripts, created by hand
and discarded (documented step by step in PROGRESS.md, but never committed as
code). This is the one script that reproduces all of it on a fresh site.

Run via:
    bench --site <site> execute california_burrito.utils.seed_demo.run

Deploy sequence:
    fresh site -> install app -> import_data.run() -> seed_demo.run()

Must run AFTER import_data.py: the manual demo ticket references real
imported data (CB Outlet "ADM", CB Asset Type "Chest Freezer", the
"Maintenance / ChestFreezer / Gasket Broken" ticket taxonomy row) and throws a
clear error rather than silently fabricating any of it if that data isn't
there yet.

Idempotent by construction, same discipline as import_data.py: every insert
here is checked against its natural key first -- or, for CB Ticket (no
natural key), against the exact outlet/asset/description combination. Safe to
re-run on a site that already has this demo data: creates nothing new, just
reuses what's there and reports what it found.

Final step, always: sets the fixture PM Program's active = 0. Baking the
retirement into this script (rather than a one-off manual fix) means it can't
be forgotten on a future re-seed. See docs/ASSUMPTIONS.md category 4 for why
it's deactivated rather than deleted.
"""

import frappe
from frappe.utils import today

from california_burrito.utils.schedule import ensure_schedule

# Phase 2's fixture Program: hand-created before the real Phase 5 import existed, to
# prove Program -> Schedule -> Execution -> next Schedule on fixture data alone.
# program_name/task_description are reproduced byte-for-byte from the original
# (title-case "Filter" in the label, lowercase "filter" in the task -- exactly what
# was typed by hand in Phase 2, left as-is rather than tidied into consistency now
# that it's becoming a committed script).
FIXTURE_PROGRAM = {
	"program_name": "Air Conditioner - Clean Filter - Monthly",
	"asset_type": "Air Conditioner",
	"task_description": "Clean filter",
	"frequency": "Monthly",
}
FIXTURE_PROGRAM_KEY = "Air Conditioner|Clean filter|Monthly"

DEMO_TECHNICIAN = "DEMO-TECH-01"

# Verbatim from the original console session -- kept as the idempotency key for this
# ticket (CB Ticket has no natural key of its own).
CHEST_FREEZER_TICKET_DESCRIPTION = "chest freezer gasket demo"


def _get_or_create_zonal_office(city, name=None):
	name = name or f"{city} Zonal Office"
	if not frappe.db.exists("CB Zonal Office", name):
		frappe.get_doc({"doctype": "CB Zonal Office", "zonal_office_name": name, "city": city}).insert()
	return name


def _get_or_create_asset_type(name):
	if not frappe.db.exists("CB Asset Type", name):
		frappe.get_doc({"doctype": "CB Asset Type", "asset_type_name": name, "active": 1}).insert()
	return name


def _get_or_create_outlet(code, city, zonal_office):
	if not frappe.db.exists("CB Outlet", code):
		frappe.get_doc(
			{
				"doctype": "CB Outlet",
				"outlet_code": code,
				"city": city,
				"zonal_office": zonal_office,
				"status": "Active",
			}
		).insert()  # CB Outlet.after_insert fires -- no-op here, no outlet-level Programs involved
	return code


def _get_or_create_asset(outlet, asset_type, model=None, installation_date=None):
	existing = frappe.db.get_value("CB Asset", {"outlet": outlet, "asset_type": asset_type}, "name")
	if existing:
		return existing
	doc = frappe.get_doc(
		{
			"doctype": "CB Asset",
			"asset_type": asset_type,
			"outlet": outlet,
			"model": model,
			"installation_date": installation_date,
			"status": "Active",
		}
	).insert()  # CB Asset.after_insert fires -- schedules against any already-active matching Program
	return doc.name


def _get_or_create_technician(employee_no, technician_name, job_title, zonal_office):
	if not frappe.db.exists("CB Technician", employee_no):
		frappe.get_doc(
			{
				"doctype": "CB Technician",
				"employee_no": employee_no,
				"technician_name": technician_name,
				"job_title": job_title,
				"department": "Maintenance",
				"zonal_office": zonal_office,
				"active": 1,
			}
		).insert()
	return employee_no


def _get_or_create_fixture_program():
	existing = frappe.db.get_value("CB PM Program", {"program_key": FIXTURE_PROGRAM_KEY}, "name")
	if existing:
		return existing
	return frappe.get_doc({"doctype": "CB PM Program", "active": 1, **FIXTURE_PROGRAM}).insert().name


def _get_or_create_taxonomy(department, category, sub1, sub2=""):
	key = "|".join([department, category, sub1, sub2])
	existing = frappe.db.get_value("CB Ticket Taxonomy", {"taxonomy_key": key}, "name")
	if existing:
		return existing
	return frappe.get_doc(
		{
			"doctype": "CB Ticket Taxonomy",
			"department": department,
			"category": category,
			"sub_category_1": sub1,
			"sub_category_2": sub2,
		}
	).insert().name


def _require(doctype, name, hint):
	if not frappe.db.exists(doctype, name):
		frappe.throw(
			f"{doctype} {name!r} not found -- run california_burrito.utils.import_data.run "
			f"first. {hint}"
		)


def seed_phase1_fixture(program_name, blr_zonal_office):
	"""Phase 1: one outlet, two assets of two different asset types -- the very
	first fixture, used to prove Outlet -> Assets navigation in the desk UI."""
	outlet = _get_or_create_outlet("BLR001", "BLR", blr_zonal_office)
	ac_asset = _get_or_create_asset(
		outlet, "Air Conditioner", model="1.5 Ton Split AC Voltas", installation_date="2024-01-15"
	)
	_get_or_create_asset(outlet, "Walk-in Chiller", model="2 Door Chiller Celfrost", installation_date="2024-01-15")
	# Explicit safety net, not a duplicate of the after_insert hook: if AST-00001
	# already existed (e.g. from import's own asset synthesis) before this script
	# ever created the fixture Program, the hook never had a chance to fire. Guarded
	# on "no schedule at all yet" rather than called unconditionally -- ensure_schedule
	# dedupes on (program, outlet, asset, due_date), and due_date is today(), which is
	# a different value on every calendar day, so an unconditional call here would
	# quietly create a fresh duplicate schedule every time this script is re-run on a
	# later date instead of recognizing the fixture as already seeded.
	if not frappe.db.exists("CB PM Schedule", {"pm_program": program_name, "outlet": outlet, "asset": ac_asset}):
		ensure_schedule(program_name, outlet, ac_asset, today())


def seed_hero_scenario(program_name, blr_zonal_office):
	"""Phase 4: a new outlet with 3 assets -- one matching type with an active
	Program, two non-matching types with none -- proving partial coverage, then
	a Failed execution producing a Ticket (TKT-00001) and the next Schedule.
	This is the one-time manual demonstration; the standing regression test
	(test_hero_scenario.py) reproduces the same narrative with fresh disposable
	asset types on every test run, independent of this fixture."""
	outlet = _get_or_create_outlet("BLR134", "BLR", blr_zonal_office)
	_get_or_create_asset_type("Freezer")
	_get_or_create_asset_type("Fryer")
	ac_asset = _get_or_create_asset(outlet, "Air Conditioner")
	_get_or_create_asset(outlet, "Freezer")
	_get_or_create_asset(outlet, "Fryer")
	technician = _get_or_create_technician(DEMO_TECHNICIAN, "Demo Technician", "Executive", blr_zonal_office)

	# Same guarded safety net as seed_phase1_fixture above -- see the comment there for
	# why this must not call ensure_schedule(..., today()) unconditionally.
	if not frappe.db.exists("CB PM Schedule", {"pm_program": program_name, "outlet": outlet, "asset": ac_asset}):
		ensure_schedule(program_name, outlet, ac_asset, today())

	already_ran = frappe.db.exists(
		"CB PM Schedule", {"pm_program": program_name, "outlet": outlet, "asset": ac_asset, "status": "Completed"}
	)
	if already_ran:
		return

	schedule_name = frappe.db.get_value(
		"CB PM Schedule",
		{"pm_program": program_name, "outlet": outlet, "asset": ac_asset, "status": "Scheduled"},
		"name",
		order_by="due_date asc",
	)
	if not schedule_name:
		frappe.throw(f"Hero scenario: no Scheduled CB PM Schedule found for {ac_asset} under {program_name}")

	execution = frappe.get_doc(
		{
			"doctype": "CB PM Execution",
			"pm_schedule": schedule_name,
			"performed_by": technician,
			"completed_on": today(),
			"result": "Failed",
		}
	).insert()
	execution.submit()  # on_submit: schedule -> Completed, next Schedule created, Ticket raised


def seed_manual_chest_freezer_ticket():
	"""The hand-raised demo ticket (TKT-00002): proves a Ticket can be created
	directly by a person, not just auto-raised from a failed PM execution, and
	exercises suggested_spare_part / assigned_to against real imported data."""
	_require("CB Outlet", "ADM", "This ticket demonstrates a hand-raised report against a real imported outlet.")
	asset = _get_or_create_asset("ADM", "Chest Freezer")
	taxonomy = _get_or_create_taxonomy("Maintenance", "ChestFreezer", "Gasket Broken")

	if frappe.db.exists(
		"CB Ticket", {"outlet": "ADM", "asset": asset, "description": CHEST_FREEZER_TICKET_DESCRIPTION}
	):
		return

	frappe.get_doc(
		{
			"doctype": "CB Ticket",
			"outlet": "ADM",
			"asset": asset,
			"ticket_taxonomy": taxonomy,
			"description": CHEST_FREEZER_TICKET_DESCRIPTION,
		}
	).insert()  # validate() auto-fills suggested_spare_part and assigned_to


def retire_fixture_program(program_name):
	"""Always the final step: the fixture Program has done its job (Phase 2's
	Program -> Schedule -> Execution -> next Schedule proof, Phase 4's hero
	scenario) and now reads as a near-duplicate of the real imported "Air
	Conditioner - Clean Air Filters - Monthly" program to a reviewer skimming
	the list. Deactivating, not deleting: AST-00003's Schedule/Execution and
	TKT-00001 all trace back to it, and `active` only gates *future* schedule
	generation via find_applicable_targets, not existing records."""
	frappe.db.set_value("CB PM Program", program_name, "active", 0)


@frappe.whitelist()
def run():
	frappe.only_for("System Manager")
	frappe.set_user("Administrator")

	blr_zonal_office = _get_or_create_zonal_office("BLR")
	program_name = _get_or_create_fixture_program()

	seed_phase1_fixture(program_name, blr_zonal_office)
	seed_hero_scenario(program_name, blr_zonal_office)
	seed_manual_chest_freezer_ticket()
	retire_fixture_program(program_name)

	frappe.db.commit()
	print("seed_demo: done.")
