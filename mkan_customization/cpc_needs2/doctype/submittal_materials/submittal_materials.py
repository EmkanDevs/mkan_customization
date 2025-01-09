# Copyright (c) 2025, Frappe Technologies and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class SubmittalMaterials(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		amended_from: DF.Link | None
		client: DF.Data | None
		contractor: DF.Data | None
		date: DF.Date | None
		discipline: DF.Data | None
		engineer: DF.Data | None
		engineers_comments: DF.SmallText | None
		item: DF.Link | None
		item_name: DF.Data | None
		manufacturer: DF.Link | None
		manufacturer__local_supplier: DF.Data | None
		naming_series: DF.Data | None
		project: DF.Link | None
		project_name: DF.Data | None
		project_title: DF.Data | None
		proposed_material: DF.SmallText | None
		revision: DF.Literal[None]
		specified_material: DF.Data | None
		specs__boq__drawings_reference: DF.Data | None
		submittal: DF.Link | None
		submittal_status: DF.Literal["", "Approved", "Approved with Comments", "Revise and Resubmit", "Rejected"]
		submittal_type: DF.Data | None
		supplier: DF.Link | None
	# end: auto-generated types
	pass
