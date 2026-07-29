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
        frm.add_custom_button("View Stock Entries", () => {
            frappe.call({
                method: "mkan_customization.mkan_customization.doctype.project_sub_contracts.project_sub_contracts.get_stock_entries",
                args: {
                    project : frm.doc.project,
                    supplier: frm.doc.party_name,
                    start_date: frm.doc.start_date,
                    end_date: frm.doc.end_date
                },
                callback(r) {
                    if (r.message && r.message.length > 0) {
                        console.log(r.message)
                        show_stock_entries_popup(r.message);
                        console.log(r.message)
                    } else {
                        frappe.msgprint("No Stock Entries found.");
                    }
                }
            });
        });
        frm.add_custom_button("View Stock Entry Items", () => {
            frappe.call({
                method: "mkan_customization.mkan_customization.doctype.project_sub_contracts.project_sub_contracts.get_stock_entry_items",
                args: {
                    project : frm.doc.project,
                    supplier: frm.doc.party_name,
                    start_date: frm.doc.start_date,
                    end_date: frm.doc.end_date
                },
                callback(r) {
                    if (r.message && r.message.length > 0) {
                        console.log(r.message)
                        show_stock_entry_items_popup(r.message);
                    } else {
                        frappe.msgprint("No Stock Entry Items found.");
                    }
                }
            });
        });
        if (frm.doc.docstatus == 1 && frm.doc.completed_contract == 0) {
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
                            error: function (err) {
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

            }, 'Create');
            frm.add_custom_button("Invoice Released Memo", () => {
                frappe.call({
                    method: "mkan_customization.mkan_customization.doctype.project_sub_contracts.project_sub_contracts.invoice_released_memo_map",
                    args: {
                        source_name: cur_frm.doc.name
                    },
                    callback: function (r) {
                        if (r.message) {
                            frappe.model.sync(r.message);
                            frappe.set_route("Form", r.message.doctype, r.message.name);
                        }
                    }
                });
            }, 'Create');
            show_po_wpr_irm_data(frm);
        };
        if (!frm.is_new()) {
            frm.add_custom_button(__('Complete Contract'), function () {
                frappe.call({
                    method: "mkan_customization.mkan_customization.doctype.project_sub_contracts.project_sub_contracts.complete_contract",
                    args: { docname: frm.doc.name },
                    callback(r) {
                        if (!r.exc) {
                            if (r.message.skipped) {
                                frappe.msgprint(r.message.reason);
                            } else {
                                frappe.msgprint("Contract marked as completed and WBS updated.");
                                frm.reload_doc();
                            }
                        }
                    }
                });
            }, __("Actions"));
        }
    },


    onload: function (frm) {
        if (frm.doc.docstatus === 1) {
            show_po_wpr_irm_data(frm);
        }
    },
    wbs_item_list: function (frm) {
        const selected_project = frm.doc.project;

        if (!selected_project) {
            frappe.msgprint("Please select a Project in this document before adding WBS items.");
            return;
        }

        // Fetch BOQs linked to the selected project
        frappe.call({
            method: "frappe.client.get_list",
            args: {
                doctype: "BOQ",
                filters: { project: selected_project },
                fields: ["name"]
            },
            callback: function (res) {
                const boq_names = res.message.map(r => r.name);
                if (boq_names.length === 0) {
                    frappe.msgprint("No BOQs found for the selected project.");
                    return;
                }

                frappe.call({
                    method: "project_costing.project_costing.doc_events.material_request.get_boq_wbs_items",
                    args: { boq_names },
                    callback: function (r) {
                        const options = r.message || [];

                        if (options.length === 0) {
                            frappe.msgprint("No WBS Items with linked Items found.");
                            return;
                        }

                        const item_map = {};
                        const valid_item_codes = [];

                        for (let opt of options) {
                            item_map[opt.item_code] = opt;
                            valid_item_codes.push(opt.item_code);
                        }

                        frappe.prompt(
                            {
                                label: 'Select WBS Item',
                                fieldname: 'selected_item',
                                fieldtype: 'Link',
                                options: 'Item',
                                get_query: () => ({
                                    filters: [["Item", "name", "in", valid_item_codes]]
                                }),
                                description: 'Choose item code linked to WBS',
                                reqd: 1
                            },
                            function (item_values) {
                                const selected = item_map[item_values.selected_item];

                                if (!selected) {
                                    frappe.msgprint("Selected item not found in WBS list.");
                                    return;
                                }

                                // 🔹 Fetch qty and unit_cost from the WBS Item doctype
                                frappe.call({
                                    method: "frappe.client.get",
                                    args: {
                                        doctype: "WBS item",
                                        name: selected.wbs_name
                                    },
                                    callback: function (res) {
                                        if (!res.message) {
                                            frappe.msgprint(`Could not fetch WBS Item: ${selected.wbs_name}`);
                                            return;
                                        }

                                        const wbs_item = res.message;

                                        const row = frm.add_child("fulfilment_terms");
                                        row.requirement = selected.item_code;
                                        row.custom_requirement_label = selected.item_name;
                                        row.custom_uom = selected.uom;
                                        row.custom_quantity = 1;
                                        row.custom_wbs = selected.wbs_name;
                                        row.custom_boq_qty = wbs_item.qty || 0;       // 🔸 from WBS Item
                                        row.custom_rate = wbs_item.unit_cost || 0;    // 🔸 from WBS Item

                                        frm.refresh_field("fulfilment_terms");

                                        frappe.msgprint(`Added: ${selected.item_name}`);
                                    }
                                });
                            },
                            'Choose WBS Item',
                            'Add Item'
                        );
                    }
                });
            }
        });
    }
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


