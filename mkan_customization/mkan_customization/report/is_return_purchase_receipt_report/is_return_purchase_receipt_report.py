import frappe
from frappe import _

MONTHS = ["January", "February", "March", "April", "May", "June", "July",
          "August", "September", "October", "November", "December"]


RETURN_REASON_DOCTYPE = "Common Return Reason"
# Fallback fieldnames, only used if auto-detection by link target / label fails
REASON_FIELD_CANDIDATES = ["custom_return_reason", "return_reason", "cpc_return_reason", "custom_common_return_reason"]
CRR_CANDIDATES = {
	"suggested_comment": ["suggested_comment", "suggested_comment_for_the_report", "comment"],
	"evidence": ["evidence", "evidence_follow_up_to_capture", "evidence__follow_up_to_capture", "follow_up"],
	"suggested_action": ["suggested_action", "action"],
}


def get_reason_fieldname():
	"""Find the return-reason field on Purchase Receipt Item (by link target, then label, then name)."""
	meta = frappe.get_meta("Purchase Receipt Item")
	for df in meta.fields:
		if df.options == RETURN_REASON_DOCTYPE:
			return df.fieldname
	for df in meta.fields:
		if "return reason" in (df.label or "").lower():
			return df.fieldname
	for name in REASON_FIELD_CANDIDATES:
		if frappe.db.has_column("Purchase Receipt Item", name):
			return name
	return None


def get_crr_column(key):
	if not frappe.db.exists("DocType", RETURN_REASON_DOCTYPE):
		return "NULL"
	for name in CRR_CANDIDATES[key]:
		if frappe.db.has_column(RETURN_REASON_DOCTYPE, name):
			return f"crr.`{name}`"
	return "NULL"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	def col(label, fieldname, fieldtype, width, options=None):
		d = {"label": _(label), "fieldname": fieldname, "fieldtype": fieldtype, "width": width}
		if options:
			d["options"] = options
		return d

	return [
		col("Purchase Receipt No.", "name", "Link", 180, "Purchase Receipt"),
		col("Original Purchase Receipt No.", "return_against", "Link", 180, "Purchase Receipt"),
		col("Return Date", "posting_date", "Date", 100),
		col("Project Code", "project", "Link", 140, "Project"),
		col("Project Name", "project_name", "Data", 180),
		col("Supplier Code", "supplier", "Link", 140, "Supplier"),
		col("Supplier Name", "supplier_name", "Data", 200),
		col("Purchase Request No.", "material_request", "Link", 180, "Material Request"),
		col("Purchase Request Date", "mr_date", "Date", 120),
		col("Purchase Request Requested QTYs", "mr_qty", "Float", 150),
		col("Purchase Order No.", "purchase_order", "Link", 180, "Purchase Order"),
		col("Purchase Order Date", "po_date", "Date", 120),
		col("Purchase Order Original QTYs", "po_qty", "Float", 150),
		col("QTYs Previously Received", "prior_net_qty", "Float", 150),
		col("Current Receipt QTYs", "current_qty", "Float", 130),
		col("Total QTYs Received", "net_qty", "Float", 130),
		col("QTYs Accepted/Retained", "accepted_qty", "Float", 140),
		col("QTYs Returned", "returned_qty", "Float", 120),
		col("Qty Outstanding vs Purchase Order", "outstanding_qty", "Float", 180),
		col("Return Rate %", "return_rate", "Percent", 110),
		col("Item/Material Code", "item_code", "Link", 160, "Item"),
		col("Item Name", "item_name", "Data", 200),
		col("Item Group", "item_group", "Link", 140, "Item Group"),
		col("UOM", "uom", "Link", 80, "UOM"),
		col("Return Reason", "return_reason", "Link", 220, "Common Return Reason"),
		col("Suggested Comment for the Report", "suggested_comment", "Small Text", 300),
		col("Evidence / Follow-up to Capture", "evidence", "Small Text", 250),
		col("Suggested Action", "suggested_action", "Small Text", 250),
		col("Created by Owner", "owner", "Link", 180, "User"),
		col("Workflow State", "workflow_state", "Data", 130),
		col("Status", "status", "Data", 120),
	]


