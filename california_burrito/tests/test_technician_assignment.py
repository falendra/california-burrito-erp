# Copyright (c) 2026, Falendra Bandhe and contributors
# For license information, please see license.txt

"""Technician assignment for CB Ticket — the fourth link of ASSIGNMENT.md's chosen
"go further" direction, deliberately kept to one deterministic rule (the first
active technician at the outlet's zonal office), not a routing engine. See
docs/ASSUMPTIONS.md for the scope decision.
"""

import frappe
from frappe.tests import IntegrationTestCase

from california_burrito.utils.technician_assignment import suggest_assigned_technician

FIXTURE_OUTLET = "BLR001"
GASKET_TAXONOMY_FILTER = {"department": "Maintenance", "category": "ChestFreezer", "sub_category_1": "Gasket Broken"}


class TestTechnicianAssignment(IntegrationTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.zonal_office = frappe.db.get_value("CB Outlet", FIXTURE_OUTLET, "zonal_office")
		self.gasket_taxonomy = frappe.db.get_value("CB Ticket Taxonomy", GASKET_TAXONOMY_FILTER, "name")
		self.assertTrue(self.gasket_taxonomy)

	def _new_ticket(self, outlet):
		return frappe.get_doc(
			{
				"doctype": "CB Ticket",
				"outlet": outlet,
				"ticket_taxonomy": self.gasket_taxonomy,
				"priority": "Medium",
			}
		).insert()

	def test_ticket_gets_assigned_to_a_technician_at_the_outlets_zonal_office(self):
		ticket = self._new_ticket(FIXTURE_OUTLET)

		self.assertTrue(ticket.assigned_to)
		assigned_tech = frappe.get_doc("CB Technician", ticket.assigned_to)
		self.assertEqual(assigned_tech.zonal_office, self.zonal_office)
		self.assertEqual(assigned_tech.active, 1)
		# Deterministic, matches calling the utility function directly.
		self.assertEqual(ticket.assigned_to, suggest_assigned_technician(FIXTURE_OUTLET))

	def test_no_active_technician_at_zonal_office_means_no_suggestion(self):
		empty_zonal_office = "Test Empty Zonal Office (technician assignment test)"
		if not frappe.db.exists("CB Zonal Office", empty_zonal_office):
			frappe.get_doc(
				{"doctype": "CB Zonal Office", "zonal_office_name": empty_zonal_office, "city": "MUM"}
			).insert()
		empty_outlet = "T5NOTECH"
		if not frappe.db.exists("CB Outlet", empty_outlet):
			frappe.get_doc(
				{
					"doctype": "CB Outlet",
					"outlet_code": empty_outlet,
					"city": "MUM",
					"zonal_office": empty_zonal_office,
					"status": "Active",
				}
			).insert()

		self.assertIsNone(suggest_assigned_technician(empty_outlet))
		ticket = self._new_ticket(empty_outlet)
		self.assertFalse(ticket.assigned_to)

	def test_manual_override_survives_unrelated_save_but_refreshes_on_outlet_change(self):
		ticket = self._new_ticket(FIXTURE_OUTLET)
		original_suggestion = ticket.assigned_to
		self.assertTrue(original_suggestion)

		# User overrides, then saves for something unrelated (status change) ->
		# the override must survive.
		other_technician = frappe.get_all(
			"CB Technician",
			filters={"zonal_office": self.zonal_office, "active": 1, "name": ["!=", original_suggestion]},
			pluck="name",
		)[0]
		ticket.assigned_to = other_technician
		ticket.status = "Assigned"
		ticket.save()
		self.assertEqual(ticket.assigned_to, other_technician)

		# But changing the outlet -- a relevant change -- refreshes it.
		other_outlet = "AKA"  # different city/zonal office than BLR001
		self.assertNotEqual(frappe.db.get_value("CB Outlet", other_outlet, "zonal_office"), self.zonal_office)
		ticket.outlet = other_outlet
		ticket.save()
		self.assertEqual(ticket.assigned_to, suggest_assigned_technician(other_outlet))
