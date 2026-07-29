# Copyright (c) 2025, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WorkProgressReport(Document):
    def before_save(self):
        if self.sales_order:
            # Get the latest previous WPR
            previous_wprs = frappe.get_all(
                "Work Progress Report",
                filters={"sales_order": self.sales_order, "name": ("!=", self.name)},
                order_by="version desc",
                limit_page_length=1,
                fields=["name"]
            )

            if previous_wprs:
                prev_doc = frappe.get_doc("Work Progress Report", previous_wprs[0].name)

                for i, row in enumerate(self.work_progress_detail):
                    prev_row = prev_doc.work_progress_detail[i]

                    # Cast to float before comparison
                    total_qty = float(row.total_quantities_implemented or 0)
                    prev_total_qty = float(prev_row.total_quantities_implemented or 0)

                    rate = float(row.rate or 0)
                    prev_rate = float(prev_row.rate or 0)

                    amount = float(row.current_executed_quantity or 0) * float(row.rate or 0)
                    prev_amount = float(prev_row.amount or 0)

                    if total_qty > prev_total_qty:
                        frappe.throw(f"Row {i+1}: total_quantities_implemented cannot be greater than previous version ({prev_total_qty})")

                    if rate > prev_rate:
                        frappe.throw(f"Row {i+1}: rate cannot be greater than previous version ({prev_rate})")

                    if amount > prev_amount:
                        frappe.throw(f"Row {i+1}: amount cannot be greater than previous version ({prev_amount})")