frappe.ui.form.on('Contract Fulfilment Checklist', {
    requirement: function (frm, cdt, cdn) {
        set_item_name(frm, cdt, cdn)
    }
});

function set_item_name(frm, cdt, cdn) {

    var row = locals[cdt][cdn];
    if (row.requirement) {

        // Fetch item details using the selected 'Requirement' (linked Item)
        frappe.call({
            method: 'frappe.client.get',
            args: {
                doctype: 'Item',
                name: row.requirement
            },
            callback: function (response) {
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

function show_stock_entries_popup(data) {
    let fields = [
        {
            fieldname: "html_table",
            fieldtype: "HTML",
            label: "Stock Entries",
        }
    ];

    let d = new frappe.ui.Dialog({
        title: "Stock Entries (Send to Subcontractor)",
        size: "extra-large",
        fields: fields
    });

    let table_html = `
        <table class="table table-bordered table-hover">
            <thead>
                <tr>
                    <th>Stock Entry</th>
                    <th>Posting Date</th>
                    <th>Supplier</th>
                    <th>Default Warehouse</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                ${data.map(row => `
                    <tr>
                        <td><a href="/app/stock-entry/${row.name}" target="_blank">${row.name}</a></td>
                        <td>${row.posting_date}</td>
                        <td>${row.custom_supplier_code}</td>
                        <td>${row.from_warehouse}</td>
                        <td>${row.docstatus == 1 ? "Submitted" : "Draft"}</td>
                    </tr>`).join("")}
            </tbody>
        </table>
    `;

    d.fields_dict.html_table.$wrapper.html(table_html);

    d.show();
}

function show_stock_entry_items_popup(data) {
    let d = new frappe.ui.Dialog({
        title: "Stock Entry Items (Send to Subcontractor)",
        size: "extra-large",
        fields: [
            {
                fieldname: "html_table",
                fieldtype: "HTML"
            }
        ]
    });

    let table_html = `
        <table class="table table-bordered table-hover">
            <thead>
                <tr>
                    <th>Stock Entry</th>
                    <th>Item Code</th>
                    <th>Item Name</th>
                    <th>Qty</th>
                    <th>UOM</th>
                    <th>Basic Rate</th>
                    <th>Source Warehouse</th>
                    <th>Target Warehouse</th>
                </tr>
            </thead>
            <tbody>
                ${data.map(row => `
                    <tr>
                        <td><a href="/app/stock-entry/${row.parent}" target="_blank">${row.parent}</a></td>
                        <td>${row.item_code}</td>
                        <td>${row.item_name}</td>
                        <td>${row.qty}</td>
                        <td>${row.uom}</td>
                        <td>${row.basic_rate}</td>
                        <td>${row.s_warehouse || ""}</td>
                        <td>${row.t_warehouse || ""}</td>
                    </tr>
                `).join("")}
            </tbody>
        </table>
    `;

    d.fields_dict.html_table.$wrapper.html(table_html);
    d.show();
}