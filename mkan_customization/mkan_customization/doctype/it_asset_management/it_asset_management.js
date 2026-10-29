// Copyright (c) 2025, Finbyz and contributors
// For license information, please see license.txt

const ASSIGNMENT_TABLE = "custom_asset_assignment";
const ASSIGNMENT_DOCTYPE = "IT Asset Assigned User2";

// CSS guard: a locked row cannot be clicked into, whatever the grid does internally
function inject_lock_css() {
    if (document.getElementById("asset-row-lock-css")) return;
    const style = document.createElement("style");
    style.id = "asset-row-lock-css";
    style.textContent = `
        .asset-row-locked .data-row .grid-static-col:not(:has(.btn-open-row)) { pointer-events: none; }
        .asset-row-locked .form-in-grid .frappe-control { pointer-events: none; opacity: 0.7; }
        .asset-row-locked .form-in-grid .grid-delete-row,
        .asset-row-locked .form-in-grid .grid-insert-row,
        .asset-row-locked .form-in-grid .grid-insert-row-below,
        .asset-row-locked .form-in-grid .grid-move-row { display: none; }
    `;
    document.head.appendChild(style);
}

async function fetch_movement_status(frm) {
    frm._movement_status = {};
    const names = (frm.doc[ASSIGNMENT_TABLE] || [])
        .map(r => r.custom_asset_movement)
        .filter(Boolean);
    if (!names.length) return;

    const movements = await frappe.db.get_list("Asset Movement", {
        filters: { name: ["in", names] },
        fields: ["name", "docstatus"],
        limit: 0,
    });
    movements.forEach(m => (frm._movement_status[m.name] = m.docstatus));
}

function original_read_only(fieldname) {
    const meta_df = frappe.meta.get_docfield(ASSIGNMENT_DOCTYPE, fieldname);
    return meta_df && meta_df.read_only ? 1 : 0;
}

function set_field_read_only(field, read_only) {
    if (!field || !field.df) return;
    field.df.read_only = read_only;
    if (field.refresh) field.refresh();
}

function lock_row_if_needed(frm, row) {
    const grid = frm.fields_dict[ASSIGNMENT_TABLE]?.grid;
    const grid_row = grid?.grid_rows_by_docname?.[row.name];
    if (!grid_row) return;

    // locked only if the movement exists and is not cancelled (docstatus 2)
    const status = (frm._movement_status || {})[row.custom_asset_movement];
    const locked = !!row.custom_asset_movement && status !== undefined && status !== 2;

    inject_lock_css();
    grid_row.wrapper.toggleClass("asset-row-locked", locked);

    grid.docfields.forEach(df => {
        if (frappe.model.no_value_type.includes(df.fieldtype)) return;
        const fn = df.fieldname;
        const read_only = locked ? 1 : original_read_only(fn);

        // 1. the row's own column definition (new object, so other rows are not affected)
        const col = grid_row.columns && grid_row.columns[fn];
        if (col && col.df) col.df = Object.assign({}, col.df, { read_only });

        // 2. the editable control inside the grid cell (exists once the cell was activated)
        set_field_read_only(grid_row.on_grid_fields_dict?.[fn], read_only);

        // 3. the control inside the expanded row form
        set_field_read_only(grid_row.grid_form?.fields_dict?.[fn], read_only);
    });

    grid_row.wrapper.find(".grid-row-check").prop("disabled", locked);
}

function lock_all_rows(frm) {
    (frm.doc[ASSIGNMENT_TABLE] || []).forEach(row => lock_row_if_needed(frm, row));
}

frappe.ui.form.on("IT Asset Management", {
    supplier(frm) {
        frm.set_query("purchase_order", () => ({
            filters: { supplier: frm.doc.supplier },
        }));
    },
    async refresh(frm) {
        await fetch_movement_status(frm);
        lock_all_rows(frm);
        // the grid may finish rendering after the event, so apply once more
        setTimeout(() => lock_all_rows(frm), 300);
    },
    after_save(frm) {
        // the movement link is written server-side after save
        frm.reload_doc();
    },
    custom_asset_assignment_add(frm) {
        lock_all_rows(frm);
    },
    custom_asset_assignment_on_form_rendered(frm) {
        lock_all_rows(frm);
    },
});

frappe.ui.form.on(ASSIGNMENT_DOCTYPE, {
    form_render(frm, cdt, cdn) {
        lock_row_if_needed(frm, locals[cdt][cdn]);
        setTimeout(() => lock_row_if_needed(frm, locals[cdt][cdn]), 100);
    },
});


