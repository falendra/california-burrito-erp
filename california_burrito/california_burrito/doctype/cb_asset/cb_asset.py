# Copyright (c) 2026, Falendra Bandhe and contributors
# For license information, please see license.txt

from frappe.model.document import Document

from california_burrito.utils.schedule import schedule_new_asset


class CBAsset(Document):
	def after_insert(self):
		# Applicability hook: a new Asset automatically becomes eligible for every
		# existing PM Program matching its asset_type — no re-entry per store.
		# See docs/DocType_Spec.md section 7.
		schedule_new_asset(self)
