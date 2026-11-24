"""
One source class per doctype. Each returns normalized activity rows (spec 6.1).

SQL fragments below are fixed strings owned by this file. User input is only
ever passed as query parameters.
"""
import frappe

from mkan_customization.warehouse_kpi.txn_types import (
	DEFAULT_EXCLUDED_PURPOSES,
	MR_CREATED,
	EQUIPMENT_LOG,
	MR_ISSUED,
	classify_stock_entry,
)

STATUS_DOCSTATUS = {"Submitted": [1], "Cancelled": [2], "Submitted + Cancelled": [1, 2]}


def load_activity(ctx):
	"""Return (query, rows) for the resolved scope `ctx` (output of scope.resolve)."""
	query = ActivityQuery(ctx)
	rows = []
	for source in SOURCES:
		rows.extend(source().fetch(query))
	rows.sort(key=lambda r: (r["date"], r["name"]), reverse=True)
	return query, rows


class ActivityQuery:
	"""Validated filter values shared by every source."""

	def __init__(self, ctx):
		f = ctx["filters"]
		self.company = f.get("company")
		self.from_date = f.from_date
		self.to_date = f.to_date
		self.warehouse = f.get("warehouse")
		self.location = f.get("location")
		self.allowed_warehouses = ctx["allowed_warehouses"]
		self.docstatuses = STATUS_DOCSTATUS.get(f.get("status") or "Submitted + Cancelled")
		if self.docstatuses is None:
			frappe.throw("Invalid status filter.")
		self.users = self._resolve_users(f.get("storekeeper"), ctx["allowed_users"])
		self.purposes = self._included_purposes()

	def _resolve_users(self, storekeeper, allowed_users):
		if storekeeper:
			allowed_lower = {u.lower(): u for u in allowed_users}
			matched = allowed_lower.get(storekeeper.lower())
			return [matched or storekeeper]
		return list(allowed_users)

	def _included_purposes(self):
		text = frappe.db.get_single_value(
			"Warehouse Staff Evaluation Settings", "excluded_stock_entry_purposes"
		)
		excluded = {p.strip() for p in (text or "").splitlines() if p.strip()}
		excluded = excluded or set(DEFAULT_EXCLUDED_PURPOSES)
		wanted = {"Material Receipt", "Material Issue", "Material Transfer"}
		return list(wanted - excluded)


