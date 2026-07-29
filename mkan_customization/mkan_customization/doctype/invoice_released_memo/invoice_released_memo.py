# Copyright (c) 2025, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt,cstr


class InvoicereleasedMemo(Document):
    def validate(self):
        item_rows = {}
        duplicates = []

        if not self.created_from:
            frappe.throw(
                "You are only allowed to create Invoice Release Memo from Sales Order or Project Sub-Contracts"
            )

        # ---------------- Duplicate + Validation ----------------
        for row in self.invoice_released_memo_detail:
            if row.progress_percentage and row.progress_percentage > 100:
                frappe.throw(f"Progress Percentage cannot be more than 100 (Row {row.idx})")

        for idx, row in enumerate(self.invoice_released_memo_detail, start=1):
            item = row.item
            item_rows.setdefault(item, []).append(idx)

        for item, rows in item_rows.items():
            if len(rows) > 1:
                duplicates.append((item, rows))

        if duplicates:
            msg_lines = []
            for item, rows in duplicates:
                msg_lines.append(f"Item <b>{item}</b> is repeated in rows: {', '.join(map(str, rows))}")
            frappe.throw("<br>".join(msg_lines))

        # ---------------- Row Calculations ----------------
        for row in self.invoice_released_memo_detail:

            if (row.accumulate_quantity or 0) > (row.contract__quantity or 0):
                frappe.throw(
                    f"Row {row.idx}: Accumulate Quantity <b>{row.accumulate_quantity}</b> cannot exceed "
                    f"Contract Quantity <b>{row.contract__quantity}</b> for item <b>{row.item_name or row.item}</b>."
                )

            if (row.accumulate_quantity or 0) <= (row.previous_quantity or 0) and (row.accumulate_quantity or 0) != 0:
                frappe.throw(
                    f"Row {row.idx}: Accumulate Quantity <b>{row.accumulate_quantity}</b> cannot be less than or equal to "
                    f"Previous Quantity <b>{row.previous_quantity}</b> for item <b>{row.item_name or row.item}</b>."
                )

            # Contract Price
            row.contract_price = (row.contract__quantity or 0) * (row.unit_rate or 0)

            # Accumulated Final Quantity
            if (row.accumulate_quantity or 0) > (row.previous_quantity or 0):
                row.accumulate_final_quantity = row.accumulate_quantity
            else:
                row.accumulate_final_quantity = row.previous_quantity

            # Current Quantity
            row.current_quantity = (row.accumulate_final_quantity or 0) - (row.previous_quantity or 0)

            # Accumulated Amount
            if row.unit_rate and row.accumulate_final_quantity and row.progress_percentage:
                row.accumulated = (row.progress_percentage / 100) * (row.unit_rate * row.accumulate_final_quantity)
            else:
                row.accumulated = 0

            # Current Amount
            if row.progress_percentage == 0:
                row.current = 0
            else:
                row.current = float(row.accumulated or 0) - float(row.previous or 0)

        # ---------------- Totals ----------------
        total_contract_price = sum(d.contract_price or 0 for d in self.invoice_released_memo_detail)
        total_previous = round(sum(float(d.previous or 0) for d in self.invoice_released_memo_detail), 2)
        total_current = sum(float(d.current or 0) for d in self.invoice_released_memo_detail)
        total_accumulated = total_previous + total_current

        total_progress_percentage = (total_accumulated / total_contract_price * 100) if total_contract_price else 0

        # ---------------- VAT ----------------
        vat_percentage = 0
        vat_amount = 0

        if self.vate_rate:
            taxes = frappe.get_all(
                "Sales Taxes and Charges",
                filters={"parent": self.vate_rate},
                fields=["rate"],
                limit=1
            )
            if taxes:
                vat_percentage = taxes[0].rate or 0
                vat_amount = total_current * vat_percentage / 100

        # ---------------- Retention ----------------
        retention_amount = total_current * (self.retention or 0) / 100

        # ---------------- Grand Total Excluding VAT ----------------
        grand_total_excluding_vat = (
            (total_current or 0)
            + (self.retention_recovery or 0)
            - (
                (self.other_warranty or 0)
                + (self.supplied_material_total or 0)
                + (self.safety or 0)
                + (self.quality or 0)
                + (self.other_deductions or 0)
            )
        )


        # ---------------- Grand Total (IMAGE FORMULA) ----------------
        grand_total = (
            (total_current + vat_amount)
            + (self.retention_recovery or 0)
            - (
                retention_amount
                - (self.other_warranty or 0)
                + (self.supplied_material_total or 0)
                + (self.safety or 0)
                + (self.quality or 0)
                + (self.other_deductions or 0)
            )
        )

        # ---------------- Assign to Parent ----------------
        self.total_contract_price = total_contract_price
        self.total_current = total_current
        self.total_previous = total_previous
        self.total_accumulated = total_accumulated
        self.total_progress_percentage = total_progress_percentage

        self.retention_amount = retention_amount
        self.advanced_payment_recovery_amount = (self.advanced_payment_recovery or 0) / 100 * total_current

        self.vat = vat_percentage
        self.vat_amount = vat_amount
        self.grand_total = grand_total
        self.grand_total_including_vat = grand_total_excluding_vat




    def before_save(self):
        if self.sales_order:
            # Get the latest previous IRM
            previous_irms = frappe.get_all("Invoice released Memo",
                filters={"sales_order": self.sales_order, "name": ("!=", self.name)},
                order_by="version desc",
                limit_page_length=1,
                fields=["name"]
            )
