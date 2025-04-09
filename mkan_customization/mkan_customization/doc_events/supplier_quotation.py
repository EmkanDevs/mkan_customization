import frappe

def on_cancel(self, method):
    for row in self.items:
        if row.request_for_quotation:
            data = frappe.get_doc("Bid Tabulation Discussion",{"request_for_quotation":row.request_for_quotation})
            if data.docstatus == 1:
                frappe.throw(f"You cannot cancel this Supplier Quotation because it is connect to Bid Tabulation Discussion {data.name}")