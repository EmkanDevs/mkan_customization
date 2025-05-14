# Copyright (c) 2025, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from mkan_customization.mkan_customization.override import assign_to

class ServiceStatus(Document):
	def after_insert(self):
		for row in self.details:
			user = frappe.db.get_value("Material Request",row.material_request,"owner")
			assign_to.add(
				dict(
					assign_to=[user],
					doctype="Service Status",
					name=self.name,
					priority= "Medium",
					notify=True,
				),
				ignore_permissions=True,
			)
