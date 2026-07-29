frappe.ui.form.on("Sub-Contractor Request", {
    refresh: function (frm) {
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('Create Project Sub-Contracting'), function () {
                frappe.call({
                    method: 'mkan_customization.mkan_customization.doctype.sub_contractor_request.sub_contractor_request.create_project_sub_contracting',
                    args: {
                        source_name: frm.doc.name
                    },
                    callback: function (r) {
                        if (r.message) {
                            frappe.model.sync(r.message);
                            frappe.set_route('Form', r.message.doctype, r.message.name);
                        }
                    }
                });
            }, __('Create'));
        }
    },

    wbs_item_list: function(frm) {
        // Use project from form if filled
        if (frm.doc.project) {
            fetch_wbs_items(frm, frm.doc.project);
        } else {
            // Prompt user for project if not filled
            frappe.prompt(
                {
                    label: 'Project',
                    fieldname: 'project',
                    fieldtype: 'Link',
                    options: 'Project',
                    reqd: 1
                },
                function(values) {
                    fetch_wbs_items(frm, values.project);
                },
                'Select Project',
                'Next'
            );
        }
    }
});

// helper function to fetch WBS items and show selection dialog
function fetch_wbs_items(frm, project) {
    frappe.call({
        method: "frappe.client.get_list",
        args: {
            doctype: "BOQ",
            filters: { project: project },
            fields: ["name"]
        },
        callback: function(res) {
            const boq_names = res.message.map(r => r.name);
            if (boq_names.length === 0) {
                frappe.msgprint("No BOQs found for the selected project.");
                return;
            }

            frappe.call({
                method: "project_costing.project_costing.doc_events.material_request.get_boq_wbs_items",
                args: { boq_names },
                callback: function(r) {
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
                        function(item_values) {
                            const selected = item_map[item_values.selected_item];

                            if (!selected) {
                                frappe.msgprint("Selected item not found in WBS list.");
                                return;
                            }

                            const row = frm.add_child("bill_of_quantity");
                            row.requirement = selected.item_code;
                            row.custom_requirement_label = selected.item_name;
                            row.custom_uom = selected.uom;
                            row.custom_quantity = 1;
                            row.custom_wbs = selected.wbs_name;
                            frm.refresh_field("bill_of_quantity");

                            frappe.msgprint(`Added: ${selected.label}`);
                        },
                        'Choose WBS Item',
                        'Add Item'
                    );
                }
            });
        }
    });
}
