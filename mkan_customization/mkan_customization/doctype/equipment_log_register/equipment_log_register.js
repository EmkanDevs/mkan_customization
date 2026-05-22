frappe.ui.form.on("Equipment Log Register", {
    refresh(frm) {

        frm.fields_dict["equipment_log_item"]
            .grid.get_field("item_code").get_query = function() {

            return {
                query: "mkan_customization.mkan_customization.doc_events.item_query.get_all_items"
            };
        };

    },
});

frappe.ui.form.on("Equipment Log Item", {
    item_code: async function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (!row.item_code) return;

        let item = await frappe.db.get_doc("Item", row.item_code);

        let is_fixed_asset = item.is_fixed_asset || 0;

        frappe.model.set_value(cdt, cdn, "fixed_asset", is_fixed_asset);

        if (is_fixed_asset) {

            // Set default quantity to 1 for fixed assets
            frappe.model.set_value(cdt, cdn, "quantity", 1);

            frappe.msgprint(
                __("This item is a Fixed Asset. Tag Number is mandatory and Quantity cannot exceed 1.")
            );

        } else {

            frappe.model.set_value(cdt, cdn, "tag_number", "");
            frappe.model.set_value(cdt, cdn, "quantity", "");
        }

        frm.refresh_field("equipment_log_item");
    },

    quantity: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (row.fixed_asset && row.quantity > 1) {

            frappe.model.set_value(cdt, cdn, "quantity", 1);

            frappe.throw(__("Quantity cannot exceed 1 for Fixed Asset items."));
        }
    }
});