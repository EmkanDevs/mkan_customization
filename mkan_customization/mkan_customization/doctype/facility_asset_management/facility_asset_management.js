// Copyright (c) 2025, Finbyz and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Facility Asset Management", {
// 	refresh(frm) {

// 	},
// });

frappe.ui.form.on("Facility Asset Management", {
    supplier: function(frm) {
        frm.set_query("purchase_order", function() {
            return {
                filters: {
                    supplier: frm.doc.supplier,
                }
            };
        });
    },
});