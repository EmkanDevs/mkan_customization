# Copyright (c) 2025, Frappe Technologies and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class SubmittalSupplier(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		active: DF.Check
		amended_from: DF.Link | None
		manufacturer: DF.Link | None
		naming_series: DF.Literal[None]
		project: DF.Data | None
		submittal: DF.Link | None
		submittal_type: DF.Data | None
		supplier: DF.Link
	# end: auto-generated types
	pass
