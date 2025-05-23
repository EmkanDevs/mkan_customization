# Copyright (c) 2025, Finbyz and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class Lodge(Document):
	def validate(self):
		self.available_capacity = self.max_capacity - self.current_capacity
