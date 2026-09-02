frappe.ui.form.on('Item', {
	refresh(frm) {
		frm.set_query('item_group', () => {
            return {
                filters: {
                    is_group: 0
                }
            }
        })
        		frm.set_query('custom_item_group_l1', () => {
            return {
                filters: {
                    parent_item_group: 'All Item Groups'
                }
            }
        })
        frm.set_query('custom_item_group_l2', () => {
            return {
                filters: {
                    parent_item_group: frm.doc.custom_item_group_l1
                }
            }
        })
        frm.set_query('custom_item_group_l3', () => {
            return {
                filters: {
                    parent_item_group: frm.doc.custom_item_group_l2
                }
            }
        })
        frm.set_query('item_group', () => {
            return {
                filters: {
                    parent_item_group: frm.doc.custom_item_group_l3
                }
            }
        })
        remove_duplicate_description(frm);
        
	},
	onload: function(frm) {
        remove_duplicate_description(frm);
    }
})

function remove_duplicate_description(frm) {
    // Check if description exists and matches item_name
    if (frm.doc.description && frm.doc.item_name && 
        frm.doc.description.trim() === frm.doc.item_name.trim()) {
        
        frm.doc.description = '';
        frm.refresh_field('description')
    }
}
