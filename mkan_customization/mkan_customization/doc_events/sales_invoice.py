import frappe
from frappe.utils import money_in_words

def validate(self, method):
    self.set_advances()
    for row in self.advances:
        if self.advance_payment:
            row.allocated_amount = self.total * self.advance_payment / 100
    if self.retention_amount or self.custom_outstanding_value_ or self.grand_total:
        outstanding_amount = self.grand_total - (self.retention_amount + self.total_advance)
        self.custom_outstanding_value_ = outstanding_amount
        self.custom_outstanding_amount_in_words = money_in_words(outstanding_amount)