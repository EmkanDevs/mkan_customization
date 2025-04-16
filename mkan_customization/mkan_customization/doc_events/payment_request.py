import frappe

def on_submit(self, method):
    if self.party_type == "Supplier" and self.party:
        missing_fields = []

        if not frappe.db.get_value("Supplier", self.party, "custom_default_bank_name"):
            missing_fields.append("<span style='color:red;'>Default Bank Name</span>")
        if not frappe.db.get_value("Supplier", self.party, "custom_default_bank_account"):
            missing_fields.append("<span style='color:red;'>Default Bank Account</span>")
        if not frappe.db.get_value("Supplier", self.party, "custom_default_iban_no"):
            missing_fields.append("<span style='color:red;'>IBAN Number</span>")

        if missing_fields:
            frappe.msgprint(f"The following supplier bank details are missing: {'<,>'.join(missing_fields)}")
