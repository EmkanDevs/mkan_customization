import frappe

def on_cancel(self, method):
    # if connected RFQ's bid tabulation discussion is created and docstatus is 1
    checked_rfqs = set()
    for row in self.items:
        rfq = row.request_for_quotation
        if not rfq or rfq in checked_rfqs:
            continue  # the same RFQ always gives the same answer, so check it once
        checked_rfqs.add(rfq)
        # Picks the same record get_doc(filters) picked before, without loading it in full.
        data = frappe.db.get_value(
            "Bid Tabulation Discussion",
            {"request_for_quotation": rfq},
            ["name", "docstatus"],
            as_dict=True,
        )
        if data and data.docstatus == 1:
            frappe.throw(f"You cannot cancel this Supplier Quotation because it is connect to Bid Tabulation Discussion {data.name}")