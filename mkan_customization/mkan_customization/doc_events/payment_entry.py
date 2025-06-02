import frappe

def on_update(self, method):
    if self.references:
        for reference in self.references:
            if reference.reference_doctype == "Purchase Order":
                self.db_set("custom_ref_name_for_purchase_order","Purchase Order")