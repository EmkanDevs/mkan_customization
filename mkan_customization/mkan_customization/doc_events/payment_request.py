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

def update_payment_entry_count_in_request():
    # Fetch all Payment Entry Reference rows where payment_request is set
    references = frappe.get_all(
        "Payment Entry Reference",
        filters={"payment_request": ["is", "set"]},
        fields=["parent", "payment_request"]
    )

    # Dictionary to track unique Payment Entries per Payment Request
    payment_request_map = {}

    for ref in references:
        payment_request = ref.payment_request
        payment_entry = ref.parent

        if payment_request not in payment_request_map:
            payment_request_map[payment_request] = set()

        payment_request_map[payment_request].add(payment_entry)

    # Update each Payment Request with the count of linked Payment Entries
    for payment_request, payment_entries in payment_request_map.items():
        count = len(payment_entries)
        frappe.db.set_value("Payment Request", payment_request, "total_payment_entry", count,update_modified=False)
        frappe.db.commit()
