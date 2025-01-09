# Copyright (c) 2025, Frappe Technologies and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class Submittal(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		active: DF.Check
		amended_from: DF.Link | None
		client: DF.Data | None
		comments: DF.SmallText | None
		consultant_received_date: DF.Date | None
		consultant_response_date: DF.Date | None
		consultant_response_status: DF.Literal["", "Approved", "Approved with Comments", "Revise and Resubmit", "Rejected"]
		discipline: DF.Literal["", "Civil", "Architecture", "Electrical", "Mechanical", "General", "Others"]
		issued_to: DF.Literal["", "For Action", "For Approve", "Re-Submission", "Closed"]
		naming_series: DF.Literal[None]
		nhc_approval_status: DF.Literal["", "Approved", "Approved with Comments", "Revise and Resubmit", "Rejected"]
		nhc_response_date: DF.Date | None
		project: DF.Link
		project_name: DF.Data | None
		project_title: DF.Data | None
		revision: DF.Literal["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
		submittal_date: DF.Date | None
		submittal_descriptionsubject: DF.Data | None
		submittal_type: DF.Link
	# end: auto-generated types
	pass
