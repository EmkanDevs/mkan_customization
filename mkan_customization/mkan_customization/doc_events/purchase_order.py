import frappe

def after_insert(self, method):
    self.custom_bid_tabulation_check = 1
    self.db_set("custom_bid_tabulation_check", 1)
    
@frappe.whitelist()
def service_status_map(source_name):
    from frappe.model.mapper import get_mapped_doc

    # Step 1: Check if a Service Status already exists with this Purchase Order
    existing = frappe.get_all("Service Status", filters={"purchase_order": source_name}, fields=["name"])
    if existing:
        frappe.throw(f"Service Status <a href='/app/service-status/{existing[0].name}' style='color:blue;'>{existing[0].name}</a> already exists for this Purchase Order.")

    # Step 2: Map Purchase Order → Service Status
    def postprocess(source_doc, target_doc):
        target_doc.purchase_order = source_doc.name
        target_doc.customer = source_doc.customer

    return get_mapped_doc(
        "Purchase Order",
        source_name,
        {
            "Purchase Order": {
                "doctype": "Service Status",
                "validation": {
                    "docstatus": ["=", 1]
                }
            },
            "Purchase Order Item": {
                "doctype": "Service Status Details",
                "field_map": {
                    "item_code": "item",
                    "item_name": "item_name",
                    "description": "description",
                    "material_request": "material_request"
                },
                "add_if_empty": True
            }
        },
        postprocess=postprocess
    )
