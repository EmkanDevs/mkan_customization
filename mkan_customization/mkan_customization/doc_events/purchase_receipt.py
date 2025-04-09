    
import frappe

def validate(self, method):
    if not self.petty_cash_request:
        return
    total = 0
    purchase_receipt_total = 0
    expense_claim_total = 0

    purchase_receipt = frappe.get_all(
        "Purchase Receipt",
        filters={"petty_cash_request": self.petty_cash_request},
        fields=["name"]
    )
    for row in purchase_receipt:
        doc = frappe.get_doc("Purchase Receipt", row.name)
        purchase_receipt_total += doc.grand_total
        
    expense_claim = frappe.get_all(
        "Expense Claim",
        filters={"petty_cash_request": self.petty_cash_request},
        fields=["name"]
    )
    for row in expense_claim:
        doc = frappe.get_doc("Expense Claim", row.name)
        expense_claim_total += doc.grand_total

    total = purchase_receipt_total + expense_claim_total
    petty_cash = frappe.get_doc("Petty Cash Request",self.petty_cash_request)
    limit = petty_cash.received_amount or petty_cash.required_amount
    if total >= limit:
        frappe.msgprint(
            f"Validation Error: The total amount for Petty Cash Request '{self.petty_cash_request}' has exceeded the limit of {limit}. "
            f"Current Total: {total}. Please review your claims."
        )
def after_insert(self,method):
    if self.petty_cash_request:
        self.is_petty_cash = 1
        self.petty_cash_employee = frappe.db.get_value("Petty Cash Request",self.petty_cash_request,"employee")
def on_cancel(self,method):
    self.db_set("petty_cash_request",None)
