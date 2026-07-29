
import frappe

def debug():
    print("--- Checking Approver Role Assignment ---")
    approvers = frappe.get_all("Has Role", filters={"role": "Approver"}, pluck="parent")
    print(f"Users with 'Approver' role in Has Role table: {approvers}")

    print("\n--- Checking Role Allotment ---")
    role_allotment = frappe.get_doc("Role Allotment")
    
    owners = set()
    for row in role_allotment.role_owner_list:
        if row.role_owner:
            for owner in row.role_owner.split(","):
                owners.add(owner.strip())
    
    print(f"All owners found in Role Allotment: {owners}")

    # Manual intersection
    intersection = [o for o in owners if o in approvers]
    print(f"Owners that are also Approvers: {intersection}")



    print("\n--- Testing get_all_approvers ---")
    from mkan_customization.mkan_customization.doctype.user_role_request.user_role_request import get_all_approvers
    all_approvers = get_all_approvers()
    print(f"All Approvers: {all_approvers}")
    
    # Check if only approvers are returned
    frappe_approvers = frappe.get_all("Has Role", filters={"role": "Approver"}, pluck="parent")
    if set(all_approvers) == set(frappe_approvers):
        print("Success: get_all_approvers returns correct list.")
    else:
        print("Failure: List mismatch.")



import json
debug()
