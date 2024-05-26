# Copyright (c) 2024, LavaLoon and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ZATCAPhase1BusinessSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		address: DF.Link
		company: DF.Link
		status: DF.Literal["Active", "Disabled"]
		type_of_transaction: DF.Literal["Simplified", "Standard Tax Invoice", "Both"]
		vat_registration_number: DF.Data | None
	# end: auto-generated types
	pass

	def validate(self):
		if frappe.get_value("ZATCA Business Settings", {"company": self.company}) and self.status == "Active":
			frappe.throw("ZATCA Phase 2 Business Settings already enabled.", title="Another Setting Already Enabled")