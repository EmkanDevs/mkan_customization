import frappe
from frappe.model.mapper import get_mapped_doc


def update_item(source, target, source_parent):
    target.against_blanket_order = 1

    # Optional: if you want to store the blanket order item reference
    target.blanket_order_item = source.name


def on_submit(doc, method):
    if doc.blanket_order_type != "Purchasing":
        return

    try:
        po = get_mapped_doc(
            "Blanket Order",
            doc.name,
            {
                "Blanket Order": {
                    "doctype": "Purchase Order",
                    "field_map": {
                        "name": "blanket_order",
                        "supplier": "supplier",
                        "to_date": "schedule_date",
                        "from_date": "transaction_date",
                        "company": "company",
                    }
                },
                "Blanket Order Item": {
                    "doctype": "Purchase Order Item",
                    "field_map": {
                        "name": "blanket_order_item",
                        "rate": "blanket_order_rate",
                        "item_code": "item_code",
                        "qty": "qty",
                        "rate": "rate",
                        "uom": "uom",
                    },
                    "postprocess": update_item,
                }
            }
        )

        # Set blanket order on all items (extra safety)
        for item in po.items:
            item.against_blanket_order = 1

        po.flags.ignore_permissions = True
        po.flags.ignore_mandatory = True

        po.insert()
        po.submit()

        frappe.msgprint(
            msg=f'Purchase Order <b><a href="/app/purchase-order/{po.name}">{po.name}</a></b> created successfully.',
            title="Purchase Order Created",
            indicator="green",
            alert=True,
        )

    except Exception:
        frappe.log_error(
            frappe.get_traceback(),
            "Blanket Order PO Creation Failed"
        )
        frappe.throw("Failed to create Purchase Order. Check Error Log for details.")