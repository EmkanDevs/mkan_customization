# Copyright (c) 2025, Finbyz and contributors
# For license information, please see license.txt

import frappe


def execute(filters=None):
    # Define the columns for the report
    columns = [
        {"label": "User", "fieldname": "user", "fieldtype": "Data", "width": 200},
        {"label": "Full Name", "fieldname": "full_name", "fieldtype": "Data", "width": 200},
        {"label": "Role", "fieldname": "role", "fieldtype": "Data", "width": 200}
    ]
    # Build the base query to fetch user data
    query = """
        SELECT u.name as user, u.full_name, hr.role
        FROM `tabUser` u
        LEFT JOIN `tabHas Role` hr ON u.name = hr.parent
        WHERE u.enabled = 1
    """
    # Initialize an empty list for the query parameters
    params = []
    # Add filters to the query if any filters are provided
    if filters:
        # If the 'user' filter is provided, add it to the query and parameters
        if filters.get('user'):
            query += " AND u.name = %s"
            params.append(filters['user'])
        # If the 'role' filter is provided, add it to the query and parameters
        if filters.get('role'):
            query += " AND hr.role = %s"
            params.append(filters['role'])
 
    # Order the results by user name
    query += " ORDER BY u.name"
    # Execute the query with the parameters and fetch the data as dictionaries
    data = frappe.db.sql(query, params, as_dict=True)
    # Return the columns and data as the result of the report
    return columns, data
