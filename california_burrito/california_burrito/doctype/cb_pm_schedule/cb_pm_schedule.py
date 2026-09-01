# Copyright (c) 2026, Falendra Bandhe and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from california_burrito.utils.schedule import build_generation_key


class CBPMSchedule(Document):
	def before_insert(self):
		self.generation_key = build_generation_key(self.pm_program, self.outlet, self.asset, self.due_date)

	def validate(self):
		program_asset_type = frappe.db.get_value("CB PM Program", self.pm_program, "asset_type")

		if program_asset_type and not self.asset:
			frappe.throw(
				_("Asset is required: PM Program {0} applies to Asset Type {1}.").format(
					self.pm_program, program_asset_type
				)
			)
		if not program_asset_type and self.asset:
			frappe.throw(
				_("Asset must be left blank: PM Program {0} is an outlet-level program (no Asset Type).").format(
					self.pm_program
				)
			)

		if self.asset:
			asset_outlet = frappe.db.get_value("CB Asset", self.asset, "outlet")
			if asset_outlet != self.outlet:
				frappe.throw(
					_("Asset {0} belongs to Outlet {1}, not {2}.").format(self.asset, asset_outlet, self.outlet)
				)


def on_doctype_update():
	# Support the due/overdue report views specifically — Frappe auto-indexes Link fields
	# individually, these composite indexes are additional. See docs/DocType_Spec.md section 7.
	frappe.db.add_index("CB PM Schedule", ["outlet", "status", "due_date"])
	frappe.db.add_index("CB PM Schedule", ["asset", "status"])
