# Copyright (c) 2026, Falendra Bandhe and contributors
# For license information, please see license.txt

"""Acceptance tests 6, 7, and 8 from docs/DocType_Spec.md.

Test 6 (Failed execution -> Ticket, atomically) and 7 (duplicate submit rejected)
run against the persistent Phase 1/2 fixture (BLR001, AST-00001, the AC/Clean-filter/
Monthly Program), each with its own due_date. Test 8 (cross-outlet asset validation)
needs a second outlet, so it creates one.
"""

import frappe
from frappe.tests import IntegrationTestCase

from california_burrito.utils.schedule import ensure_schedule

FIXTURE_ZONAL_OFFICE = "BLR Zonal Office"
FIXTURE_OUTLET = "BLR001"
FIXTURE_AC_ASSET = "AST-00001"
FIXTURE_AC_PROGRAM_KEY = "Air Conditioner|Clean filter|Monthly"
TEST_TECHNICIAN = "T-TICKET-01"


class TestPMTicketWorkflow(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

		program_name = frappe.db.get_value("CB PM Program", {"program_key": FIXTURE_AC_PROGRAM_KEY}, "name")
		self.assertTrue(
			program_name, "Expected the 'Air Conditioner / Clean filter / Monthly' PM Program fixture to exist"
		)
		self.program = program_name

		if not frappe.db.exists("CB Technician", TEST_TECHNICIAN):
			frappe.get_doc(
				{
					"doctype": "CB Technician",
					"employee_no": TEST_TECHNICIAN,
					"technician_name": "Test Technician (Ticket workflow)",
					"job_title": "Executive",
					"zonal_office": FIXTURE_ZONAL_OFFICE,
					"active": 1,
				}
			).insert()
		self.technician = TEST_TECHNICIAN

	def _new_execution(self, due_date, completed_on, result):
		schedule = ensure_schedule(self.program, FIXTURE_OUTLET, FIXTURE_AC_ASSET, due_date)
		schedule_name = schedule if isinstance(schedule, str) else schedule.name
		return schedule_name, frappe.get_doc(
			{
				"doctype": "CB PM Execution",
				"pm_schedule": schedule_name,
				"performed_by": self.technician,
				"completed_on": completed_on,
				"result": result,
			}
		).insert()

	def test_6_failed_execution_creates_ticket_atomically(self):
		schedule_name, execution = self._new_execution(
			due_date="2026-05-01", completed_on="2026-05-01", result="Failed"
		)
		execution.submit()
		execution.reload()

		# Atomically: schedule -> Completed, next schedule created, Ticket created,
		# execution.generated_ticket set.
		self.assertEqual(frappe.db.get_value("CB PM Schedule", schedule_name, "status"), "Completed")
		self.assertTrue(
			frappe.db.exists(
				"CB PM Schedule",
				{
					"pm_program": self.program,
					"outlet": FIXTURE_OUTLET,
					"asset": FIXTURE_AC_ASSET,
					"due_date": "2026-06-01",
				},
			),
			"Expected the next PM Schedule to be created even though this execution failed",
		)
		self.assertTrue(execution.generated_ticket)

		ticket = frappe.get_doc("CB Ticket", execution.generated_ticket)
		self.assertEqual(ticket.outlet, FIXTURE_OUTLET)
		self.assertEqual(ticket.asset, FIXTURE_AC_ASSET)
		self.assertEqual(ticket.source_pm_execution, execution.name)
		self.assertEqual(ticket.status, "Open")
		self.assertTrue(ticket.ticket_taxonomy)

	def test_7_duplicate_submit_rejected(self):
		_schedule_name, execution = self._new_execution(
			due_date="2026-07-01", completed_on="2026-07-01", result="Passed"
		)
		execution.submit()

		with self.assertRaises(frappe.ValidationError):
			execution.submit()

	def test_8_cross_outlet_asset_rejected(self):
		hyd_zonal_office = "HYD Zonal Office (Test 8)"
		if not frappe.db.exists("CB Zonal Office", hyd_zonal_office):
			frappe.get_doc(
				{"doctype": "CB Zonal Office", "zonal_office_name": hyd_zonal_office, "city": "HYD"}
			).insert()

		other_outlet = frappe.get_doc(
			{
				"doctype": "CB Outlet",
				"outlet_code": "T8HYDOUT",
				"city": "HYD",
				"zonal_office": hyd_zonal_office,
				"status": "Active",
			}
		).insert().name

		other_asset = frappe.get_doc(
			{
				"doctype": "CB Asset",
				"asset_type": "Air Conditioner",
				"outlet": other_outlet,
				"status": "Active",
			}
		).insert().name

		schedule = frappe.get_doc(
			{
				"doctype": "CB PM Schedule",
				"pm_program": self.program,
				"outlet": FIXTURE_OUTLET,  # BLR001
				"asset": other_asset,  # belongs to T8HYDOUT, not BLR001
				"due_date": "2026-08-01",
				"status": "Scheduled",
			}
		)
		with self.assertRaises(frappe.ValidationError):
			schedule.insert()
