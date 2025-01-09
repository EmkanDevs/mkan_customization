# Copyright (c) 2025, Frappe Technologies and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class DepartmentServiceList(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.cpc_needs2.doctype.department_service_group.department_service_group import DepartmentServiceGroup
		from frappe.types import DF

		department: DF.Link | None
		name: DF.Int | None
		service_group: DF.TableMultiSelect[DepartmentServiceGroup]
		service_name: DF.Data | None
	# end: auto-generated types
	pass
