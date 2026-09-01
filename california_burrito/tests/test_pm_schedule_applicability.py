# Copyright (c) 2026, Falendra Bandhe and contributors
# For license information, please see license.txt

"""Acceptance tests 1 and 2 from docs/DocType_Spec.md: PM Program applicability is
computed fresh from live CB Asset / CB Outlet data at generation time, never scoped
to whichever outlets/assets happened to appear in the import sample.

Test 1 runs against the persistent Phase 1/2 fixture (Outlet BLR001, its two assets,
and the "Air Conditioner / Clean filter / Monthly" PM Program) plus one extra AC
asset created here, so the "applies to every matching asset, not just one" behaviour
is actually exercised — the fixture only seeds a single AC asset. Test 2 needs
several outlets to prove outlet-level applicability, so it creates its own; the
Phase 1 fixture only has one.
"""

import frappe
from frappe.tests import IntegrationTestCase

from california_burrito.utils.schedule import ensure_schedule, find_applicable_targets

FIXTURE_ZONAL_OFFICE = "BLR Zonal Office"
FIXTURE_OUTLET = "BLR001"
FIXTURE_AC_ASSET = "AST-00001"  # Air Conditioner
FIXTURE_CHILLER_ASSET = "AST-00002"  # Walk-in Chiller
FIXTURE_AC_PROGRAM_KEY = "Air Conditioner|Clean filter|Monthly"


class TestPMScheduleApplicability(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def test_1_asset_type_program_applies_only_to_matching_assets(self):
		self.assertTrue(frappe.db.exists("CB Asset", FIXTURE_AC_ASSET))
		self.assertTrue(frappe.db.exists("CB Asset", FIXTURE_CHILLER_ASSET))

		program_name = frappe.db.get_value("CB PM Program", {"program_key": FIXTURE_AC_PROGRAM_KEY}, "name")
		self.assertTrue(
			program_name, "Expected the 'Air Conditioner / Clean filter / Monthly' PM Program fixture to exist"
		)
		program = frappe.get_doc("CB PM Program", program_name)

		# A second AC asset at the same outlet, created just for this test — proves
		# applicability covers every matching asset, not just the one the fixture seeds.
		second_ac_asset = frappe.get_doc(
			{
				"doctype": "CB Asset",
				"asset_type": "Air Conditioner",
				"outlet": FIXTURE_OUTLET,
				"status": "Active",
			}
		).insert().name

		targets = find_applicable_targets(program)
		target_assets = {asset for _, asset in targets}

		self.assertIn(FIXTURE_AC_ASSET, target_assets)
		self.assertIn(second_ac_asset, target_assets)
		self.assertNotIn(FIXTURE_CHILLER_ASSET, target_assets)

		for outlet_name, asset_name in targets:
			ensure_schedule(program.name, outlet_name, asset_name, "2026-09-01")

		scheduled_assets = set(
			frappe.get_all("CB PM Schedule", filters={"pm_program": program.name}, pluck="asset")
		)
		self.assertIn(FIXTURE_AC_ASSET, scheduled_assets)
		self.assertIn(second_ac_asset, scheduled_assets)
		self.assertNotIn(FIXTURE_CHILLER_ASSET, scheduled_assets)

		# Idempotent generation: calling ensure_schedule again for the same target/date
		# must not create a second row — the DB-level unique constraint on
		# generation_key is what actually guards this, not a pre-check.
		before = frappe.db.count(
			"CB PM Schedule", {"pm_program": program.name, "asset": FIXTURE_AC_ASSET, "due_date": "2026-09-01"}
		)
		ensure_schedule(program.name, FIXTURE_OUTLET, FIXTURE_AC_ASSET, "2026-09-01")
		after = frappe.db.count(
			"CB PM Schedule", {"pm_program": program.name, "asset": FIXTURE_AC_ASSET, "due_date": "2026-09-01"}
		)
		self.assertEqual(before, after)

	def test_2_outlet_level_program_applies_to_every_active_outlet(self):
		program = frappe.get_doc(
			{
				"doctype": "CB PM Program",
				"program_name": "Test Pest Control Monthly (acceptance test 2)",
				"task_description": "Pest control (acceptance test 2)",
				"frequency": "Monthly",
				# asset_type intentionally left blank -> outlet-level program
			}
		).insert()

		new_outlets = [
			frappe.get_doc(
				{
					"doctype": "CB Outlet",
					"outlet_code": code,
					"city": "BLR",
					"zonal_office": FIXTURE_ZONAL_OFFICE,
					"status": "Active",
				}
			).insert().name
			for code in ("T2OUTA", "T2OUTB", "T2OUTC")
		]

		targets = find_applicable_targets(program)
		target_outlets = [outlet for outlet, _asset in targets]

		# Applicability is computed fresh from every active CB Outlet, including BLR001
		# from the Phase 1 fixture — never scoped to only the outlets this test creates.
		# This is a stronger check than asserting a literal count of 3: it proves the
		# function tracks the live outlet universe rather than a fixed set.
		self.assertEqual(len(targets), frappe.db.count("CB Outlet", {"status": "Active"}))
		self.assertIn(FIXTURE_OUTLET, target_outlets)
		for outlet in new_outlets:
			self.assertIn(outlet, target_outlets)

		for outlet_name, asset_name in targets:
			ensure_schedule(program.name, outlet_name, asset_name, "2026-09-01")

		for outlet in [*new_outlets, FIXTURE_OUTLET]:
			self.assertEqual(
				frappe.db.count("CB PM Schedule", {"pm_program": program.name, "outlet": outlet}), 1
			)