class DocSource:
	doctype = child = None
	date_sql = "t.posting_date"
	owner_sql = "t.owner"
	company_sql = "t.company"
	warehouse_sql = "c.warehouse"
	location_sql = "NULL"
	target_sql = "NULL"
	stock_qty_sql = "0"
	stock_uom_sql = "''"
	txn_qty_sql = "0"
	txn_uom_sql = "''"
	extras = ()  # header columns, "t.col AS alias"
	aggregates = ()  # extra SUM columns, "SUM(...) AS _alias"
	extra_join = ""
	credits_amendments = True
	is_stock_doc = True

	def fetch(self, q):
		if not self.applies(q) or not q.users:
			return []
		sql, params = self.build_sql(q)
		return self.merge(frappe.db.sql(sql, params, as_dict=True))

	def applies(self, q):
		if q.location:
			return not self.is_stock_doc
		if q.warehouse:
			return self.is_stock_doc
		return True

	def build_sql(self, q):
		conds, params = self.conditions(q)
		extras = "".join(f", {e}" for e in self.extras)
		aggregates = "".join(f", {a}" for a in self.aggregates)
		group = "".join(f", {e.split(' AS ')[0]}" for e in self.extras)
		sql = f"""
			SELECT t.name, {self.owner_sql} AS doc_owner, t.docstatus, {self.date_sql} AS doc_date,
				t.amended_from, {self._original_owner_sql()} AS original_owner,
				{self.warehouse_sql} AS _wh, {self.location_sql} AS _loc, {self.target_sql} AS _tgt,
				{self.stock_uom_sql} AS _suom, {self.txn_uom_sql} AS _tuom,
				COUNT(c.name) AS _lines, SUM({self.stock_qty_sql}) AS _sqty, SUM({self.txn_qty_sql}) AS _tqty
				{aggregates}{extras}
			FROM `tab{self.doctype}` t
			JOIN `tab{self.child}` c ON c.parent = t.name
			LEFT JOIN `tab{self.doctype}` orig ON orig.name = t.amended_from
			{self.extra_join}
			WHERE {" AND ".join(conds)}
			GROUP BY t.name, _wh, _loc, _tgt, _suom, _tuom {group}
		"""
		return sql, params

	def conditions(self, q):
		params = {
			"dt": self.doctype,
			"from_date": q.from_date,
			"to_date": q.to_date,
			"users": q.users,
			"docstatuses": self.docstatuses(q),
		}
		conds = [
			"t.docstatus IN %(docstatuses)s",
			f"{self.date_sql} BETWEEN %(from_date)s AND %(to_date)s",
			self._user_condition(),
		]
		self._add_company(q, conds, params)
		self._add_place(q, conds, params)
		self.add_extra_conditions(q, conds, params)
		return conds, params

	def docstatuses(self, q):
		return q.docstatuses

	def add_extra_conditions(self, q, conds, params):
		pass

	def classify(self, row):
		raise NotImplementedError

	def merge(self, db_rows):
		"""Fold (document x warehouse x uom) rows into one row per document."""
		docs = {}
		for r in db_rows:
			doc = docs.get(r.name) or docs.setdefault(r.name, self._new_row(r))
			doc["lines"] += r._lines
			_add_qty(doc["stock_uom_qty"], r._suom, r._sqty)
			_add_qty(doc["txn_uom_qty"], r._tuom, r._tqty)
			_add_unique(doc["warehouses"], r._wh)
			_add_unique(doc["locations"], r._loc)
			_add_unique(doc["targets"], r._tgt)
			doc["assets"] += int(r.get("_assets") or 0)
			doc["light"] += int(r.get("_light") or 0)
		return list(docs.values())

	def _new_row(self, r):
		row = {
			"doctype": self.doctype,
			"name": r.name,
			"user": r.doc_owner,
			"date": str(r.doc_date),
			"docstatus": r.docstatus,
			"amended_from": r.amended_from if self.credits_amendments else None,
			"original_owner": r.original_owner if self.credits_amendments else None,
			"lines": 0,
			"stock_uom_qty": {},
			"txn_uom_qty": {},
			"warehouses": [],
			"locations": [],
			"targets": [],
			"assets": 0,
			"light": 0,
			"elr_type": r.get("elr_type"),
			"mr_type": r.get("mr_type"),
			"stock_entry_type": r.get("stock_entry_type"),
			"ref": r.get("ref"),
		}
		row["type"] = self.classify(r)
		return row

	def _original_owner_sql(self):
		return "orig.owner" if self.credits_amendments else "NULL"

	def _user_condition(self):
		if not self.credits_amendments:
			return f"{self.owner_sql} IN %(users)s"
		return f"({self.owner_sql} IN %(users)s OR (t.amended_from IS NOT NULL AND orig.owner IN %(users)s))"

	def _add_company(self, q, conds, params):
		if q.company and self.company_sql:
			conds.append(f"{self.company_sql} = %(company)s")
			params["company"] = q.company

	def _add_place(self, q, conds, params):
		if self.is_stock_doc and q.warehouse:
			conds.append(f"{self.warehouse_sql} = %(warehouse)s")
			params["warehouse"] = q.warehouse
		elif self.is_stock_doc and q.allowed_warehouses:
			conds.append(f"{self.warehouse_sql} IN %(allowed_wh)s")
			params["allowed_wh"] = q.allowed_warehouses
		elif not self.is_stock_doc and q.location:
			conds.append(f"{self.location_sql} = %(location)s")
			params["location"] = q.location


class StockEntrySource(DocSource):
	doctype, child = "Stock Entry", "Stock Entry Detail"
	warehouse_sql = "IF(t.purpose = 'Material Receipt', c.t_warehouse, c.s_warehouse)"
	stock_qty_sql, stock_uom_sql = "c.transfer_qty", "c.stock_uom"
	txn_qty_sql, txn_uom_sql = "c.qty", "c.uom"
	extras = (
		"t.purpose AS purpose",
		"t.stock_entry_type AS stock_entry_type",
		"t.is_opening AS is_opening",
		"t.custom_petty_cash AS petty_cash",
		"t.custom_return_material_ref_doc AS ref",
	)

	def add_extra_conditions(self, q, conds, params):
		conds.append("t.purpose IN %(purposes)s")
		params["purposes"] = q.purposes or [""]

	def classify(self, r):
		return classify_stock_entry(r)


