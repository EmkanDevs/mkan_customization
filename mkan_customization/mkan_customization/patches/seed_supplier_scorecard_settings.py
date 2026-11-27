"""Create the Supplier Scorecard Settings from the sample values, plus any missing criteria records."""
import frappe

from mkan_customization.mkan_customization.doctype.supplier_scorecard_settings.defaults import seed_settings


def execute():
	for doctype in ("supplier_scorecard_setting_criterion", "supplier_scorecard_rating_rule",
			"supplier_scorecard_band", "supplier_scorecard_settings"):
		frappe.reload_doc("Mkan Customization", "doctype", doctype)
	seed_settings()
