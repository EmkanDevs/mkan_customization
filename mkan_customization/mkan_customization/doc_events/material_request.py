import frappe

def validate(self,method):
    self.custom_created_by_user = self.owner
    for item in self.items:
        validate_item_uom(item)
    
def validate_item_uom(item_row):
    allowed_uoms = frappe.get_all(
        "UOM Conversion Detail",
        filters={"parent": item_row.item_code},
        fields=["uom"]
    )

    allowed_uoms_list = [d.uom for d in allowed_uoms]

    stock_uom = frappe.db.get_value("Item", item_row.item_code, "stock_uom")
    if stock_uom and stock_uom not in allowed_uoms_list:
        allowed_uoms_list.append(stock_uom)

    if item_row.uom not in allowed_uoms_list:
        frappe.throw(
            f"Row #{item_row.idx}: UOM <b>{item_row.uom}</b> is not valid for Item <b>{item_row.item_code}</b>.<br>"
            f"Allowed UOMs: {', '.join(allowed_uoms_list)}"
        )
        
@frappe.whitelist()
def validate_before_po_creation(material_request):
    # Check if there are any submitted RFQs linked to the Material Request
    rfqs = frappe.get_all(
        "Request for Quotation Item",
        filters={"material_request": material_request},
        fields=["parent"],
        distinct=True
    )

    if not rfqs:
        return "Please create a Request for Quotation before creating a Purchase Order."

    rfq_names = [rfq["parent"] for rfq in rfqs]
    submitted_rfqs = frappe.get_all(
        "Request for Quotation",
        filters={"name": ["in", rfq_names], "docstatus": 1},
        fields=["name"]
    )
    # frappe.throw(f"Submitted RFQs: {submitted_rfqs}")

    if not submitted_rfqs:
        return "The linked Request for Quotation(s) must be submitted before creating a Purchase Order."

    # Check if Bid Tabulation Discussion is created and submitted for the RFQ
    bt_list = frappe.get_all(
        "Bid Tabulation Discussion",
        filters={
            "request_for_quotation": ["in", [r["name"] for r in submitted_rfqs]],
            "docstatus": 1  # Only submitted
        },
        fields=["name"]
    )
    if not bt_list:
        return "Please create and submit a Bid Tabulation for the submitted Request for Quotation(s) before creating a Purchase Order."

    return True