// // Copyright (c) 2025, Finbyz and contributors
// // For license information, please see license.txt

// const ASSIGNMENT_TABLE = "custom_asset_assignment";
// const ASSIGNMENT_DOCTYPE = "IT Asset Assigned User2";

// async function fetch_movement_status(frm) {
//     frm._movement_status = {};
//     const names = (frm.doc[ASSIGNMENT_TABLE] || [])
//         .map(r => r.custom_asset_movement)
//         .filter(Boolean);
//     if (!names.length) return;

//     const movements = await frappe.db.get_list("Asset Movement", {
//         filters: { name: ["in", names] },
//         fields: ["name", "docstatus"],
//         limit: 0,
//     });
//     movements.forEach(m => (frm._movement_status[m.name] = m.docstatus));
// }

// function lock_row_if_needed(frm, row) {
//     const grid = frm.fields_dict[ASSIGNMENT_TABLE]?.grid;
//     const grid_row = grid?.grid_rows_by_docname?.[row.name];
//     if (!grid_row) return;

//     // locked only if the movement exists and is not cancelled (docstatus 2)
//     const status = (frm._movement_status || {})[row.custom_asset_movement];
//     const locked = !!row.custom_asset_movement && status !== undefined && status !== 2;

//     grid.docfields.forEach(df => {
//         if (frappe.model.no_value_type.includes(df.fieldtype)) return;
//         // original setting comes from meta, which toggle_editable never mutates
//         const meta_df = frappe.meta.get_docfield(ASSIGNMENT_DOCTYPE, df.fieldname);
//         const originally_read_only = !!(meta_df && meta_df.read_only);
//         grid_row.toggle_editable(df.fieldname, !locked && !originally_read_only);
//     });

//     grid_row.wrapper.find(".grid-row-check").prop("disabled", locked);
// }

// function lock_all_rows(frm) {
//     (frm.doc[ASSIGNMENT_TABLE] || []).forEach(row => lock_row_if_needed(frm, row));
// }

// frappe.ui.form.on("IT Asset Management", {
//     supplier(frm) {
//         frm.set_query("purchase_order", () => ({
//             filters: { supplier: frm.doc.supplier },
//         }));
//     },
//     async refresh(frm) {
//         await fetch_movement_status(frm);
//         lock_all_rows(frm);
//         // the grid may finish rendering after the event, so apply once more
//         setTimeout(() => lock_all_rows(frm), 300);
//     },
//     after_save(frm) {
//         // the movement link is written server-side after save
//         frm.reload_doc();
//     },
//     custom_asset_assignment_add(frm) {
//         lock_all_rows(frm);
//     },
// });

// frappe.ui.form.on(ASSIGNMENT_DOCTYPE, {
//     form_render(frm, cdt, cdn) {
//         lock_row_if_needed(frm, locals[cdt][cdn]);
//     },
// });


// // const LOCK_FIELDS = [
// //     "assigned_user", "department", "designation", "project",
// //     "location", "from_date", "to_date", "custom_asset_movement",
// // ];

// // function lock_assignment_rows(frm) {
// //     const grid = frm.fields_dict.custom_asset_assignment?.grid;
// //     if (!grid) return;

// //     grid.grid_rows.forEach(grid_row => {
// //         const locked = !!grid_row.doc.custom_asset_movement;

// //         // grid cells
// //         grid_row.toggle_editable(LOCK_FIELDS, !locked);
// //         grid_row.wrapper.find(".grid-row-check").prop("disabled", locked);

// //         // expanded row form, if open
// //         LOCK_FIELDS.forEach(fn => {
// //             const f = grid_row.grid_form?.fields_dict?.[fn];
// //             if (f) {
// //                 f.df.read_only = locked ? 1 : 0;
// //                 f.refresh();
// //             }
// //         });
// //     });
// // }

// // // the grid can finish rendering after the event fires, so run once now and once after
// // function lock_soon(frm) {
// //     lock_assignment_rows(frm);
// //     setTimeout(() => lock_assignment_rows(frm), 300);
// // }

// // frappe.ui.form.on("IT Asset Management", {
// //     supplier(frm) {
// //         frm.set_query("purchase_order", () => ({ filters: { supplier: frm.doc.supplier } }));
// //     },
// //     refresh(frm) {
// //         lock_soon(frm);
// //     },
// //     after_save(frm) {
// //         frm.reload_doc();   // movement link is written server-side after save
// //     },
// //     custom_asset_assignment_add(frm) {
// //         lock_soon(frm);
// //     },
// //     custom_asset_assignment_on_form_rendered(frm) {
// //         lock_soon(frm);
// //     },
// // });

