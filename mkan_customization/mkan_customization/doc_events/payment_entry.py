import frappe

def on_update(self, method):
    if not any(ref.reference_doctype == "Purchase Order" for ref in (self.references or [])):
        return
    # Same value as before, written once, and only when it is not already saved.
    if self.get("custom_ref_name_for_purchase_order") != "Purchase Order":
        self.db_set("custom_ref_name_for_purchase_order", "Purchase Order")