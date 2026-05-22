import frappe

@frappe.whitelist()
def get_all_items(doctype, txt, searchfield, start, page_len, filters):
    return frappe.db.sql("""
        SELECT name, item_name, item_group
        FROM `tabItem`
        WHERE (name LIKE %(txt)s OR item_name LIKE %(txt)s)
        LIMIT %(page_len)s OFFSET %(start)s
    """, {
        "txt": f"%{txt}%",
        "start": start,
        "page_len": page_len
    })