import frappe
from frappe import _

def validate_stock_blanket_exclusivity(doc, method):
    if doc.is_stock_item and doc.blanket_order_po_exemption:
        frappe.throw(
            _("You can only enable either <b>Maintain Stock</b> or <b>Blanket Order PO Exemption</b>, not both."),
            title=_("Invalid Selection")
        )



def set_item_naming(doc, method=None):
    l1 = (doc.custom_abbreviation_l1 or "").strip()
    l2 = (doc.custom_abbreviation_l2 or "").strip()
    l3 = (doc.custom_abbreviation_l3 or "").strip()
    abbr = (doc.custom_abbreviation or "").strip()

    if not all([l1, l2, l3, abbr]):
        frappe.throw(
            _("Cannot generate Item Code because one or more abbreviations are missing."),
            title=_("Missing Abbreviation")
        )

    prefix = f"{l1}-{l2}-{l3}-{abbr}-"
    like_prefix = prefix.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")

    last_item = frappe.db.sql(
        """
        SELECT name
        FROM `tabItem`
        WHERE name LIKE %s
        ORDER BY name DESC
        LIMIT 1
        FOR UPDATE
        """,
        (like_prefix + "%",),
    )

    last_number = 0
    if last_item:
        try:
            last_number = int(last_item[0][0].rsplit("-", 1)[1])
        except (ValueError, IndexError):
            last_number = 0

    next_number = last_number + 1
    item_code = f"{prefix}{next_number:04d}"

    # Just set item_code — Item's autoname ("field:item_code") will
    # copy this into doc.name right after before_insert runs.
    doc.item_code = item_code