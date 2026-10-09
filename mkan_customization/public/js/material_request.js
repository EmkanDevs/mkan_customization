const DEPT_MANDATORY_PROJECTS = [
	"Services Related to Operation and Production (Overhead)",
	"General and Administrative Expenses (G&A)",
];
const material_request_project_names = new Map();

frappe.ui.form.on("Material Request", {
	setup(frm) {
		frm.set_query("department", "items", (doc, cdt, cdn) => {
			const row = locals[cdt][cdn];
			const project_name = DEPT_MANDATORY_PROJECTS.includes(row.project)
				? row.project : material_request_project_names.get(row.project);
			// Wait for the Project name before offering Department choices.
			if (row.project && typeof project_name !== "string") {
				return { filters: { name: ["=", ""] } };
			}
			return {
				filters: project_name === "Services Related to Operation and Production (Overhead)"
					? { custom_project: row.project } : {},
			};
		});
		$(frm.wrapper).on("grid-row-render.mkan_project_dimensions", (event, grid_row) => {
			if (grid_row.doc?.doctype === "Material Request Item") {
				set_row_department_requirement(frm, grid_row.doc);
			}
		});
	},
	refresh: function (frm) {
		(frm.doc.items || []).forEach(row => set_row_department_requirement(frm, row));
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

		frm.add_custom_button(
			"PO Details Report",
			() => {
				const transaction_date = frm.doc.transaction_date || null;
				frappe.route_options = {
					material_request: frm.doc.name,
					project: frm.doc.project || null,
					from_date: transaction_date,
					to_date: transaction_date
				};
				frappe.set_route("po-details-report");
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
	custom_project(frm) {
		return Promise.all((frm.doc.items || []).map(row =>
			frappe.model.set_value(row.doctype, row.name, "project", frm.doc.custom_project || "")
		));
	},

	async validate(frm) {
		const missing = [];
		await Promise.all((frm.doc.items || []).map(async row => {
			if (!row.project && frm.doc.custom_project) {
				await frappe.model.set_value(row.doctype, row.name, "project", frm.doc.custom_project);
			}
			const required = await set_row_department_requirement(frm, row);
			if (required && !row.department) missing.push(row.idx);
		}));
		if (missing.length) {
			missing.sort((a, b) => a - b);
			frappe.throw(__("Department is mandatory for row(s): {0}", [missing.join(", ")]));
		}
		await Promise.all((frm.doc.items || []).filter(row => row.project || row.department).map(row =>
			set_row_cost_center(row.doctype, row.name)
		));
	},
});

frappe.ui.form.on("Material Request Item", {
	async items_add(frm, cdt, cdn) {
		if (frm.doc.custom_project) {
			await frappe.model.set_value(cdt, cdn, "project", frm.doc.custom_project);
		}
		await set_row_department_requirement(frm, locals[cdt][cdn]);
		await set_row_cost_center(cdt, cdn);
	},
	async project(frm, cdt, cdn) {
		await set_row_department_requirement(frm, locals[cdt][cdn]);
		await set_row_cost_center(cdt, cdn);
	},
	department(frm, cdt, cdn) {
		return set_row_cost_center(cdt, cdn);
	},
	form_render(frm, cdt, cdn) {
		return set_row_department_requirement(frm, locals[cdt][cdn]);
	},
});

async function set_row_department_requirement(frm, row) {
	const project = row.project;
	const project_name = await get_material_request_project_name(project);
	if (locals[row.doctype]?.[row.name] !== row || row.project !== project) return;
	const required = DEPT_MANDATORY_PROJECTS.includes(project_name);
	const df = frappe.meta.get_docfield(row.doctype, "department", row.name);
	if (df) df.reqd = required ? 1 : 0;
	const grid_row = frm.fields_dict.items.grid.grid_rows_by_docname[row.name];
	if (grid_row) grid_row.toggle_reqd("department", required);
	return required;
}

async function get_material_request_project_name(project) {
	if (!project || DEPT_MANDATORY_PROJECTS.includes(project)) {
		return Promise.resolve(project || "");
	}
	if (!material_request_project_names.has(project)) {
		const lookup = frappe.db.get_value("Project", project, "project_name")
			.then(r => {
				const project_name = r.message?.project_name || "";
				material_request_project_names.set(project, project_name);
				return project_name;
			})
			.catch(error => {
				material_request_project_names.delete(project);
				throw error;
			});
		material_request_project_names.set(project, lookup);
	}
	return material_request_project_names.get(project);
}

async function set_row_cost_center(cdt, cdn) {
	const row = locals[cdt][cdn];
	const { project, department } = row;
	const name = department || project;
	let cost_center = "";
	if (name) {
		const doctype = department ? "Department" : "Project";
		const result = await frappe.db.get_value(doctype, name, "cost_center");
		cost_center = result.message?.cost_center || "";
	}
	// Ignore a lookup that finished after the row changed or was deleted.
	if (locals[cdt]?.[cdn] !== row || row.project !== project || row.department !== department) return;
	await frappe.model.set_value(cdt, cdn, "cost_center", cost_center);
}
