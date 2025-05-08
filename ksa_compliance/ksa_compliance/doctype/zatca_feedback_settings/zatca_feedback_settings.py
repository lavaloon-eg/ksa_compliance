# Copyright (c) 2025, LavaLoon and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ZATCAFeedbackSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		lavaloon_contact_page: DF.Data | None
		max_file_size_mb: DF.Int
		max_number_of_files: DF.Int
		recipient_emails: DF.SmallText | None
	# end: auto-generated types
	pass
