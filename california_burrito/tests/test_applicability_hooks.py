# Copyright (c) 2026, Falendra Bandhe and contributors
# For license information, please see license.txt

"""Acceptance test 3 and the Phase 4 checklist item for outlet-level auto-scheduling.

docs/DocType_Spec.md section 7: CB Asset.after_insert / CB Outlet.after_insert are
the reconciliation hooks that make a new Asset or Outlet automatically eligible for
matching existing PM Programs, with no re-entry per store.
"""

import frappe
from frappe.tests import IntegrationTestCase

FIXTURE_ZONAL_OFFICE = "BLR Zonal Office"
FIXTURE_OUTLET = "BLR001"
FIXTURE_AC_PROGRAM_KEY = "Air Conditioner|Clean filter|Monthly"


class TestApplicabilityHooks(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		program_name = frappe.db.get_value("CB PM Program", {"program_key": FIXTURE_AC_PROGRAM_KEY}, "name")
		self.assertTrue(
			program_name, "Expected the 'Air Conditioner / Clean filter / Monthly' PM Program fixture to exist"
		)
		self.ac_program = program_name

	def test_3_new_asset_auto_schedules_matching_program(self):
		# A fresh, disposable, guaranteed-*active* Program -- not self.ac_program (the
		# retired Phase 2 fixture, deliberately active=0 as of the demo-data sweep; see
		# docs/ASSUMPTIONS.md category 4). schedule_new_asset() only matches active
		# Programs, so this test must supply one of its own to actually exercise the
		# hook, same pattern as test_new_asset_of_non_matching_type_gets_no_schedule's
		# disposable asset type below.
		test_asset_type = "Test Applicability Hook Type (test 3)"
		if not frappe.db.exists("CB Asset Type", test_asset_type):
			frappe.get_doc({"doctype": "CB Asset Type", "asset_type_name": test_asset_type, "active": 1}).insert()

		program_key = f"{test_asset_type}|Test task (test 3)|Monthly"
		program_name = frappe.db.get_value("CB PM Program", {"program_key": program_key}, "name")
		if not program_name:
			program_name = frappe.get_doc(
				{
					"doctype": "CB PM Program",
					"program_name": "Test Applicability Hook Program (test 3)",
					"asset_type": test_asset_type,
					"task_description": "Test task (test 3)",
					"frequency": "Monthly",
					"active": 1,
				}
			).insert().name

		new_asset = frappe.get_doc(
			{
				"doctype": "CB Asset",
				"asset_type": test_asset_type,
				"outlet": FIXTURE_OUTLET,
				"status": "Active",
			}
		).insert().name  # CB Asset.after_insert fires here

		self.assertTrue(
			frappe.db.exists(
				"CB PM Schedule", {"pm_program": program_name, "outlet": FIXTURE_OUTLET, "asset": new_asset}
			),
			"Expected CB Asset.after_insert to auto-create a matching schedule",
		)

	def test_new_asset_of_non_matching_type_gets_no_schedule(self):
		# Proves after_insert isn't scheduling blanket-wide for every new asset — only
		# for programs whose asset_type actually matches.
		other_type = "Test Non-Matching Type (Phase 4 hook test)"
		if not frappe.db.exists("CB Asset Type", other_type):
			frappe.get_doc({"doctype": "CB Asset Type", "asset_type_name": other_type, "active": 1}).insert()

		new_asset = frappe.get_doc(
			{
				"doctype": "CB Asset",
				"asset_type": other_type,
				"outlet": FIXTURE_OUTLET,
				"status": "Active",
			}
		).insert().name

		self.assertFalse(frappe.db.exists("CB PM Schedule", {"asset": new_asset}))

	def test_new_outlet_auto_schedules_outlet_level_programs(self):
		program = frappe.get_doc(
			{
				"doctype": "CB PM Program",
				"program_name": "Test Pest Control Monthly (Phase 4 hook test)",
				"task_description": "Pest control (Phase 4 hook test)",
				"frequency": "Monthly",
				# asset_type blank -> outlet-level program
			}
		).insert()

		new_outlet = frappe.get_doc(
			{
				"doctype": "CB Outlet",
				"outlet_code": "T4OUT",
				"city": "BLR",
				"zonal_office": FIXTURE_ZONAL_OFFICE,
				"status": "Active",
			}
		).insert().name  # CB Outlet.after_insert fires here

		self.assertTrue(
			frappe.db.exists(
				"CB PM Schedule",
				{"pm_program": program.name, "outlet": new_outlet, "asset": ["is", "not set"]},
			),
			"Expected CB Outlet.after_insert to auto-create a schedule for the outlet-level program",
		)
		# And this new, asset-less outlet must NOT be scheduled for the existing
		# asset-type-scoped AC program — the two hooks must stay scoped to their own kind
		# of program.
		self.assertFalse(frappe.db.exists("CB PM Schedule", {"pm_program": self.ac_program, "outlet": new_outlet}))
