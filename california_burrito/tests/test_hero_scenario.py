# Copyright (c) 2026, Falendra Bandhe and contributors
# For license information, please see license.txt

"""The hero scenario from docs/DocType_Spec.md: create a new outlet with several
assets (only some matching an existing Program's asset type) -> confirm PM coverage
is correct and partial, not blanket -> execute the matching PM as Failed -> confirm a
Ticket and the next PM Schedule are both created.

This was previously verified once, manually, in Phase 4 via a one-off script
(output captured in PROGRESS.md, script discarded) — never as a standing
`bench run-tests` test. This reproduces the full narrative as one test, using
fresh, disposable asset types so it stays correct regardless of how the real PM
Program catalog grows (it asserts "at least one schedule" for the matching asset
and "none" for the non-matching ones, not an exact count).
"""

import frappe
from frappe.tests import IntegrationTestCase

from california_burrito.utils.recurrence import next_due_date

FIXTURE_ZONAL_OFFICE = "BLR Zonal Office"
HERO_OUTLET_CODE = "T7HERO"
HERO_TECHNICIAN = "T-HERO-TECH-01"


class TestHeroScenario(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def test_new_outlet_partial_coverage_then_failed_execution_creates_ticket_and_next_schedule(self):
		# Two fresh asset types with no PM Program targeting them — guaranteed
		# "non-matching", regardless of how the real catalog (Fryer, Chest Freezer,
		# etc.) evolves.
		for name in ("Test Hero Freezer Type", "Test Hero Fryer Type"):
			if not frappe.db.exists("CB Asset Type", name):
				frappe.get_doc({"doctype": "CB Asset Type", "asset_type_name": name, "active": 1}).insert()

		outlet = frappe.get_doc(
			{
				"doctype": "CB Outlet",
				"outlet_code": HERO_OUTLET_CODE,
				"city": "BLR",
				"zonal_office": FIXTURE_ZONAL_OFFICE,
				"status": "Active",
			}
		).insert()  # CB Outlet.after_insert fires

		ac_asset = frappe.get_doc(
			{"doctype": "CB Asset", "asset_type": "Air Conditioner", "outlet": outlet.name, "status": "Active"}
		).insert()  # CB Asset.after_insert fires -> matching PM Programs get scheduled
		freezer_asset = frappe.get_doc(
			{"doctype": "CB Asset", "asset_type": "Test Hero Freezer Type", "outlet": outlet.name, "status": "Active"}
		).insert()  # no matching Program -> nothing scheduled
		fryer_asset = frappe.get_doc(
			{"doctype": "CB Asset", "asset_type": "Test Hero Fryer Type", "outlet": outlet.name, "status": "Active"}
		).insert()  # no matching Program -> nothing scheduled

		# Partial coverage: the AC asset gets scheduled, the other two correctly don't.
		schedules = frappe.get_all(
			"CB PM Schedule", filters={"outlet": outlet.name, "asset": ["is", "set"]}, fields=["name", "asset"]
		)
		scheduled_assets = {s.asset for s in schedules}
		self.assertIn(ac_asset.name, scheduled_assets)
		self.assertNotIn(freezer_asset.name, scheduled_assets)
		self.assertNotIn(fryer_asset.name, scheduled_assets)

		# Execute one of the AC schedules as Failed.
		ac_schedule_name = [s.name for s in schedules if s.asset == ac_asset.name][0]
		schedule_before = frappe.get_doc("CB PM Schedule", ac_schedule_name)
		program = frappe.get_doc("CB PM Program", schedule_before.pm_program)

		if not frappe.db.exists("CB Technician", HERO_TECHNICIAN):
			frappe.get_doc(
				{
					"doctype": "CB Technician",
					"employee_no": HERO_TECHNICIAN,
					"technician_name": "Test Hero Technician",
					"job_title": "Executive",
					"zonal_office": FIXTURE_ZONAL_OFFICE,
					"active": 1,
				}
			).insert()

		execution = frappe.get_doc(
			{
				"doctype": "CB PM Execution",
				"pm_schedule": ac_schedule_name,
				"performed_by": HERO_TECHNICIAN,
				"completed_on": frappe.utils.today(),
				"result": "Failed",
			}
		).insert()
		execution.submit()
		execution.reload()

		# Atomically: schedule -> Completed, next schedule created, Ticket created,
		# execution.generated_ticket set.
		self.assertEqual(frappe.db.get_value("CB PM Schedule", ac_schedule_name, "status"), "Completed")

		expected_next_due = next_due_date(schedule_before.due_date, program.frequency)
		self.assertTrue(
			frappe.db.exists(
				"CB PM Schedule",
				{
					"pm_program": program.name,
					"outlet": outlet.name,
					"asset": ac_asset.name,
					"due_date": expected_next_due,
				},
			),
			"Expected the next PM Schedule to be created even though this execution failed",
		)

		self.assertTrue(execution.generated_ticket)
		ticket = frappe.get_doc("CB Ticket", execution.generated_ticket)
		self.assertEqual(ticket.outlet, outlet.name)
		self.assertEqual(ticket.asset, ac_asset.name)
		self.assertEqual(ticket.source_pm_execution, execution.name)
		self.assertEqual(ticket.status, "Open")
