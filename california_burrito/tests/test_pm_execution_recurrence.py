# Copyright (c) 2026, Falendra Bandhe and contributors
# For license information, please see license.txt

"""Acceptance tests 4 and 5 from docs/DocType_Spec.md: CB PM Execution.on_submit is
the sole recurrence mechanism, and next_due is computed from the schedule's
due_date, never from the actual completion date — that's what keeps the cadence
fixed instead of drifting when an execution runs late.

Runs against the Phase 1/2 fixture's Outlet (BLR001) and its Air Conditioner asset
(looked up by outlet + asset_type rather than a hardcoded docname), using the
"Air Conditioner / Clean filter / Monthly" PM Program added for Phase 2, plus one
test-only Technician. Each test uses its own due_date so the two tests don't share
a schedule regardless of run order.
"""

import frappe
from frappe.tests import IntegrationTestCase

from california_burrito.utils.schedule import ensure_schedule

FIXTURE_ZONAL_OFFICE = "BLR Zonal Office"
FIXTURE_OUTLET = "BLR001"
FIXTURE_AC_PROGRAM_KEY = "Air Conditioner|Clean filter|Monthly"
TEST_TECHNICIAN = "T-RECURRENCE-01"


class TestPMExecutionRecurrence(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

		program_name = frappe.db.get_value("CB PM Program", {"program_key": FIXTURE_AC_PROGRAM_KEY}, "name")
		self.assertTrue(
			program_name, "Expected the 'Air Conditioner / Clean filter / Monthly' PM Program fixture to exist"
		)
		self.program = program_name

		# Looked up by (outlet, asset_type), not a hardcoded "AST-00001" docname -- see
		# test_pm_schedule_applicability.py's test_1 for why a literal name here is
		# order-dependent on the real import.
		self.ac_asset = frappe.db.get_value(
			"CB Asset", {"outlet": FIXTURE_OUTLET, "asset_type": "Air Conditioner"}, "name"
		)
		self.assertTrue(self.ac_asset, "Expected the Phase 1 fixture's Air Conditioner asset at BLR001 to exist")

		if not frappe.db.exists("CB Technician", TEST_TECHNICIAN):
			frappe.get_doc(
				{
					"doctype": "CB Technician",
					"employee_no": TEST_TECHNICIAN,
					"technician_name": "Test Technician (Recurrence)",
					"job_title": "Executive",
					"zonal_office": FIXTURE_ZONAL_OFFICE,
					"active": 1,
				}
			).insert()
		self.technician = TEST_TECHNICIAN

	def _submit_execution(self, due_date, completed_on, result="Passed"):
		schedule = ensure_schedule(self.program, FIXTURE_OUTLET, self.ac_asset, due_date)
		schedule_name = schedule if isinstance(schedule, str) else schedule.name
		execution = frappe.get_doc(
			{
				"doctype": "CB PM Execution",
				"pm_schedule": schedule_name,
				"performed_by": self.technician,
				"completed_on": completed_on,
				"result": result,
			}
		).insert()
		execution.submit()
		return schedule_name

	def test_4_passed_execution_completes_schedule_and_creates_next(self):
		schedule_name = self._submit_execution(due_date="2026-01-01", completed_on="2026-01-01")

		self.assertEqual(frappe.db.get_value("CB PM Schedule", schedule_name, "status"), "Completed")

		next_schedule_name = frappe.db.get_value(
			"CB PM Schedule",
			{
				"pm_program": self.program,
				"outlet": FIXTURE_OUTLET,
				"asset": self.ac_asset,
				"due_date": "2026-02-01",
			},
			"name",
		)
		self.assertTrue(next_schedule_name, "Expected a Feb 2026 schedule to be created on submit")
		self.assertEqual(frappe.db.get_value("CB PM Schedule", next_schedule_name, "status"), "Scheduled")

	def test_5_late_execution_does_not_drift_next_due_date(self):
		# Submitted a week late (Mar 8, not Mar 1) — the next due date must still be
		# computed from the fixed due_date, not from this completion date.
		self._submit_execution(due_date="2026-03-01", completed_on="2026-03-08")

		self.assertTrue(
			frappe.db.exists(
				"CB PM Schedule",
				{
					"pm_program": self.program,
					"outlet": FIXTURE_OUTLET,
					"asset": self.ac_asset,
					"due_date": "2026-04-01",
				},
			),
			"Expected next due date to be 2026-04-01 (due_date + 1 month)",
		)
		self.assertFalse(
			frappe.db.exists(
				"CB PM Schedule",
				{
					"pm_program": self.program,
					"outlet": FIXTURE_OUTLET,
					"asset": self.ac_asset,
					"due_date": "2026-04-08",
				},
			),
			"Next due date must not drift to completed_on + 1 month (2026-04-08)",
		)
