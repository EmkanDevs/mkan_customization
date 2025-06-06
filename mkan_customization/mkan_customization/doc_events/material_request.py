import frappe

def validate(self,method):
    self.custom_created_by_user = self.owner
    

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
