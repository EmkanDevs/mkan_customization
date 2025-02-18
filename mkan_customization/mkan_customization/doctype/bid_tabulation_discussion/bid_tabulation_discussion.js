frappe.provide("frappe.bid_tabulation_discussion");
frappe.ui.form.on("Bid Tabulation Discussion", {
    refresh:function(frm){
        frappe.bid_tabulation_discussion.render_schedule(frm);
        frm.set_df_property('discussion', 'cannot_add_rows', true); // Hide add row button
        frm.set_df_property('discussion', 'cannot_delete_rows', true); // Hide delete button
        frm.set_df_property('discussion', 'cannot_delete_all_rows', true); // Hide delete all button
        if (frm.doc.docstatus == 1){
            console.log("hello")
            frm.add_custom_button(__("Purchase Order"), () => frm.events.make_purchase_order(frm), __("Create"));
            frm.add_custom_button(__("Quotation"), () => frm.events.make_quotation(frm), __("Create"));
        }

        if (!frm.doc.request_for_quotation) return; // Ensure RFQ exists

        frappe.call({
            method: "mkan_customization.mkan_customization.doctype.bid_tabulation_discussion.bid_tabulation_discussion.fetch_attachments_and_display",
            args: { request_for_quotation: frm.doc.request_for_quotation },
            callback: function(r) {
                if (r.message) {
                    $(frm.fields_dict.custom_html.wrapper).html(r.message);
                    console.log(frm.fields_dict.custom_html.wrapper)
                } else {
                    $(frm.fields_dict.custom_html.wrapper).html("<p>No attachments found.</p>");
                }
            }
        });
    },
    final_supplier:function(frm){
        frappe.call({
            method: "mkan_customization.mkan_customization.doctype.bid_tabulation_discussion.bid_tabulation_discussion.set_supplier_quotation_value",
            args: { request_for_quotation: frm.doc.request_for_quotation,
                    supplier:frm.doc.final_supplier
             },
            async: false, 
            callback: function(r) {
                if (r.message) {
                    frm.set_value("supplier_quotation", r.message[0]);
                    frm.save_or_update()
                }
            }
        });
    },
    make_purchase_order() {
        // Create a dialog for selecting the source name
        let dialog = new frappe.ui.Dialog({
            title: 'Select Source Name',
            fields: [
                {
                    label: 'Source Name',
                    fieldname: 'source_name',
                    fieldtype: 'Link',
                    options: 'Supplier Quotation',
                    reqd: 1,
                    default: cur_frm.doc.supplier_quotation
                }
            ],
            primary_action_label: 'Proceed',
            primary_action(values) {
                if (values.source_name) {
                    frappe.model.open_mapped_doc({
                        method: "mkan_customization.mkan_customization.doctype.bid_tabulation_discussion.bid_tabulation_discussion.make_purchase_order",
                        frm: cur_frm,
                        source_name: values.source_name,
                        args:{bid_tabulation: cur_frm.doc.name}
                    });
                    dialog.hide();
                } else {
                    frappe.msgprint(__('Please select a source name.'));
                }
               
                dialog.hide();
            }
        });

        dialog.show();
    },
    make_quotation() {
        // Create a dialog for selecting the source name
        let dialog = new frappe.ui.Dialog({
            title: 'Select Source Name',
            fields: [
                {
                    label: 'Source Name',
                    fieldname: 'source_name',
                    fieldtype: 'Link',
                    options: 'Supplier Quotation', // Specify the Doctype or options
                    reqd: 1, // Make it mandatory
                    default:cur_frm.doc.supplier_quotation
                }
            ],
            primary_action_label: 'Proceed',
            primary_action(values) {

                if (values.source_name) {
                    frappe.model.open_mapped_doc({
                        method: "mkan_customization.mkan_customization.doctype.bid_tabulation_discussion.bid_tabulation_discussion.make_quotation",
                        frm: cur_frm,
                        source_name: values.source_name,
                        args:{bid_tabulation: cur_frm.doc.name}
                    });
                    dialog.hide();
                } else {
                    frappe.msgprint(__('Please select a source name.'));
                }
            }
        });
    
        // Show the dialog
        dialog.show();
    },
    
    onload: function (frm) {
        if (frm.doc.request_for_quotation) {
            frm.set_query("supplier", function () {
                return {
                    filters: {
                        name: ["in", get_suppliers_from_rfq(frm.doc.request_for_quotation)]
                    }
                };
            });
            frm.set_query("final_supplier", function () {
                return {
                    filters: {
                        name: ["in", get_suppliers_from_rfq(frm.doc.request_for_quotation)]
                    }
                };
            });
            frm.set_query("supplier_quotation", function () {
                return {
                    filters: {
                        name: ["in", get_suppliers_quotation(frm.doc.request_for_quotation)]
                    }
                };
            });
        }
    }
});

function get_suppliers_from_rfq(rfq) {
    if(rfq){
        let suppliers = [];
        frappe.call({
            method: "mkan_customization.mkan_customization.doctype.bid_tabulation_discussion.bid_tabulation_discussion.get_supplier_options",
            args: { docname: rfq },
            async: false, 
            callback: function(r) {
                if (r.message) {
                    suppliers = r.message;
                }
            }
        });
        return suppliers;
    }
}

function get_suppliers_quotation(rfq) {
    let suppliers = [];
    frappe.call({
        method: "mkan_customization.mkan_customization.doctype.bid_tabulation_discussion.bid_tabulation_discussion.set_supplier_quotation",
        args: { request_for_quotation: rfq },
        async: false, 
        callback: function(r) {
            if (r.message) {
                request_for_quotation = r.message;
            }
        }
    });
    return request_for_quotation;
}

frappe.bid_tabulation_discussion.render_schedule = function (frm) {
    if (!frm.is_dirty()) {
        frappe.call({
            method: "mkan_customization.mkan_customization.doctype.bid_tabulation_discussion.bid_tabulation_discussion.get_supplier_details",
            args: {
                docname: frm.doc.request_for_quotation 
            },
            callback: function (r) {
                if (r.message) {
                    // frm.dashboard.reset();

                    frm.dashboard.add_section(
                        frappe.render_template(
                            "bid_tabulation_discussion",
                            { schedule_details: r.message }
                        ),
                        __("Supplier Details")
                    );

                    frm.dashboard.show();
                } else {
                    // frm.dashboard.hide();
                    frappe.msgprint({
                        title: __("No Data"),
                        indicator: "orange",
                        message: __("No supplier or item details found for the selected Request for Quotation.")
                    });
                }
            },
            error: function (err) {
                console.error("Error fetching supplier options:", err);
                frappe.msgprint({
                    title: __("Error"),
                    indicator: "red",
                    message: __("An error occurred while fetching supplier details. Please try again.")
                });
            }
        });
    } else {
        frm.dashboard.hide();
    }
};

