import frappe
from frappe import _
from frappe.utils import flt


def after_insert(self, method):
    self.custom_bid_tabulation_check = 1
    self.db_set("custom_bid_tabulation_check", 1)

    if not self.supplier:
        return

    supplier = frappe.get_doc("Supplier", self.supplier)

    missing_fields = []

    if not supplier.get("custom_default_iban_no"):
        missing_fields.append("Default IBAN No.")

    if not supplier.get("custom_section_materials_services"):
        missing_fields.append("Section, Materials, Services")

    if not supplier.get("tax_id"):
        missing_fields.append("Tax ID")

    if not supplier.get("custom_cr_number"):
        missing_fields.append("CR Number")

    if not supplier.get("primary_address"):
        missing_fields.append("Address")

    if missing_fields:
        frappe.throw(
            _("Supplier {0} is missing required data: {1}").format(
                self.supplier_name, ", ".join(missing_fields)
            )
        )
    
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


def validate_rates_against_bid_tabulation(doc):
    """
    Returns mismatch data — does NOT throw.
    Client side handles the dialog.
    """
    if not doc.get("bid_tabulation"):
        return []

    sq_name = frappe.db.get_value(
        "Bid Tabulation Discussion",
        doc.bid_tabulation,
        "supplier_quotation"
    )

    if not sq_name:
        return []

    sq_items = frappe.get_all(
        "Supplier Quotation Item",
        filters={"parent": sq_name},
        fields=["item_code", "rate"],
    )

    sq_rate_map = {row["item_code"]: flt(row["rate"]) for row in sq_items}

    mismatches = []

    for item in doc.items:
        sq_rate = sq_rate_map.get(item.item_code)

        if sq_rate is None:
            mismatches.append({
                "item_code": item.item_code,
                "item_name": item.item_name,
                "sq_rate": "Not in SQ",
                "po_rate": flt(item.rate),
            })
        elif flt(sq_rate) != flt(item.rate):
            mismatches.append({
                "item_code": item.item_code,
                "item_name": item.item_name,
                "sq_rate": sq_rate,
                "po_rate": flt(item.rate),
            })

    return mismatches


@frappe.whitelist()
def check_rate_mismatch(doc):

    doc = frappe.parse_json(doc)

    if not doc.get("bid_tabulation"):
        return []

    sq_name = frappe.db.get_value(
        "Bid Tabulation Discussion",
        doc.get("bid_tabulation"),
        "supplier_quotation"
    )

    if not sq_name:
        return []

    sq_items = frappe.get_all(
        "Supplier Quotation Item",
        filters={"parent": sq_name},
        fields=["item_code", "rate"],
    )

    sq_rate_map = {
        row["item_code"]: flt(row["rate"])
        for row in sq_items
    }

    mismatches = []

    for item in doc.get("items", []):

        sq_rate = sq_rate_map.get(item.get("item_code"))

        if sq_rate is None:
            continue

        if flt(sq_rate) != flt(item.get("rate")):

            mismatches.append({
                "item_code": item.get("item_code"),
                "item_name": item.get("item_name"),
                "sq_rate": sq_rate,
                "po_rate": flt(item.get("rate")),
            })

    return mismatches