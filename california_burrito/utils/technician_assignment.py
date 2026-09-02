# Copyright (c) 2026, Falendra Bandhe and contributors
# For license information, please see license.txt

"""Technician assignment for CB Ticket — the deliberately simple version of the
chosen "go further" direction's fourth link. One deterministic rule: the first
active CB Technician whose zonal_office matches the ticket's outlet's zonal_office.
No load balancing, no escalation, no reporting-chain logic — see
docs/ASSUMPTIONS.md for why this stops here; full routing is explicitly deferred
post-deployment, not forgotten.
"""

import frappe


def suggest_assigned_technician(outlet_name):
	"""Return a CB Technician name to suggest for a ticket at this outlet, or None
	if the outlet has no zonal_office or no active technician covers it."""
	if not outlet_name:
		return None

	zonal_office = frappe.db.get_value("CB Outlet", outlet_name, "zonal_office")
	if not zonal_office:
		return None

	return frappe.db.get_value(
		"CB Technician",
		{"zonal_office": zonal_office, "active": 1},
		"name",
		order_by="name asc",
	)
