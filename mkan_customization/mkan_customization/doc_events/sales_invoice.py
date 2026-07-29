import frappe
from frappe.utils import money_in_words,flt

def validate(self, method):

    # self.set_advances()
 
    for row in self.advances:
        if self.advance_payment:
            row.allocated_amount = self.total * self.advance_payment / 100
    if self.retention_amount or self.custom_outstanding_value_ or self.grand_total:
        outstanding_amount = (
    flt(self.grand_total)
    - flt(self.retention_amount)
    - flt(self.total_advance)
    + flt(self.retention_recovery)
    )
        self.custom_outstanding_value_ = outstanding_amount
        self.custom_outstanding_amount_in_words = money_in_words(outstanding_amount)

def add_items(doc, method):
    selected_items = [row.item for row in doc.custom_add_items] if doc.custom_add_items else []

    if not selected_items:
        return

    selected_set = set(selected_items)

    rows_to_remove = []
    for row in (doc.items or []):
        if row.item_code not in selected_set:
            rows_to_remove.append(row)

    for row in rows_to_remove:
        doc.remove(row)

    doc.custom_add_items = []

