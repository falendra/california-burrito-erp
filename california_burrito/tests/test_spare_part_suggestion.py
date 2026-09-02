# Copyright (c) 2026, Falendra Bandhe and contributors
# For license information, please see license.txt

"""Spare-part suggestion for CB Ticket (docs/DocType_Spec.md section 9) — the
deferred half of ASSIGNMENT.md's chosen "go further" direction: PM failure -> ticket
-> spare-part suggestion -> technician assignment.

Runs against real Phase 5 import data throughout: the real "ChestFreezer / Gasket
Broken" taxonomy row, the real "Chest Freezer Celfrost" spare part family, and a
real Chest-Freezer asset synthesized at one of Before.xlsx's sample outlets — this
is the exact scenario docs/ASSIGNMENT.md itself uses to motivate the whole
direction, and it turns out the real data has a clean match for it.
"""

import frappe
from frappe.tests import IntegrationTestCase

from california_burrito.utils.spare_parts import suggest_spare_part

REAL_GASKET_PART = "CF01CF"  # Gasket, Chest Freezer Celfrost


class TestSparePartSuggestion(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		# Looked up by (outlet, asset_type), not a hardcoded "AST-00007" docname -- the
		# real import's asset numbers depend on how many CB Asset rows already exist
		# when it runs (see california_burrito/utils/seed_demo.py's deploy-order
		# docstring), so a literal name here would only happen to pass on whichever
		# site's specific creation history put "Chest Freezer at ADM" at that number.
		self.chest_freezer_asset = frappe.db.get_value(
			"CB Asset", {"outlet": "ADM", "asset_type": "Chest Freezer"}, "name"
		)
		self.assertTrue(self.chest_freezer_asset, "Expected a real 'Chest Freezer' asset synthesized at outlet ADM")
		self.gasket_taxonomy = frappe.db.get_value(
			"CB Ticket Taxonomy",
			{"department": "Maintenance", "category": "ChestFreezer", "sub_category_1": "Gasket Broken"},
			"name",
		)
		self.assertTrue(self.gasket_taxonomy, "Expected the real 'ChestFreezer / Gasket Broken' taxonomy row")
		self.outlet = frappe.db.get_value("CB Asset", self.chest_freezer_asset, "outlet")

	def test_chest_freezer_gasket_broken_suggests_the_real_gasket_part(self):
		# The exact docs/ASSIGNMENT.md scenario: "A ticket says 'Gasket Broken' on a
		# chest freezer. The spare-parts catalog has a part code for exactly that."
		ticket = frappe.get_doc(
			{
				"doctype": "CB Ticket",
				"outlet": self.outlet,
				"asset": self.chest_freezer_asset,
				"ticket_taxonomy": self.gasket_taxonomy,
				"priority": "Medium",
			}
		).insert()

		self.assertEqual(ticket.suggested_spare_part, REAL_GASKET_PART)

	def test_suggestion_narrows_by_taxonomy_when_equipment_has_several_parts(self):
		# "Chest Freezer Celfrost" has 8 parts in the real catalog (Gasket, Q Motor,
		# Relay, ...) — without a taxonomy hint, suggest_spare_part must still return
		# a real candidate for that equipment (not error, not nothing), and with the
		# gasket-specific taxonomy it must pick the gasket, not a random one of the 8.
		no_taxonomy_result = suggest_spare_part(self.chest_freezer_asset, None)
		all_chest_freezer_parts = frappe.get_all(
			"CB Spare Part", filters={"equipment_model": ["like", "%Chest Freezer%"]}, pluck="name"
		)
		self.assertGreater(len(all_chest_freezer_parts), 1)
		self.assertIn(no_taxonomy_result, all_chest_freezer_parts)

		with_taxonomy_result = suggest_spare_part(self.chest_freezer_asset, self.gasket_taxonomy)
		self.assertEqual(with_taxonomy_result, REAL_GASKET_PART)

	def test_no_asset_means_no_suggestion(self):
		ticket = frappe.get_doc(
			{
				"doctype": "CB Ticket",
				"outlet": self.outlet,
				"ticket_taxonomy": self.gasket_taxonomy,
				"priority": "Low",
				# asset intentionally blank -> outlet-level ticket, nothing to match
			}
		).insert()

		self.assertFalse(ticket.suggested_spare_part)

	def test_no_matching_equipment_means_no_suggestion(self):
		# TKT-00001's real situation: an Air Conditioner asset with no model, and the
		# real Spare Part catalog has no equipment_model containing the literal phrase
		# "Air Conditioner" (AC parts are catalogued under brand names like "Dsw Ac
		# Commercial Aircon" instead) — correctly no suggestion, not a wrong guess.
		# Looked up by (outlet, asset_type) rather than a hardcoded "AST-00003", same
		# reasoning as self.chest_freezer_asset above -- this is the hero scenario's
		# BLR134 Air Conditioner, which never gets a model set.
		hero_ac_asset = frappe.db.get_value("CB Asset", {"outlet": "BLR134", "asset_type": "Air Conditioner"}, "name")
		self.assertTrue(hero_ac_asset, "Expected the hero scenario's Air Conditioner asset at BLR134 to exist")
		self.assertIsNone(suggest_spare_part(hero_ac_asset, None))

	def test_manual_override_survives_an_unrelated_save(self):
		ticket = frappe.get_doc(
			{
				"doctype": "CB Ticket",
				"outlet": self.outlet,
				"asset": self.chest_freezer_asset,
				"ticket_taxonomy": self.gasket_taxonomy,
				"priority": "Medium",
			}
		).insert()
		self.assertEqual(ticket.suggested_spare_part, REAL_GASKET_PART)

		# User overrides the suggestion, then saves again for something unrelated
		# (e.g. moving the ticket forward) — the override must not be silently
		# clobbered back to the auto-suggestion.
		other_chest_freezer_part = frappe.get_all(
			"CB Spare Part",
			filters={"equipment_model": ["like", "%Chest Freezer%"], "name": ["!=", REAL_GASKET_PART]},
			pluck="name",
		)[0]
		ticket.suggested_spare_part = other_chest_freezer_part
		ticket.status = "Assigned"
		ticket.save()

		self.assertEqual(ticket.suggested_spare_part, other_chest_freezer_part)

		# But changing the asset — a relevant change — does refresh it. (Each sample
		# outlet has exactly one Chest Freezer, so a different one means a different
		# outlet too — keep outlet and asset consistent.)
		other_asset = frappe.get_all(
			"CB Asset",
			filters={"asset_type": "Chest Freezer", "name": ["!=", self.chest_freezer_asset]},
			fields=["name", "outlet"],
		)[0]
		ticket.asset = other_asset.name
		ticket.outlet = other_asset.outlet
		ticket.save()
		self.assertEqual(ticket.suggested_spare_part, REAL_GASKET_PART)
