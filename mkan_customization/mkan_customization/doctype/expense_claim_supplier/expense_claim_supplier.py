# Copyright (c) 2025, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class ExpenseClaimSupplier(Document):

    def validate(self):
        """Validate that CR Number or Tax ID does not already exist in Supplier."""
        duplicates = []

        cr_number = (self.cr_number or "").strip()
        tax_id = (self.tax_id or "").strip()

        # Check if a Supplier exists with the same CR Number
        if cr_number:
            existing_cr = frappe.db.exists("Supplier", {"custom_cr_number": cr_number})
            if existing_cr:
                duplicates.append(f"CR Number: {cr_number}")

        # Check if a Supplier exists with the same Tax ID
        if tax_id:
            existing_tax = frappe.db.exists("Supplier", {"tax_id": tax_id})
            if existing_tax:
                duplicates.append(f"Tax ID: {tax_id}")

        # If any duplicates found, stop save and show message
        if duplicates:
            msg = "<br>".join(duplicates)
            frappe.throw(
                f"⚠️ Supplier with the following identifiers already exists:<br><br>{msg}<br><br>"
                "<b>Please Generate a Purchase Invoice for this Supplier.<b>"
            )
