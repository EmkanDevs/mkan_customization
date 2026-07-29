# Copyright (c) 2025, Finbyz and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc


class SubContractorRequest(Document):
	pass

@frappe.whitelist()
def create_project_sub_contracting(source_name, target_doc=None):
    def postprocess(source_doc, target_doc):
        target_doc.requires_fulfilment = 1

    doc = get_mapped_doc(
        "Sub-Contractor Request",
        source_name,
        {
            "Sub-Contractor Request": {
                "doctype": "Project Sub-Contracts",
                "field_map": {
					"date": "post_date",
					"project": "project",
					"selected_supplier":"party_name",
					"zone__area":"zone__area",
					"estimated_start_date":"start_date",
					"estimated_end_date":"end_date",
     
				},
                "validation": {
                    "docstatus": ["=", 1]
                }
            },
            "Contract Fulfilment Checklist": {
                "doctype": "Contract Fulfilment Checklist",
                "field_map": {
                    "requirement": "requirement",
                    "custom_requirement_label": "custom_requirement_label",
                    "wbs": "wbs",
                    "custom_version":"custom_version",
                    "custom_start_date":"custom_start_date",
                    "custom_end_date":"custom_end_date",
                    "wbs_short_description":"wbs_short_description",
                    "custom_quantity":"custom_quantity",
                    "custom_uom":"custom_uom",
                    "custom_uom":"custom_uom",
                    "custom_amount":"custom_amount",
                    "notes":"notes",
                    "fulfilled":"fulfilled"
                    
                }
            },
            "Contract Payment Checklist": {
                "doctype": "Contract Payment Checklist",
                "field_map": {
                    "fully_paid": "fully_paid",
                    "business_statement": "business_statement",
                    "uom": "uom",
                    "quantity":"quantity",
                    "payment_amount":"payment_amount",
                    "notes":"notes",
                    "payment_percentage":"payment_percentage"
                }
            }
        },
        target_doc,
        postprocess
    )

    return doc