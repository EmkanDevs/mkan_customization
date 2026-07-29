frappe.pages['po---material-master'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'PO - Material Master List (Cost Control)',
        single_column: true
    });

    page.add_inner_button(__('Print Table'), function() {
        let table = document.querySelector('.po---material-master table');
        if (!table) {
            frappe.msgprint("No data to print");
            return;
        }
        let clone = table.cloneNode(true);

        let print_window = window.open('', '', 'height=700,width=900');

        print_window.document.write(`
            <html>
            <head>
                <title>PO - Material Master List</title>
                <style>
                    table {
                        width: 100%;
                        border-collapse: collapse;
                        font-size: 12px;
                    }
                    table, th, td {
                        border: 1px solid #000;
                    }
                    th, td {
                        padding: 6px;
                        text-align: left;
                    }
                    th {
                        background: #f2f2f2;
                    }
                </style>
            </head>
            <body>
                ${clone.outerHTML}
            </body>
            </html>
        `);

        print_window.document.close();
        print_window.focus();
        print_window.print();
    });

    // Add Export to Excel Button
    page.add_inner_button(__('Export to Excel'), function() {
        let table = document.querySelector('.po---material-master table');
        if (!table) {
            frappe.msgprint("No data to export");
            return;
        }
    
        let cloned = table.cloneNode(true);
        let csv = [];
        let rows = cloned.querySelectorAll("tr");
    
        rows.forEach(tr => {
            let row = [];
            let cols = tr.querySelectorAll("th, td");
            cols.forEach(td => {
                let htmlContent = td.innerHTML.replace(/<br\s*\/?>/gi, "\n");
                let text = (new DOMParser().parseFromString(htmlContent, "text/html")).body.textContent;
                text = text
                    .split("\n")
                    .map(line => line.trim()) 
                    .filter(line => line.length > 0)
                    .join("\n");
    
                row.push('"' + text.replace(/"/g, '""') + '"');
            });
            csv.push(row.join(","));
        });
    
        let blob = new Blob(["\ufeff" + csv.join("\n")], { type: "text/csv;charset=utf-8;" });
        let link = document.createElement("a");
        link.href = URL.createObjectURL(blob);
        link.download = "PO_Material_Master.csv";
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    });

    // Add container for filters + table
    $(frappe.render_template(`<div class="po---material-master">
        <div class="data-area mt-4">
            <table class="table table-bordered table-striped">
                <thead>
                    <tr>
                        <th>PO No.</th>
                        <th>Project Code</th>
                        <th>Project Name</th>
                        <th>PO Date</th>
                        <th>Supplier Code</th>
                        <th>Supplier Name</th>
                        <th>Item Code</th>
                        <th>Item Name</th>
                        <th>UOM</th>
                        <th>Rate</th>
                    </tr>
                </thead>
                <tbody class="data-body"></tbody>
            </table>
        </div>
    </div>`)).appendTo(page.body);

    // Filters
    let filters = {
        project: page.add_field({
            label: 'Project',
            fieldtype: 'Link',
            fieldname: 'project',
            options: 'Project',
            change: () => load_data()
        }),
        supplier: page.add_field({
            label: 'Supplier',
            fieldtype: 'Link',
            fieldname: 'supplier',
            options: 'Supplier',
            change: () => load_data()
        }),
        item: page.add_field({
            label: 'Item',
            fieldtype: 'Link',
            fieldname: 'item',
            options: 'Item',
            change: () => load_data()
        }),
        from_date: page.add_field({
            label: 'From Date',
            fieldtype: 'Date',
            fieldname: 'from_date',
            change: () => load_data()
        }),
        to_date: page.add_field({
            label: 'To Date',
            fieldtype: 'Date',
            fieldname: 'to_date',
            change: () => load_data()
        })
    };

    function load_data() {
        let filter_values = {};
        Object.keys(filters).forEach(f => {
            filter_values[f] = filters[f].get_value();
        });

        frappe.call({
            method: "mkan_customization.mkan_customization.page.po___material_master.po___material_master.get_data",
            args: { filters: filter_values },
            callback: function(r) {
                let data = r.message || [];
                let tbody = $(wrapper).find(".data-body");
                tbody.empty();

                if (data.length === 0) {
                    tbody.append(`<tr><td colspan="10" class="text-center text-muted">No records found</td></tr>`);
                }

                data.forEach(row => {
                    tbody.append(`
                        <tr>
                            <td>${row.po_no}</td>
                            <td>${row.project_code || ""}</td>
                            <td>${row.project_name || ""}</td>
                            <td>${row.po_date || ""}</td>
                            <td>${row.supplier_code || ""}</td>
                            <td>${row.supplier_name || ""}</td>
                            <td>${row.item_code || ""}</td>
                            <td>${row.item_name || ""}</td>
                            <td>${row.uom || ""}</td>
                            <td>${row.rate || 0}</td>
                        </tr>
                    `);
                });
            }
        });
    }

    // Initial load
    load_data();
};
