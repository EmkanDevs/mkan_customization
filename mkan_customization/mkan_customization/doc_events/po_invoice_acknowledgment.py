import frappe
from frappe import db
from frappe.utils import nowdate, getdate
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_invoice

def before_save(doc, method):
    if not doc.created_by:
        user = frappe.session.user
        doc.created_by = user
    if doc.acknowledgement:
        frappe.throw("This document is locked and cannot be edited")
    
def validate(doc, method):
    for i in doc.po_acknowledgement:
        po_invoice_created = frappe.db.get_values("Purchase Order Reference", {"purchase_order": i.purchase_order}, ["parent"])
        po_invoice_created = [x for x in po_invoice_created if x[0] != doc.name]
        if po_invoice_created:
            ids = [x[0] for x in po_invoice_created]
            all_po_invoices = ", ".join(ids[:-1]) + " and " + ids[-1] if len(ids) > 1 else ids[0]
            sentence = "The below Purchase Order data is repeated in these PO Invoice Acknowldegement: " + all_po_invoices
            frappe.throw(sentence)

@frappe.whitelist()
def get_allowed_roles():
    try:
        settings = frappe.get_single("Accounting Settings")
        roles = [
            row.role for row in settings.table_vuab
            if row.required
        ]
        return roles
    except Exception:
        return []
        
@frappe.whitelist()
def lock_document(doctype, docname):
    doc = frappe.get_doc(doctype, docname)
    for row in doc.po_acknowledgement:
        po = frappe.get_doc("Purchase Order", row.purchase_order)

        existing_pi = frappe.db.exists(
            "Purchase Invoice Item",
            {"purchase_order": po.name}
        )
        if existing_pi:
            frappe.msgprint(f"Purchase Invoice already exists for PO {po.name}.")
            return False
            
    for row in doc.po_acknowledgement:
        if row.purchase_order:

            posting_date = nowdate()
            bill_date = nowdate()
            # pick the larger of posting_date and po.schedule_date
            due_date = po.schedule_date if po.schedule_date and getdate(po.schedule_date) >= getdate(posting_date) else posting_date

            pi = frappe.get_doc({
                "doctype": "Purchase Invoice",
                "company": po.company,
                "supplier": po.supplier,
                "currency": po.currency,
                "buying_price_list": po.buying_price_list,
                "posting_date": posting_date,
                "due_date": due_date,
                "bill_no": row.supplier_invoice_no,
                "bill_date": row.supplier_invoice_date,
                "items": []
            })
            # Copy PO items into PI
            for item in po.items:
                pi.append("items", {
                    "item_code": item.item_code,
                    "item_name": item.item_name,
                    "qty": item.qty,
                    "uom": item.uom,
                    "rate": item.rate,
                    "amount": item.amount,
                    "purchase_order": po.name,
                    "expense_account": item.expense_account, 
                    "cost_center": item.cost_center,
                    "warehouse": item.warehouse,
                })
                
            # pi.run_method("validate")
            pi = make_purchase_invoice(po.name)
            pi.insert(ignore_permissions=True)
            doc.append("pi_acknowledgement", {
            "purchase_order": po.name,
            "purchase_invoice": pi.name
            })
            doc.save()
    doc.db_set("acknowledgement", 1)
    user = frappe.session.user
    doc.db_set("acknowledged_by", user)
    return True