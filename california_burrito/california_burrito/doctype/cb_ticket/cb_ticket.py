# Copyright (c) 2026, Falendra Bandhe and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CBTicket(Document):
	pass


def on_doctype_update():
	frappe.db.add_index("CB Ticket", ["outlet", "status"])
	frappe.db.add_index("CB Ticket", ["assigned_to", "status"])