// // frappe.ui.form.on("IT Asset Assigned User2", {
// //     form_render(frm) {
// //         lock_soon(frm);
// //     },
// // });


// // const LOCK_FIELDS = [
// //     "assigned_user", "department", "designation", "project",
// //     "location", "from_date", "to_date", "custom_asset_movement",
// // ];

// // async function get_active_movements(frm) {
// //     const names = (frm.doc.custom_asset_assignment || [])
// //         .map(r => r.custom_asset_movement)
// //         .filter(Boolean);
// //     if (!names.length) return new Set();

// //     const movements = await frappe.db.get_list("Asset Movement", {
// //         filters: { name: ["in", names] },
// //         fields: ["name", "docstatus"],
// //         limit: 0,
// //     });
// //     return new Set(movements.filter(m => m.docstatus !== 2).map(m => m.name));
// // }

// // function apply_row_lock(grid_row, locked) {
// //     // give each row its own docfield copies so locking one row doesn't affect others
// //     if (!grid_row._docfields_cloned) {
// //         grid_row.docfields = grid_row.docfields.map(d => Object.assign({}, d));
// //         grid_row._docfields_cloned = true;
// //     }

// //     LOCK_FIELDS.forEach(fn => {
// //         const df = grid_row.docfields.find(d => d.fieldname === fn);
// //         if (df) df.read_only = locked ? 1 : 0;

// //         // row form (when the row is expanded)
// //         const f = grid_row.grid_form?.fields_dict?.[fn];
// //         if (f) {
// //             f.df.read_only = locked ? 1 : 0;
// //             f.refresh();
// //         }
// //     });

// //     grid_row.refresh();
// //     grid_row.wrapper.find(".grid-row-check").prop("disabled", locked);
// //     grid_row.wrapper.find(".btn-open-row").toggleClass("hidden", false); // keep "view" available
// // }

// // async function lock_assignment_rows(frm) {
// //     const grid = frm.fields_dict.custom_asset_assignment?.grid;
// //     if (!grid) return;

// //     const active = await get_active_movements(frm);
// //     grid.grid_rows.forEach(grid_row => {
// //         apply_row_lock(grid_row, active.has(grid_row.doc.custom_asset_movement));
// //     });
// // }

// // frappe.ui.form.on("IT Asset Management", {
// //     supplier(frm) {
// //         frm.set_query("purchase_order", () => ({ filters: { supplier: frm.doc.supplier } }));
// //     },
// //     refresh(frm) {
// //         lock_assignment_rows(frm);
// //     },
// //     after_save(frm) {
// //         // the movement link is written server-side after save
// //         frm.reload_doc();
// //     },
// //     custom_asset_assignment_on_form_rendered(frm) {
// //         lock_assignment_rows(frm);
// //     },
// //     custom_asset_assignment_add(frm) {
// //         lock_assignment_rows(frm);
// //     },
// // });

// // frappe.ui.form.on("IT Asset Assigned User2", {
// //     form_render(frm) {
// //         lock_assignment_rows(frm);
// //     },
// // });



// // // // Copyright (c) 2025, Finbyz and contributors
// // // // For license information, please see license.txt

// // // // frappe.ui.form.on("IT Asset Management", {
// // // // 	refresh(frm) {

// // // // 	},
// // // // });

// // // frappe.ui.form.on("IT Asset Management", {
// // //     supplier: function(frm) {
// // //         frm.set_query("purchase_order", function() {
// // //             return {
// // //                 filters: {
// // //                     supplier: frm.doc.supplier,
// // //                 }
// // //             };
// // //         });
// // //     },

// // // });


// // // // frappe.ui.form.on("IT Asset Management", {
// // // //     supplier: function(frm) {
// // // //         if (frm.doc.supplier) {
// // // //             frappe.call({
// // // //                 method: "frappe.client.get_list",
// // // //                 args: {
// // // //                     doctype: "Purchase Order",
// // // //                     filters: { supplier: frm.doc.supplier},
// // // //                     fields: ["name"],
// // // //                     limit_page_length: 1
// // // //                 },
// // // //                 callback: function(response) {
// // // //                     if (response.message) {
// // // //                         frm.set_value("purchase_order", response.message[0].name);
// // // //                     }
// // // //                 }
// // // //             });
// // // //         } else {
// // // //             frm.set_value("purchase_order", null);
// // // //         }
// // // //     }
// // // // });