'''
            if previous_irms:
                prev_doc = frappe.get_doc("Invoice released Memo", previous_irms[0].name)
                for i, row in enumerate(self.invoice_released_memo_detail):
                    prev_row = prev_doc.invoice_released_memo_detail[i]

                    # if row.contract__quantity > prev_row.contract__quantity:
                    #     frappe.throw(f"Row {i+1}: contract__quantity cannot be greater than previous version ({prev_row.contract__quantity})")

                    if row.unit_rate > prev_row.unit_rate:
                        frappe.throw(f"Row {i+1}: unit_rate cannot be greater than previous version ({prev_row.unit_rate})")

                    if row.contract_price > prev_row.contract_price:
                        frappe.throw(f"Row {i+1}: contract_price cannot be greater than previous version ({prev_row.contract_price})")
'''

@frappe.whitelist()
def get_items_from_sub_contract(project_sub_contracts):
    pro_sub = frappe.get_doc("Project Sub-Contracts", project_sub_contracts)

    items = []
    for row in pro_sub.fulfilment_terms:
        items.append({
            "item": row.requirement,
            "unit": row.custom_uom,
            "contract__quantity": row.custom_quantity,
            "contract_price": row.custom_amount,
        })
    return items

@frappe.whitelist()
def get_items_from_sales_order(sales_order):
    if not sales_order:
        frappe.throw("Please select a Sales Order")

    so = frappe.get_doc("Sales Order", sales_order)

    items = []
    for row in so.items:
        items.append({
            "boq_id": so.custom_boq,
            "item": row.item_code,
            "description": row.description,
            "unit": row.uom,
            "contract__quantity": row.qty,
            "unit_rate": row.rate,
            "contract_price": row.amount,
        })
    return items


@frappe.whitelist()
def create_payment_request(docname):
    irm = frappe.get_doc("Invoice released Memo", docname)

    # Check if already exists
    existing_pr = frappe.db.exists(
        "Payment Request",
        {
            "reference_doctype": "Invoice released Memo",
            "reference_name": irm.name,
            "party": irm.vendor,
            "docstatus": ("!=", 2)
        }
    )
    if existing_pr:
        return existing_pr

    pr = frappe.new_doc("Payment Request")
    pr.party_type = "Supplier"
    pr.party = irm.vendor
    pr.posting_date = irm.date or frappe.utils.nowdate()
    pr.reference_doctype = "Invoice released Memo"
    pr.reference_name = irm.name
    pr.grand_total = irm.grand_total_including_vat or irm.grand_total or 0
    pr.currency = frappe.defaults.get_global_default("currency")

    # bypass mandatory reference validation
    pr.insert(ignore_permissions=True, ignore_mandatory=True)

    return pr.name

