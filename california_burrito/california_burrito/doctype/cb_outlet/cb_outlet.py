# Copyright (c) 2026, Falendra Bandhe and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from california_burrito.utils.schedule import schedule_new_outlet


class CBOutlet(Document):
	def after_insert(self):
		# Applicability hook: a new Outlet automatically becomes eligible for every
		# existing outlet-level PM Program (asset_type blank) — no re-entry per store.
		# See docs/DocType_Spec.md section 7.
		schedule_new_outlet(self)
