# Copyright (c) 2025, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class InvoicereleasedMemo(Document):
	def validate(self):
		for row in self.invoice_released_memo_detail:
			if row.contract__quantity and row.unit_rate:
				row.contract_price = row.contract__quantity * row.unit_rate
			if row.current_quantity and row.previous_quantity:
				row.accumulate_quantity = row.current_quantity + row.previous_quantity

@frappe.whitelist()
def get_matching_work_progress_reports(doctype, txt, searchfield, start, page_len, filters):
	if not filters:
		return []

	return frappe.db.sql("""
		SELECT name
		FROM `tabWork Progress Report`
		WHERE
			project = %(project_no)s
			AND sub_contractor = %(vendor)s
			AND project_sub_contracts = %(project_sub_contracts)s
			AND name LIKE %(txt)s
	""", {
		"project_no": filters.get("project_no"),
		"vendor": filters.get("vendor"),
		"project_sub_contracts": filters.get("project_sub_contracts"),
		"txt": "%" + txt + "%"
	})
	
import frappe

@frappe.whitelist()
def set_work_progress_report(invoice_name, work_progress_report):
	# Basic validation
	if not invoice_name or not work_progress_report:
		frappe.throw("Both invoice name and work progress report are required.")

	# Direct DB update, bypassing standard validation
	frappe.db.set_value(
		"Invoice released Memo",     
		invoice_name,                
		"work_progress_report",    
		work_progress_report,        
		update_modified=False      
	)
	# frappe.db.commit()
	return "Work Progress Report set successfully."
