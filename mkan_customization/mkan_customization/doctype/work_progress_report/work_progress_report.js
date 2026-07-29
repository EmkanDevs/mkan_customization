// Copyright (c) 2025, Finbyz and contributors
// For license information, please see license.txt

frappe.ui.form.on("Work Progress Report", {
    select_item: function(frm) {
        show_item_selector_dialog(frm);
    }
});

function show_item_selector_dialog(frm) {
    const child_table = frm.doc.work_progress_detail || [];

    if (!child_table.length) {
        frappe.msgprint(__('No items available in the child table.'));
        return;
    }

    // Track which items are checked across filters
    const selected_rows_map = {};

    const d = new frappe.ui.Dialog({
        title: 'Select Material Request',
        fields: [
            {
                fieldname: 'item_search',
                fieldtype: 'Data', // plain text input
                label: 'Search Item',
                description: __('Search and filter items below')
            },
            {
                fieldname: 'items_html',
                fieldtype: 'HTML'
            }
        ],
        primary_action_label: 'Get Items',
        primary_action() {
            const selected_rows = Object.keys(selected_rows_map)
                .map(name => child_table.find(r => r.name === name))
                .filter(Boolean);
    
            if (!selected_rows.length) {
                frappe.msgprint(__('Please select at least one item.'));
                return;
            }
    
            frm.clear_table('work_progress_detail');
            selected_rows.forEach((row, i) => {
                const new_row = frm.add_child('work_progress_detail');
                Object.keys(row).forEach(key => {
                    if (!['name','owner','creation','modified','modified_by','docstatus','parent','parentfield','parenttype','idx'].includes(key)) {
                        new_row[key] = row[key];
                    }
                });
                new_row.idx = i + 1; // reset serial number
            });    
            frm.refresh_field('work_progress_detail');
            d.hide();
        }
    });

    // render the table
    function render_table(filtered_rows) {
        const table_html = `
            <div style="border: 1px solid var(--muted-foreground); border-radius:6px; padding:8px;">
                <table class="table table-bordered" style="width:100%; border-collapse:collapse;">
                    <thead>
                        <tr style="background: transparent;">
                            <th style="width: 36px; text-align:center;"><input type="checkbox" id="dialog-select-all"></th>
                            <th style="width:220px;">Item</th>
                            <th style="width:300px;">Description</th>
                            <th style="width:80px; text-align:right;">Qty</th>
                            <th style="width:120px; text-align:right;">Rate</th>
                        </tr>
                    </thead>
                </table>
                <div id="dialog-table-body" style="max-height:360px; overflow:auto; margin-top:6px;">
                    <table class="table table-bordered" style="width:100%; border-collapse:collapse;">
                        <tbody>
                            ${filtered_rows.map(row => `
                                <tr data-name="${row.name}">
                                    <td style="width:36px; text-align:center;">
                                        <input type="checkbox" class="row-checkbox" ${selected_rows_map[row.name] ? 'checked' : ''}>
                                    </td>
                                    <td style="width:220px; padding:8px;">${frappe.utils.escape_html(row.item || '')}</td>
                                    <td style="width:300px; padding:8px;">${frappe.utils.escape_html(row.description || row.item_name || '')}</td>
                                    <td style="width:80px; text-align:right; padding:8px;">${row.total_quantities_implemented || 0}</td>
                                    <td style="width:120px; text-align:right; padding:8px;">${row.rate || 0}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    
        const $html = d.fields_dict.items_html.$wrapper;
        $html.empty().append(table_html);
    
        // ✅ Select-all logic
        $html.find('#dialog-select-all').on('change', function() {
            const checked = $(this).is(':checked');
            $html.find('.row-checkbox').prop('checked', checked);
            filtered_rows.forEach(r => {
                if (checked) selected_rows_map[r.name] = true;
                else delete selected_rows_map[r.name];
            });
        });
    
        // ✅ Row click toggling
        $html.find('tr[data-name]').on('click', function(e) {
            if ($(e.target).is('input')) return;
            const $cb = $(this).find('.row-checkbox');
            const checked = !$cb.prop('checked');
            $cb.prop('checked', checked);
            const rowname = $(this).data('name');
            if (checked) selected_rows_map[rowname] = true;
            else delete selected_rows_map[rowname];
        });
    
        // ✅ Direct checkbox clicks
        $html.find('.row-checkbox').on('change', function() {
            const rowname = $(this).closest('tr').data('name');
            if ($(this).is(':checked')) selected_rows_map[rowname] = true;
            else delete selected_rows_map[rowname];
        });
    }    

    // Initial render
    render_table(child_table);

    // Filter when user selects/inputs in search
    d.fields_dict.item_search.$input.on('input change', function() {
        const val = d.get_value('item_search') || '';
        const lower = val.toString().toLowerCase();

        const filtered = child_table.filter(r => {
            if (!val) return true;
            return (
                (r.item && r.item.toLowerCase().includes(lower)) ||
                (r.item_name && r.item_name.toLowerCase().includes(lower)) ||
                (r.description && r.description.toLowerCase().includes(lower))
            );
        });

        render_table(filtered);
    });

    d.show();
}
