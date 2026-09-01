# Copyright (c) 2026, Falendra Bandhe and contributors
# For license information, please see license.txt

"""PM schedule generation: the one place CB PM Schedule documents get created.

docs/DocType_Spec.md section 7 is the contract this file implements verbatim —
`ensure_schedule` is the ONLY function that creates a CB PM Schedule, and
`find_applicable_targets` computes applicability fresh from the live CB Asset /
CB Outlet tables, never from whatever outlets happened to appear in the import
sample. A new Asset or Outlet becomes eligible the moment it exists.
"""

import frappe
from frappe.utils import getdate


def build_generation_key(program, outlet, asset, due_date):
	return f"{program}|{outlet}|{asset or ''}|{getdate(due_date)}"


def ensure_schedule(program, outlet, asset, due_date):
	"""Idempotently create the CB PM Schedule for (program, outlet, asset, due_date).

	Called from exactly four places: initial seeding, CB Asset.after_insert,
	CB Outlet.after_insert, and CB PM Execution.on_submit. Never duplicate this
	logic inline anywhere else.
	"""
	due_date = getdate(due_date)
	key = build_generation_key(program, outlet, asset, due_date)
	try:
		return frappe.get_doc(
			{
				"doctype": "CB PM Schedule",
				"pm_program": program,
				"outlet": outlet,
				"asset": asset,
				"due_date": due_date,
				"status": "Scheduled",
				"generation_key": key,
			}
		).insert()
	except frappe.UniqueValidationError:
		# Concurrent insert already created it — the DB-level unique constraint on
		# generation_key is the actual protection here, not this pre-check.
		return frappe.db.get_value("CB PM Schedule", {"generation_key": key}, "name")


def find_applicable_targets(program):
	"""Return [(outlet, asset), ...] a PM Program currently applies to.

	`program` is a CB PM Program document (or anything with an `.asset_type`
	attribute — frappe.get_doc(...) results both qualify). Computed fresh from
	CB Asset / CB Outlet at call time — this is what makes a new store or a new
	asset automatically eligible for existing programs, with no re-entry per store.
	"""
	if program.asset_type:
		return [
			(a.outlet, a.name)
			for a in frappe.get_all(
				"CB Asset",
				filters={"asset_type": program.asset_type, "status": "Active"},
				fields=["outlet", "name"],
			)
		]
	return [
		(o.name, None)
		for o in frappe.get_all("CB Outlet", filters={"status": "Active"}, fields=["name"])
	]
