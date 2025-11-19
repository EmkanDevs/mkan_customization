frappe.ui.form.on("Material Request", {
    refresh: function (frm) {
		frm.events.make_custom_buttons(frm);
		frm.toggle_reqd("customer", frm.doc.material_request_type == "Customer Provided");
		frm.add_custom_button(
			"Material Request Transfers Report",
			() => {
				let transaction_date = frm.doc.transaction_date;
				
				frappe.set_route("query-report", "Material Request Transfers Report", {
					material_request: frm.doc.name,
					from_date: transaction_date,  // Pass as-is
					to_date: transaction_date
				});
			},
			__("Report")
		);
	},
    make_custom_buttons: function (frm) {
		if (frm.doc.docstatus == 0) {
			frm.add_custom_button(
				__("Bill of Materials"),
				() => frm.events.get_items_from_bom(frm),
				__("Get Items From")
			);
		}

		if (frm.doc.docstatus == 1 && frm.doc.status != "Stopped") {
			let precision = frappe.defaults.get_default("float_precision");

			if (flt(frm.doc.per_received, precision) < 100) {
				frm.add_custom_button(__("Stop"), () => frm.events.update_status(frm, "Stopped"));
			}

			if (flt(frm.doc.per_ordered, precision) < 100) {
				let add_create_pick_list_button = () => {
					frm.add_custom_button(
						__("Pick List"),
						() => frm.events.create_pick_list(frm),
						__("Create")
					);
				};

				if (frm.doc.material_request_type === "Material Transfer") {
					add_create_pick_list_button();
					frm.add_custom_button(
						__("Material Transfer"),
						() => frm.events.make_stock_entry(frm),
						__("Create")
					);

					frm.add_custom_button(
						__("Material Transfer (In Transit)"),
						() => frm.events.make_in_transit_stock_entry(frm),
						__("Create")
					);
				}

				if (frm.doc.material_request_type === "Material Issue") {
					frm.add_custom_button(
						__("Issue Material"),
						() => frm.events.make_stock_entry(frm),
						__("Create")
					);
				}

				if (frm.doc.material_request_type === "Customer Provided") {
					frm.add_custom_button(
						__("Material Receipt"),
						() => frm.events.make_stock_entry(frm),
						__("Create")
					);
				}

				if (frm.doc.material_request_type === "Purchase") {
					frm.add_custom_button(
                __("Purchase Order"),
                () => {
                    frappe.call({
                        method: "mkan_customization.mkan_customization.doc_events.material_request.validate_before_po_creation",
                        args: {
                            material_request: frm.doc.name
                        },
                        callback: function (r) {
                            // Defensive check
                            if (r.message === true) {
                                frm.events.make_purchase_order(frm);
                            } else if (typeof r.message === "string") {
                                frappe.throw(__(r.message));
                            } else {
                                frappe.throw(__("Something went wrong. Please contact your administrator."));
                            }
                        }
                    });
                },
                __("Create")
            );

					frm.add_custom_button(
						__("Request for Quotation"),
						() => frm.events.make_request_for_quotation(frm),
						__("Create")
					);

					frm.add_custom_button(
						__("Supplier Quotation"),
						() => frm.events.make_supplier_quotation(frm),
						__("Create")
					);
				}

				if (frm.doc.material_request_type === "Manufacture") {
					frm.add_custom_button(
						__("Work Order"),
						() => frm.events.raise_work_orders(frm),
						__("Create")
					);
				}

				if (frm.doc.material_request_type === "Subcontracting") {
					frm.add_custom_button(
						__("Subcontracted Purchase Order"),
						() => frm.events.make_purchase_order(frm),
						__("Create")
					);
				}

				frm.page.set_inner_btn_group_as_primary(__("Create"));
			}
		}

		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(
				__("Sales Order"),
				() => frm.events.get_items_from_sales_order(frm),
				__("Get Items From")
			);
		}

		if (frm.doc.docstatus == 1 && frm.doc.status == "Stopped") {
			frm.add_custom_button(__("Re-open"), () => frm.events.update_status(frm, "Submitted"));
		}
	},
})