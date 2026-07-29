import frappe

@frappe.whitelist()
def get_boq_item_map(boq):
    boq_doc = frappe.get_doc("BOQ", boq)
    warehouse = boq_doc.warehouse

    item_map = {}
    for row in boq_doc.boq_details:
        if row.created_item and row.boq_id:
            item_map[row.created_item] = row.boq_id
    return {
        "warehouse": boq_doc.warehouse,
        "item_map": item_map
    }


def before_submit(doc, method=None):
    if not doc.custom_stopped_sales_order_ref:
        return

    # Build a quick lookup of the new SO items to refresh IRM detail rows
    so_item_map = {row.item_code: row for row in (doc.get("items") or [])}

    old_so = doc.custom_stopped_sales_order_ref
    new_so = doc.name
    project = doc.project

    # Fetch IRM list at DB-level
    irm_list = frappe.db.get_all(
        "Invoice released Memo",
        filters={"sales_order": old_so},
        fields=["name", "version","sales_order"]
    )

    for irm in irm_list:
        irm_name = irm["name"]
        current_version = irm.get("version") or 0

        # Handle version increment safely
        try:
            new_version = int(current_version) + 1
        except Exception:
            new_version = current_version

        # Update IRM parent document via db.set_value
        frappe.db.set_value(
            "Invoice released Memo",
            irm_name,
            {
                "sales_order": new_so,
                "version": new_version,
                "project_name" : project
            },
            update_modified=False
        )

        # Update existing detail rows via db.set_value (per-row) to avoid doc saves
        if so_item_map:
            detail_rows = frappe.db.get_all(
                "Invoice released memo detail",
                filters={"parent": irm_name, "item": ["in", list(so_item_map.keys())]},
                fields=["name", "item"],
            )
            for row in detail_rows:
                so_row = so_item_map.get(row.item)
                if not so_row:
                    continue

                frappe.db.set_value(
                    "Invoice released memo detail",
                    row.name,
                    {
                        "contract__quantity": so_row.qty,
                        "unit_rate": so_row.rate,
                        "contract_price": (so_row.amount or 0) or ((so_row.qty or 0) * (so_row.rate or 0)),
                        "boq_id": doc.custom_boq,
                        "version": new_version,
                    },
                    update_modified=False,
                )