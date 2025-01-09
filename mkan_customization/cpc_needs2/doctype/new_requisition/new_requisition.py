# Copyright (c) 2025, Frappe Technologies and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class NewRequisition(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		description: DF.SmallText | None
		employee_department: DF.Data | None
		employee_name: DF.Data | None
		for_department: DF.Link | None
		for_employee: DF.Link | None
		for_project: DF.Link | None
		priority: DF.Link | None
		request_from: DF.Literal["", "IT", "HR", "QA"]
		requested_on: DF.Date | None
		status: DF.Literal["Open", "Replied", "On Hold", "Resolved", "Closed"]
		subject: DF.Data
		submitted_by: DF.Data | None
	# end: auto-generated types
	pass
