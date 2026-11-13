import frappe
from frappe import _
from frappe.utils import flt, money_in_words


def validate(self, method=None):
	# -------------------------------------------------------------
	# F01: Percentage Range Validation (0 to 100 inclusive)
	# -------------------------------------------------------------
	adv_val = self.get("advance_payment")
	if adv_val is not None and adv_val != "":
		try:
			adv_pct = flt(adv_val)
		except Exception:
			frappe.throw(_("Advance Recovery % must be between 0 and 100."))
		if adv_pct < 0 or adv_pct > 100:
			frappe.throw(_("Advance Recovery % must be between 0 and 100."))

	ret_val = self.get("retention")
	if ret_val is not None and ret_val != "":
		try:
			ret_pct = flt(ret_val)
		except Exception:
			frappe.throw(_("Retention % must be between 0 and 100."))
		if ret_pct < 0 or ret_pct > 100:
			frappe.throw(_("Retention % must be between 0 and 100."))

	# -------------------------------------------------------------
	# Calculation Base: Net Total (excluding VAT)
	# -------------------------------------------------------------
	net_total = flt(self.net_total or self.total)

	# Retention calculation strictly based on THIS invoice's net amount
	retention_percent = flt(self.retention or 0)
	retention_precision = self.precision("retention_amount") or 2
	self.retention_amount = flt((net_total * retention_percent) / 100, retention_precision)

	# -------------------------------------------------------------
	# F03 & F04: Advance Recovery Checks and Allocation
	# -------------------------------------------------------------
	recovery_percent = flt(self.advance_payment or 0)
	target_recovery = flt((net_total * recovery_percent) / 100, 2)

	# Stop standard ERPNext from automatically allocating 100% of invoice total
	self.allocate_advances_automatically = 0

	# Fetch eligible advance entries if not loaded yet
	if not self.get("advances") and recovery_percent > 0:
		self.set_advances()

	total_available = sum(flt(row.advance_amount) for row in self.get("advances", []))

	so_name = next((d.sales_order for d in self.get("items", []) if d.sales_order), None)
	so_label = f"Sales Order {so_name}" if so_name else "this Sales Order"

	if recovery_percent > 0:
		# F03: Missing eligible advance
		if total_available == 0:
			if self.docstatus == 1:
				frappe.throw(
					_("Cannot submit invoice with positive advance recovery ({0}%) because no eligible advance is available against {1}. Record/approve the advance receipt, or set Advance Recovery % to 0%.").format(
						recovery_percent, so_label
					),
					title=_("No Eligible Advance"),
				)
			else:
				frappe.msgprint(
					_("No eligible advance is available against {0}. Requested recovery: SAR {1:,.2f}. Record/approve the advance receipt, or set recovery to 0% if intentionally skipped.").format(
						so_label, target_recovery
					),
					title=_("No Eligible Advance"),
					indicator="orange",
				)
		# F04: Partial advance shortfall
		elif total_available < target_recovery:
			shortfall = target_recovery - total_available
			if self.docstatus == 1:
				shortfall_reason = (self.get("custom_cpc_recovery_shortfall_reason") or "").strip()
				if not shortfall_reason:
					frappe.throw(
						_("Requested advance recovery (SAR {0:,.2f}) exceeds available advance (SAR {1:,.2f}) by SAR {2:,.2f}. Please provide a Recovery Shortfall Reason before submitting.").format(
							target_recovery, total_available, shortfall
						),
						title=_("Shortfall Acknowledgment Required"),
					)
			else:
				frappe.msgprint(
					_("Requested recovery SAR {0:,.2f}; available SAR {1:,.2f}; allocated SAR {2:,.2f}; shortfall SAR {3:,.2f}.").format(
						target_recovery, total_available, total_available, shortfall
					),
					title=_("Advance Recovery Shortfall"),
					indicator="orange",
				)

	# Allocate advance up to target recovery and available balance
	remaining_recovery = target_recovery
	for row in self.get("advances", []):
		available = flt(row.advance_amount)
		if remaining_recovery > 0:
			alloc = min(remaining_recovery, available)
			row.allocated_amount = alloc
			remaining_recovery -= alloc
		else:
			row.allocated_amount = 0.0

	self.total_advance = sum(flt(d.allocated_amount) for d in self.get("advances", []))

	# -------------------------------------------------------------
	# F02: Current Payment Due = Standard Outstanding - Unpaid Held Retention
	# -------------------------------------------------------------
	grand_total = flt(self.rounded_total or self.grand_total)
	if self.docstatus == 1 and flt(self.outstanding_amount) > 0:
		standard_outstanding = flt(self.outstanding_amount)
	else:
		standard_outstanding = max(0.0, grand_total - flt(self.total_advance))

	due_precision = self.precision("custom_outstanding_value_") or 2
	current_due = max(0.0, flt(standard_outstanding - flt(self.retention_amount), due_precision))

	self.custom_outstanding_value_ = current_due
	self.custom_outstanding_amount_in_words = money_in_words(current_due)