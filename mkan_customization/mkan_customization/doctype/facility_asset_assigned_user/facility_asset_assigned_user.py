# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class FacilityAssetAssignedUser(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		assigned_user: DF.Link | None
		department: DF.Data | None
		designation: DF.Data | None
		from_date: DF.Date | None
		location: DF.Data | None
		name1: DF.Data | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		project: DF.Link | None
		to_date: DF.Date | None
	# end: auto-generated types
	pass
