
import frappe

def debug():
    print("--- Roles ---")
    roles = frappe.get_all("Role", filters={"name": ["like", "%Approver%"]}, pluck="name")
    print(roles)

    print("\n--- Role Allotment ---")
    ra = frappe.get_doc("Role Allotment")
    for row in ra.role_owner_list:
        print(f"Role: {row.role}, Owners: {row.role_owner}")

    print("\n--- Testing get_role_owners ---")
    # Simulate the function logic
    owners = set()
    for row in ra.role_owner_list:
        if row.role_owner:
             for owner in row.role_owner.split(","):
                owners.add(owner.strip())
    
    print(f"All Owners found: {owners}")
    
    valid_owners = frappe.get_all(
        "Has Role",
        filters={
            "role": "Approver",
            "parent": ["in", list(owners)]
        },
        pluck="parent"
    )
    print(f"Valid Owners (Approvers): {valid_owners}")

    # Check roles for a sample owner if any
    if owners:
        sample = list(owners)[0]
        print(f"\n--- Roles for {sample} ---")
        user_roles = frappe.get_roles(sample)
        print(user_roles)

debug()
