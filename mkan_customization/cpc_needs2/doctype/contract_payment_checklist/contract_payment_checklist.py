# Copyright (c) 2025, Frappe Technologies and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ContractPaymentChecklist(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		business_statement: DF.Data | None
		fully_paid: DF.Check
		notes: DF.Text | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		payment_amount: DF.Float
		payment_percentage: DF.Float
		quantity: DF.Int
		uom: DF.Link | None
	# end: auto-generated types
	pass
