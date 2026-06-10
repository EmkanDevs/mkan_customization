import frappe
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt

@frappe.whitelist()
def make_stock_in_entry(source_name, target_doc=None):
	def set_missing_values(source, target):
		target.stock_entry_type = "Material Transfer"
		target.set_missing_values()

		if not frappe.db.get_single_value("Stock Settings", "use_serial_batch_fields"):
			target.make_serial_and_batch_bundle_for_transfer()

	def update_item(source_doc, target_doc, source_parent):
		target_doc.t_warehouse = ""

		if source_doc.material_request_item and source_doc.material_request:
			add_to_transit = frappe.db.get_value("Stock Entry", source_name, "add_to_transit")
			if add_to_transit:
				warehouse = frappe.get_value(
					"Material Request Item", source_doc.material_request_item, "warehouse"
				)
				target_doc.t_warehouse = warehouse

		target_doc.s_warehouse = source_doc.t_warehouse
		target_doc.qty = source_doc.qty - source_doc.transferred_qty

	doclist = get_mapped_doc(
		"Stock Entry",
		source_name,
		{
			"Stock Entry": {
				"doctype": "Stock Entry",
				"field_map": {"name": "outgoing_stock_entry"},
				"validation": {"docstatus": ["=", 1]},
			},
			"Stock Entry Detail": {
				"doctype": "Stock Entry Detail",
				"field_map": {
					"name": "ste_detail",
					"parent": "against_stock_entry",
					"serial_no": "serial_no",
					"batch_no": "batch_no",
					"material_request":"custom_material_request",
                    "material_request_item":"custom_material_request_item"
				},
				"postprocess": update_item,
				"condition": lambda doc: flt(doc.qty) - flt(doc.transferred_qty) > 0.00001,
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist



@frappe.whitelist()
def create_returned_material_to_warehouse_request(source_name, target_doc=None):
	"""Create Returned Material to Warehouse Request from Stock Entry"""

	source_doc = frappe.get_doc("Stock Entry", source_name)

	# Get project from first child row
	project = None

	if source_doc.items:
		project = source_doc.items[0].project

	if not project:
		frappe.throw(
			frappe._("Stock Entry Item must have a Project")
		)

	def set_missing_values(source, target):

		target.date = frappe.utils.today()

		# Set stock entry reference
		target.stock_entry_reference = source.name

		# Set project from child row
		target.project = project

		# Default handed by
		if not target.handed_by:
			target.handed_by = frappe.session.user

	def update_item(source_doc, target_doc, source_parent):
		"""Map Stock Entry Detail to Returned Material to Warehouse Items"""

		target_doc.item_code = source_doc.item_code
		target_doc.item_name = source_doc.item_name
		target_doc.description = source_doc.description
		target_doc.quantity = source_doc.qty
		target_doc.uom = source_doc.uom

	doclist = get_mapped_doc(
		"Stock Entry",
		source_name,
		{
			"Stock Entry": {
				"doctype": "Returned Material to Warehouse Request",
				"field_map": {
					"to_warehouse": "default_target_warehouse",
					"posting_date": "date",
					"from_warehouse": "default_target_warehouse"
				},
				"validation": {
					"docstatus": ["=", 1]
				},
			},

			"Stock Entry Detail": {
				"doctype": "Returned Material to Warehouse Items",
				"field_map": {
					"item_code": "item_code",
					"item_name": "item_name",
					"description": "description",
					"qty": "quantity",
					"uom": "uom",
					"project": "project"
				},
				"postprocess": update_item,
			},
		},
		target_doc,
		set_missing_values,
	)

	return doclist