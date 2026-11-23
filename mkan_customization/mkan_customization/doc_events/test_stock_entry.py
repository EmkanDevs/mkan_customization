import unittest
from unittest.mock import patch

import frappe

from mkan_customization.mkan_customization.doc_events.stock_entry import (
	get_reference_documents,
	set_reference_documents,
)

LINKS = {
	"Stock Entry Detail": {
		"material_request": "Material Request",
		"custom_material_request": "Material Request",
		"against_stock_entry": "Stock Entry",
		"reference_purchase_receipt": "Purchase Receipt",
	},
	"Stock Entry": {
		"outgoing_stock_entry": "Stock Entry",
		"custom_return_material_ref_doc": "Returned Material to Warehouse Request",
		"work_order": "Work Order",
	},
}


def get_meta(doctype):
	def get_field(fieldname):
		options = LINKS[doctype].get(fieldname)
		return frappe._dict(fieldtype="Link", options=options) if options else None

	return frappe._dict(get_field=get_field)


class TestStockEntryReferenceDocuments(unittest.TestCase):
	def setUp(self):
		meta = patch("frappe.get_meta", side_effect=get_meta)
		meta.start()
		self.addCleanup(meta.stop)

	def make_doc(self, items, **fields):
		return frappe._dict(items=[frappe._dict(row) for row in items], **fields)

	def test_lists_unique_item_and_parent_references_with_type(self):
		doc = self.make_doc(
			[
				{"material_request": "MR-1", "custom_material_request": "MR-1"},
				{"material_request": "MR-2", "against_stock_entry": "STE-9"},
				{"material_request": "MR-1", "reference_purchase_receipt": "PR-1"},
			],
			outgoing_stock_entry="STE-9",
			custom_return_material_ref_doc="RMW-1",
		)
		self.assertEqual(
			get_reference_documents(doc).splitlines(),
			[
				"Material Request: MR-1",
				"Material Request: MR-2",
				"Stock Entry: STE-9",
				"Purchase Receipt: PR-1",
				"Returned Material to Warehouse Request: RMW-1",
			],
		)

	def test_same_name_in_different_doctypes_is_kept(self):
		doc = self.make_doc([{"against_stock_entry": "X-1"}], work_order="X-1")
		self.assertEqual(get_reference_documents(doc), "Stock Entry: X-1\nWork Order: X-1")

	def test_fields_missing_on_the_site_are_skipped(self):
		doc = self.make_doc([], purchase_order="PO-1", work_order="WO-1")
		self.assertEqual(get_reference_documents(doc), "Work Order: WO-1")

	def test_clears_old_references_when_none_left(self):
		doc = self.make_doc([{"item_code": "ITEM"}], custom_reference_documents="Old")
		set_reference_documents(doc)
		self.assertEqual(doc.custom_reference_documents, "")
