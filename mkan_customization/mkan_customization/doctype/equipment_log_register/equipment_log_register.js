frappe.ui.form.on("Equipment Log Register", {
    refresh(frm) {
        set_uom_query(frm);

        frm._equipment_log_uom_map = frm._equipment_log_uom_map || {};
        (frm.doc.equipment_log_item || []).forEach(async row => {
            if (row.item_code && !frm._equipment_log_uom_map[row.name]) {
                let item = await frappe.db.get_doc("Item", row.item_code);
                let allowed = [item.stock_uom];
                (item.uoms || []).forEach(u => {
                    if (u.uom && !allowed.includes(u.uom)) allowed.push(u.uom);
                });
                frm._equipment_log_uom_map[row.name] = allowed;
            }
        });

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
            frappe.model.set_value(cdt, cdn, "quantity", 1);
            frappe.msgprint(
                __("This item is a Fixed Asset. Tag Number is mandatory and Quantity cannot exceed 1.")
            );
        } else {
            frappe.model.set_value(cdt, cdn, "tag_number", "");
            frappe.model.set_value(cdt, cdn, "quantity", "");
        }

        // Build the list of UOMs valid for this item: stock UOM + alternate UOMs
        let allowed_uoms = [item.stock_uom];
        (item.uoms || []).forEach(u => {
            if (u.uom && !allowed_uoms.includes(u.uom)) allowed_uoms.push(u.uom);
        });

        // Cache it against this row so set_query can look it up later
        frm._equipment_log_uom_map = frm._equipment_log_uom_map || {};
        frm._equipment_log_uom_map[cdn] = allowed_uoms;

        // Default the UOM to the item's stock UOM
        frappe.model.set_value(cdt, cdn, "uom", item.stock_uom);

        frm.refresh_field("equipment_log_item");
    },

    quantity: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.fixed_asset && row.quantity > 1) {
            frappe.model.set_value(cdt, cdn, "quantity", 1);
            frappe.throw(__("Quantity cannot exceed 1 for Fixed Asset items."));
        }
    },

    equipment_log_item_add: function(frm, cdt, cdn) {
        // Ensure the query filter is registered as soon as a row exists
        set_uom_query(frm);
    }
});

function set_uom_query(frm) {
    frm.set_query("uom", "equipment_log_item", function(doc, cdt, cdn) {
        let allowed = (frm._equipment_log_uom_map && frm._equipment_log_uom_map[cdn]) || [];
        if (!allowed.length) {
            // No item selected yet on this row — fall back to no filter
            return {};
        }
        return {
            filters: { name: ["in", allowed] }
        };
    });
}