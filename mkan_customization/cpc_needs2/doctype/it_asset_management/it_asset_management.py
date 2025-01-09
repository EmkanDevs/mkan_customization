# Copyright (c) 2025, Frappe Technologies and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class ITAssetManagement(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		activated: DF.Check
		antivirus: DF.Check
		anydesk: DF.Data | None
		asset: DF.Link | None
		asset_local_code: DF.Data
		autodesk: DF.Data | None
		cadmate: DF.Data | None
		current_status: DF.Literal["", "In Storage", "In Use", "Retired", "Awaiting Disposal"]
		date_of_purchase_acquisition: DF.Date | None
		generation: DF.Data | None
		hard_disk_size_gb: DF.Data | None
		hard_disk_type: DF.Literal["", "Hard Disk Drive (HDD)", "Solid State Drive (SSD)", "M.2"]
		item: DF.Link | None
		item_group: DF.Data | None
		item_name: DF.Data | None
		location: DF.Link | None
		manufacturer: DF.Data | None
		more_items: DF.SmallText | None
		oswindows_type: DF.Literal["", "Windows Server 2022 Standard", "Windows 7", "Windows 10 Pro", "Windows 10 Business", "Windows 11 Pro", "Windows 11 Business"]
		ram_size: DF.Data | None
		serial_number: DF.Data | None
		windows_key: DF.Data | None
	# end: auto-generated types
	pass
