// Copyright (c) 2026, Finbyz and contributors
// For license information, please see license.txt


frappe.ui.form.on('Accounting Entry Settings', {
    setup: function (frm) {
        frm.set_query('default_purchase_item', function () {
            return {
                filters: {
                    is_purchase_item: 1,
                    disabled: 0
                }
            };
        });

        frm.set_query('default_sales_item', function () {
            return {
                filters: {
                    is_sales_item: 1,
                    disabled: 0
                }
            };
        });

        frm.set_query('default_supplier', function () {
            return {
                filters: {
                    disabled: 0
                }
            };
        });

        frm.set_query('default_customer', function () {
            return {
                filters: {
                    disabled: 0
                }
            };
        });
    }
});

