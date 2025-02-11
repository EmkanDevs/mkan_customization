// Copyright (c) 2025, Finbyz and contributors
// For license information, please see license.txt

frappe.ui.form.on("Petty Cash Request", {
    refresh(frm) {
        frm.set_query("employee", function () {
            return {
                filters: {
                    user_id: frappe.session.user,
                    docstatus:1
                }
            };
        });
    }
});
