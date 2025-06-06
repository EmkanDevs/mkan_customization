// // Copyright (c) 2025, Finbyz and contributors
// // For license information, please see license.txt

frappe.ui.form.on('Project Sub-Contracts', {
    start_date(frm) {
    // If start_date is changed in parent, update all child rows
    if (frm.doc.start_date && frm.doc.fulfilment_terms) {
        frm.doc.fulfilment_terms.forEach(row => {
            row.custom_start_date = frm.doc.start_date;
        });
        frm.refresh_field('fulfilment_terms');
        }
    },
    end_date(frm) {
    // If start_date is changed in parent, update all child rows
    if (frm.doc.end_date && frm.doc.fulfilment_terms) {
        frm.doc.fulfilment_terms.forEach(row => {
            row.custom_end_date = frm.doc.end_date;
        });
        frm.refresh_field('fulfilment_terms');
        }
    },
    refresh(frm) {
        if (frm.doc.docstatus == 1) {
            frm.add_custom_button("Purchase Order", () => {
                // Create the dialog box for supplier and version input
                const dialog = new frappe.ui.Dialog({
                    title: 'Create Purchase Order',
                    fields: [
                        {
                            label: 'Supplier',
                            fieldname: 'supplier',
                            fieldtype: 'Link',
                            options: 'Supplier',
                            default: frm.doc.party_name
                        },
                        {
                            label: 'Version',
                            fieldname: 'custom_version',
                            fieldtype: 'Int',
                            reqd: 1 // Making version field required
                        }
                    ],
                    primary_action_label: 'Create',
                    primary_action(values) {
                        // Close the dialog after submission
                        dialog.hide();

                        // Perform backend call to create the purchase orders
                        frappe.call({
                            method: 'mkan_customization.mkan_customization.doctype.project_sub_contracts.project_sub_contracts.create_multiple_purchase_orders',
                            args: {
                                docname: frm.doc.name,
                                version: values.custom_version, // Pass the selected version
                                supplier: values.supplier || frm.doc.party_name // Pass the supplier or default to null
                            },
                            callback(r) {
                                if (!r.exc) {
                                    const po_names = r.message; // PO names returned from backend
                                    if (po_names.length) {
                                        // Generate links for each PO created
                                        const links = po_names.map(po => `<a href="/app/purchase-order/${po}" target="_blank">${po}</a>`);
                                        frappe.msgprint({
                                            title: "Purchase Orders Created",
                                            message: `Created: ${links.join(", ")}`,
                                            indicator: "green"
                                        });
                                        frm.reload_doc(); // Reload the current document to reflect changes
                                    } else {
                                        frappe.msgprint("No Purchase Orders were created.");
                                    }
                                } else {
                                    frappe.msgprint("An error occurred while creating the Purchase Orders.");
                                }
                            },
                            error: function(err) {
                                // Fallback in case of network/server errors
                                console.log("")
                            }
                        });
                    }
                });

                dialog.show(); // Show the dialog
            }, 'Create');
            frm.add_custom_button("Work Progress Report", () => {
                frappe.model.open_mapped_doc({
                    method: "mkan_customization.mkan_customization.doctype.project_sub_contracts.project_sub_contracts.work_progress_report_map",
                    source_name: cur_frm.doc.name,
                });

            },'Create');
            frm.add_custom_button("Invoice Released Memo", () => {
                frappe.call({
                    method: "mkan_customization.mkan_customization.doctype.project_sub_contracts.project_sub_contracts.invoice_released_memo_map",
                    args: {
                        source_name: cur_frm.doc.name
                    },
                    callback: function(r) {
                        if (r.message) {
                            frappe.model.sync(r.message);
                            frappe.set_route("Form", r.message.doctype, r.message.name);
                        }
                    }
                });
            },'Create');
            show_po_wpr_irm_data(frm);
        };
        

    },


    onload: function (frm) {
        if (frm.doc.docstatus === 1) {
            show_po_wpr_irm_data(frm);
        }
    },
    // refresh: function (frm) {
    //     if (frm.doc.docstatus === 1) {
    //         show_po_wpr_irm_data(frm);
    //     }
    // }
});

function show_po_wpr_irm_data(frm) {
    frappe.call({
        method: "mkan_customization.mkan_customization.doctype.project_sub_contracts.project_sub_contracts.fetch_po_wpr_ipm",
        args: {
            project_sub_contracts: frm.doc.name
        },
        callback: function (r) {
            if (r.message) {
                $(frm.fields_dict.custom_html_tab.wrapper).html(r.message);

                // Optional: bind custom click handlers if needed
                $(".remove-pr").click(function () {
                    let pr_name = $(this).data("pr");
                    clear_project_sub_contracts(pr_name, frm);  // Define this function if required
                });
            } else {
                frm.fields_dict.custom_html_tab.$wrapper.html("<p>No linked records found.</p>");
            }
        }
    });
}


frappe.ui.form.on('Contract Fulfilment Checklist',{
    requirement: function(frm,cdt,cdn){
        set_item_name(frm,cdt,cdn)
    }
});
    
function set_item_name(frm,cdt,cdn){
    
    var row = locals[cdt][cdn];
    if (row.requirement) {
        
        // Fetch item details using the selected 'Requirement' (linked Item)
        frappe.call({
            method: 'frappe.client.get',
            args: {
                doctype: 'Item',
                name: row.requirement
            },
            callback: function(response) {
                console.log()
                const item = response.message;
                if (item) {
                    // Set the item_code and item_name to the Requirement Label field
                    frappe.model.set_value(cdt, cdn, 'custom_requirement_label', `${item.item_code} : ${item.item_name}`);
                }
            }
        })
    }
}