def get_data(filters):
	conditions = ["pr.docstatus <> 2", "pr.is_return = 1"]
	reason_field = get_reason_fieldname()
	if reason_field:
		reason_select = f"pri.`{reason_field}`"
		crr_join = (
			f"LEFT JOIN `tab{RETURN_REASON_DOCTYPE}` crr ON crr.name = pri.`{reason_field}`"
			if frappe.db.exists("DocType", RETURN_REASON_DOCTYPE)
			else ""
		)
	else:
		# Field not created yet: report still runs, reason columns stay empty
		frappe.msgprint(
			_("Return reason field not found on Purchase Receipt Item; reason columns will be empty."),
			indicator="orange",
		)
		reason_select, crr_join = "NULL", ""

	if filters.return_against:
		conditions.append("pr.return_against = %(return_against)s")
	if filters.year:
		conditions.append("YEAR(pr.posting_date) = %(year)s")
	if filters.month:
		filters.month_no = MONTHS.index(filters.month) + 1
		conditions.append("MONTH(pr.posting_date) = %(month_no)s")
	if filters.owner:
		conditions.append("pr.owner = %(owner)s")
	if filters.item_code:
		conditions.append("pri.item_code = %(item_code)s")
	if filters.item_group:
		conditions.append("COALESCE(pri.item_group, i.item_group) = %(item_group)s")
	if filters.supplier:
		conditions.append("pr.supplier = %(supplier)s")
	if filters.project:
		conditions.append("COALESCE(pri.project, pr.project, poi.project) = %(project)s")
	if filters.material_request:
		conditions.append("pri.material_request = %(material_request)s")
	if filters.purchase_order:
		conditions.append("pri.purchase_order = %(purchase_order)s")
	if filters.workflow_state:
		conditions.append("pr.workflow_state = %(workflow_state)s")

	return frappe.db.sql(
		f"""
		SELECT
			pr.name,
			pr.return_against,
			pr.posting_date,
			COALESCE(pri.project, pr.project, poi.project) AS project,
			COALESCE(p.project_name, '') AS project_name,
			pr.supplier,
			pr.supplier_name,
			pri.material_request,
			mr.transaction_date AS mr_date,
			COALESCE(mri.qty, 0) AS mr_qty,
			pri.purchase_order,
			po.transaction_date AS po_date,
			COALESCE(poi.qty, 0) AS po_qty,

			/* Net received before this return (current return excluded when submitted) */
			COALESCE(net_receipts.net_qty, 0)
				+ IF(pr.docstatus = 1, ABS(pri.qty), 0) AS prior_net_qty,

			ABS(pri.qty) AS current_qty,
			COALESCE(net_receipts.net_qty, 0) AS net_qty,
			COALESCE(net_receipts.net_qty, 0) AS accepted_qty,
			COALESCE(return_totals.returned_qty, 0) AS returned_qty,
			GREATEST(COALESCE(poi.qty, 0) - COALESCE(net_receipts.net_qty, 0), 0) AS outstanding_qty,
			CASE WHEN COALESCE(poi.qty, 0) > 0
				THEN ROUND(100 * COALESCE(return_totals.returned_qty, 0) / poi.qty, 2)
				ELSE 0 END AS return_rate,

			pri.item_code,
			COALESCE(pri.item_name, i.item_name) AS item_name,
			COALESCE(pri.item_group, i.item_group) AS item_group,
			pri.uom,

			{reason_select} AS return_reason,
			{get_crr_column('suggested_comment')} AS suggested_comment,
			{get_crr_column('evidence')} AS evidence,
			{get_crr_column('suggested_action')} AS suggested_action,

			pr.owner,
			pr.workflow_state,
			pr.status
		FROM `tabPurchase Receipt` pr
		INNER JOIN `tabPurchase Receipt Item` pri ON pri.parent = pr.name
		LEFT JOIN `tabPurchase Order` po ON po.name = pri.purchase_order
		LEFT JOIN `tabPurchase Order Item` poi ON poi.name = pri.purchase_order_item
		LEFT JOIN `tabMaterial Request` mr ON mr.name = pri.material_request
		LEFT JOIN `tabMaterial Request Item` mri ON mri.name = pri.material_request_item
		LEFT JOIN `tabProject` p ON p.name = COALESCE(pri.project, pr.project, poi.project)
		LEFT JOIN `tabItem` i ON i.name = pri.item_code
		{crr_join}

		/* Net receipts per PO item (receipts minus returns, submitted only) */
		LEFT JOIN (
			SELECT pri3.purchase_order_item,
				SUM(CASE WHEN pr3.is_return = 1 THEN -ABS(pri3.qty) ELSE ABS(pri3.qty) END) AS net_qty
			FROM `tabPurchase Receipt Item` pri3
			INNER JOIN `tabPurchase Receipt` pr3 ON pr3.name = pri3.parent
			WHERE pr3.docstatus = 1
			GROUP BY pri3.purchase_order_item
		) net_receipts ON net_receipts.purchase_order_item = pri.purchase_order_item

		/* Cumulative returned qty per PO item */
		LEFT JOIN (
			SELECT pri4.purchase_order_item, SUM(ABS(pri4.qty)) AS returned_qty
			FROM `tabPurchase Receipt Item` pri4
			INNER JOIN `tabPurchase Receipt` pr4 ON pr4.name = pri4.parent
			WHERE pr4.docstatus = 1 AND pr4.is_return = 1
			GROUP BY pri4.purchase_order_item
		) return_totals ON return_totals.purchase_order_item = pri.purchase_order_item

		WHERE {" AND ".join(conditions)}
		ORDER BY pr.posting_date DESC, pr.name DESC, pri.idx ASC
		""",
		filters,
		as_dict=True,
	)