import frappe
from frappe.utils import flt


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_data(filters):
    conditions = ""

    if filters.get("purchase_order"):
        conditions += f" and po.name = '{filters.purchase_order}'"
    if filters.get("project"):
        conditions += f"""
            and exists (
                select 1 from `tabPurchase Order Item` poi
                where poi.parent = po.name
                and poi.project = '{filters.project}'
            )
        """
    if filters.get("from_date"):
        conditions += f" and po.transaction_date >= '{filters.from_date}'"
    if filters.get("to_date"):
        conditions += f" and po.transaction_date <= '{filters.to_date}'"
    if filters.get("status"):
        conditions += f" and po.status = '{filters.status}'"

    pos = frappe.db.sql(f"""
        select 
            po.name,
            po.name,
            po.transaction_date,
            po.schedule_date,
            po.supplier_name,
            po.grand_total,
            po.set_warehouse,

            (select poi.project_name 
             from `tabPurchase Order Item` poi 
             where poi.parent = po.name 
             and poi.project_name is not null 
             limit 1) as item_project

        from `tabPurchase Order` po
        where po.docstatus = 1 {conditions}
    """, as_dict=1)

    data = []

    for po in pos:

        po_qty = frappe.db.sql("""
            select sum(qty) from `tabPurchase Order Item` where parent=%s
        """, po.name)[0][0] or 0

        received_qty = frappe.db.sql("""
            select sum(pri.qty)
            from `tabPurchase Receipt Item` pri
            join `tabPurchase Receipt` pr on pr.name = pri.parent
            where pri.purchase_order=%s and pr.docstatus=1
        """, po.name)[0][0] or 0

        billed_qty = frappe.db.sql("""
            select sum(pii.qty)
            from `tabPurchase Invoice Item` pii
            join `tabPurchase Invoice` pi on pi.name = pii.parent
            where pii.purchase_order=%s and pi.docstatus=1
        """, po.name)[0][0] or 0

        pending_qty = flt(po_qty - received_qty)
        qty_to_bill = flt(po_qty - billed_qty)

        billed_amount = frappe.db.sql("""
            select sum(pii.base_net_amount)
            from `tabPurchase Invoice Item` pii
            join `tabPurchase Invoice` pi on pi.name = pii.parent
            where pii.purchase_order=%s and pi.docstatus=1
        """, po.name)[0][0] or 0

        received_amount = frappe.db.sql("""
            select sum(pri.base_net_amount)
            from `tabPurchase Receipt Item` pri
            join `tabPurchase Receipt` pr on pr.name = pri.parent
            where pri.purchase_order=%s and pr.docstatus=1
        """, po.name)[0][0] or 0

        pending_amount = flt(po.grand_total - billed_amount)

        advance_amount = frappe.db.sql("""
            select sum(grand_total)
            from `tabPayment Request`
            where reference_doctype='Purchase Order'
            and reference_name=%s and docstatus=1
        """, po.name)[0][0] or 0

        payment_amount = frappe.db.sql("""
            select sum(per.allocated_amount)
            from `tabPayment Entry Reference` per
            join `tabPayment Entry` pe on pe.name = per.parent
            where per.reference_doctype='Purchase Order'
            and per.reference_name=%s and pe.docstatus=1
        """, po.name)[0][0] or 0

        data.append({
            "po_no": po.name,
            "po_title": po.name,
            "po_date": po.transaction_date,
            "required_date": po.schedule_date,
            "project": po.item_project,
            "supplier": po.supplier_name,
            "po_qty": po_qty,
            "received_qty": received_qty,
            "pending_qty": pending_qty,
            "billed_qty": billed_qty,
            "qty_to_bill": qty_to_bill,
            "grand_total": po.grand_total,
            "billed_amount": billed_amount,
            "pending_amount": pending_amount,
            "received_amount": received_amount,
            "warehouse": po.set_warehouse,
            "advance_amount": advance_amount,
            "payment_amount": payment_amount
        })

    return data


def get_columns():
    return [
        {"label":"PO No","fieldname":"po_no","fieldtype":"Link","options":"Purchase Order","width":130},
        {"label":"PO Name","fieldname":"po_title","width":200},
        {"label":"Date","fieldname":"po_date","fieldtype":"Date","width":90},
        {"label":"Required Date","fieldname":"required_date","fieldtype":"Date","width":90},
        {"label":"Project","fieldname":"project","fieldtype":"Link","options":"Project","width":150},
        {"label":"Supplier","fieldname":"supplier","fieldtype":"Link","options":"Supplier","width":150},
        {"label":"PO Qty","fieldname":"po_qty","fieldtype":"Float","width":100},
        {"label":"Received Qty","fieldname":"received_qty","fieldtype":"Float","width":100},
        {"label":"Pending Qty","fieldname":"pending_qty","fieldtype":"Float","width":100},
        {"label":"Billed Qty","fieldname":"billed_qty","fieldtype":"Float","width":100},
        {"label":"Qty to Bill","fieldname":"qty_to_bill","fieldtype":"Float","width":100},
        {"label":"Grand Total (SAR)","fieldname":"grand_total","fieldtype":"Currency","width":130},
        {"label":"Billed Amount","fieldname":"billed_amount","fieldtype":"Currency","width":130},
        {"label":"Pending Amount","fieldname":"pending_amount","fieldtype":"Currency","width":130},
        {"label":"Received Amount","fieldname":"received_amount","fieldtype":"Currency","width":130},
        {"label":"Warehouse","fieldname":"warehouse","fieldtype":"Link","options":"Warehouse","width":140},
        {"label":"Advance Amount","fieldname":"advance_amount","fieldtype":"Currency","width":140},
        {"label":"Payment Entry Amount","fieldname":"payment_amount","fieldtype":"Currency","width":140},
    ]