class PurchaseReceiptSource(DocSource):
	doctype, child = "Purchase Receipt", "Purchase Receipt Item"
	stock_qty_sql, stock_uom_sql = "c.stock_qty", "c.stock_uom"
	txn_qty_sql, txn_uom_sql = "c.qty", "c.uom"
	extras = ("t.is_return AS is_return",)

	def classify(self, r):
		return "Supplier Return" if r.is_return else "Purchase Receipt"


class StockReconciliationSource(DocSource):
	doctype, child = "Stock Reconciliation", "Stock Reconciliation Item"
	extras = ("t.purpose AS purpose",)

	def classify(self, r):
		return "Opening Entry" if r.purpose == "Opening Stock" else "Stock Adjustment"


class MaterialRequestSource(DocSource):
	doctype, child = "Material Request", "Material Request Item"
	date_sql = "t.transaction_date"
	warehouse_sql = "COALESCE(NULLIF(c.warehouse, ''), t.set_warehouse)"
	stock_qty_sql, stock_uom_sql = "c.stock_qty", "c.stock_uom"
	txn_qty_sql, txn_uom_sql = "c.qty", "c.uom"
	extras = ("t.material_request_type AS mr_type",)

	def classify(self, r):
		return MR_CREATED


class MaterialRequestIssuedSource(MaterialRequestSource):
	"""Credited to the user of the latest 'Issued' state change (spec 4.5)."""

	owner_sql = "iss.issued_by"
	date_sql = "DATE(iss.issued_on)"
	credits_amendments = False
	extra_join = """
		JOIN (
			SELECT sc.parent,
				SUBSTRING_INDEX(GROUP_CONCAT(sc.owner ORDER BY sc.modification_time DESC, sc.idx DESC), ',', 1) AS issued_by,
				MAX(sc.modification_time) AS issued_on
			FROM `tabState Change Items` sc
			WHERE sc.parenttype = 'Material Request' AND sc.workflow_state = 'Issued'
			GROUP BY sc.parent
		) iss ON iss.parent = t.name
	"""

	def docstatuses(self, q):
		return [1] if 1 in q.docstatuses else [0]  # [0] returns nothing for Cancelled-only

	def add_extra_conditions(self, q, conds, params):
		conds.append("t.docstatus = 1")

	def classify(self, r):
		return MR_ISSUED


class ReturnRequestSource(DocSource):
	doctype = "Returned Material to Warehouse Request"
	child = "Returned Material to Warehouse Items"
	date_sql = "t.date"
	company_sql = None  # doctype has no company field
	warehouse_sql = "t.default_target_warehouse"
	stock_qty_sql = txn_qty_sql = "c.quantity"
	stock_uom_sql = txn_uom_sql = "c.uom"

	def classify(self, r):
		return "Return Request"


class EquipmentLogSource(DocSource):
	"""Equipment Log Register: assets and light equipment (fixed_asset = 1 or 0)."""

	doctype, child = "Equipment Log Register", "Equipment Log Item"
	# The doctype has no posting date. Transfer Receipt has no date field at all, so it
	# and any blank date fall back to the creation date.
	date_sql = "COALESCE(t.receiving_date, t.return_date, DATE(t.creation))"
	company_sql = None
	warehouse_sql = "NULL"
	location_sql = "c.location"
	stock_qty_sql = txn_qty_sql = "c.quantity"
	stock_uom_sql = txn_uom_sql = "c.uom"
	extras = ("t.transaction_type AS elr_type",)
	aggregates = (
		"SUM(IFNULL(c.fixed_asset, 0) = 1) AS _assets",
		"SUM(IFNULL(c.fixed_asset, 0) = 0) AS _light",
	)
	is_stock_doc = False

	def classify(self, r):
		return EQUIPMENT_LOG


SOURCES = [
	StockEntrySource,
	PurchaseReceiptSource,
	StockReconciliationSource,
	MaterialRequestSource,
	MaterialRequestIssuedSource,
	ReturnRequestSource,
	EquipmentLogSource,
]


def _add_qty(bucket, uom, qty):
	if uom and qty:
		bucket[uom] = bucket.get(uom, 0) + float(qty)


def _add_unique(values, value):
	if value and value not in values:
		values.append(value)
