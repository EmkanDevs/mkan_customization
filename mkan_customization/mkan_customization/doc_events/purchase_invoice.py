import frappe
from frappe.utils import money_in_words


def validate(self, method):
	self.set_advances()
	for row in self.advances:
		row.allocated_amount = self.total