@frappe.whitelist()
def make_irm_payment_request(docname):
    doc = frappe.get_doc("Invoice released Memo", docname)
    data = frappe.new_doc("Payment Requester")

    data.payment_request_type = "Inward" if doc.sales_order else "Outward"

    data.reference_doctype = "Invoice released Memo"
    data.reference_name = doc.name
    data.grand_total = doc.grand_total
    data.party_type = "Customer"
    data.party = doc.client

    if doc.project_name:
        project_id = frappe.db.get_value("Project", {"project_name": doc.project_name}, "name")
        if project_id:
            data.project = project_id

    data.save()

    return data


@frappe.whitelist()
def get_matching_work_progress_reports(doctype, txt, searchfield, start, page_len, filters):
    if not filters:
        return []

    return frappe.db.sql("""
        SELECT name
        FROM `tabWork Progress Report`
        WHERE
            project = %(project_no)s
            AND sub_contractor = %(vendor)s
            AND project_sub_contracts = %(project_sub_contracts)s
            AND name LIKE %(txt)s
    """, {
        "project_no": filters.get("project_no"),
        "vendor": filters.get("vendor"),
        "project_sub_contracts": filters.get("project_sub_contracts"),
        "txt": "%" + txt + "%"
    })
    
import frappe

@frappe.whitelist()
def set_work_progress_report(invoice_name, work_progress_report):
    # Basic validation
    if not invoice_name or not work_progress_report:
        frappe.throw("Both invoice name and work progress report are required.")

    # Direct DB update, bypassing standard validation
    frappe.db.set_value(
        "Invoice released Memo",     
        invoice_name,                
        "work_progress_report",    
        work_progress_report,        
        update_modified=False      
    )
    # frappe.db.commit()
    return "Work Progress Report set successfully."

@frappe.whitelist()
def create_sales_invoice_draft(source_name):
    """Create a Sales Invoice in draft mode from Invoice Released Memo"""
    source = frappe.get_doc("Invoice released Memo", source_name)
    target = frappe.new_doc("Sales Invoice")

    if source.sales_order:
        sales_order_doc = frappe.get_doc("Sales Order", source.sales_order)
        target.customer = sales_order_doc.customer
        target.advance_payment = sales_order_doc.custom_advance_amount

        # 🔹 Copy Taxes from Sales Order
    if sales_order_doc.taxes:
        for tax in sales_order_doc.taxes:
            target.append("taxes", {
                "charge_type": tax.charge_type,
                "account_head": tax.account_head,
                "description": tax.description,
                "rate": tax.rate,
                "cost_center": tax.cost_center,
                "tax_amount": tax.tax_amount,
                "base_tax_amount": tax.base_tax_amount,
                "included_in_print_rate": tax.included_in_print_rate,
                "included_in_paid_amount": tax.included_in_paid_amount
            })
    else:
        # fallback to client field in IRM
        target.customer = source.client
        
    project_id = frappe.db.get_value("Project", {"project_name": source.project_name}, "name")
    # 🔹 Map main fields
    target.posting_date = source.date
    target.project = project_id
    target.due_date = frappe.utils.nowdate()
    target.project = source.project_name
    target.retention = source.retention
    target.retention_amount = source.retention_amount
    target.retention_recovery = source.retention_recovery
    target.total_deductions = source.total_deductions

    # 🔹 Add child items
    for row in source.invoice_released_memo_detail:
        target.append("items", {
            "item_code": row.item,
            "qty": row.current_quantity,
            "rate": row.unit_rate,
            "uom": row.unit,
            "amount" : row.current,
            "project" : row.project
        })

    # 🔹 Save as draft (docstatus = 0 by default)
    target.run_method("calculate_taxes_and_totals")
    target.docstatus = 0 
    target.insert(ignore_permissions=True)
    frappe.db.commit()

   

    return target.name


