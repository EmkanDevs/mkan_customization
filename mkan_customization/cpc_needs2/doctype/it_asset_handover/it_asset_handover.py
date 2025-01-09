# Copyright (c) 2025, Frappe Technologies and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ITAssetHandover(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.cpc_needs2.doctype.it_asset_handover_item.it_asset_handover_item import ITAssetHandoverItem
		from frappe.types import DF

		handover_items: DF.Table[ITAssetHandoverItem]
		handover_type: DF.Literal["To Client or User", "To IT Support"]
		hanover_date: DF.Date | None
		provider_badge: DF.Link | None
		provider_department: DF.Data | None
		provider_designation: DF.Data | None
		provider_name: DF.Data | None
		receiver_badge: DF.Link | None
		receiver_department: DF.Data | None
		receiver_designation: DF.Data | None
		receiver_name: DF.Data | None
	# end: auto-generated types
	pass
