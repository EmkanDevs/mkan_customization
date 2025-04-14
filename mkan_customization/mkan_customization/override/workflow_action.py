import frappe
from frappe.utils.user import get_users_with_role
from frappe.model.workflow import has_approval_access
from frappe.workflow.doctype.workflow_action.workflow_action import get_workflow_action_url

def get_users_next_action_data_for_workflow(transitions, doc):
	user_data_map = {}

	@frappe.request_cache
	def user_has_permission(user: str) -> bool:
		from frappe.permissions import has_permission

		return has_permission(doctype=doc, user=user)

	for transition in transitions:
		users = get_users_with_role(transition.allowed)
		filtered_users = [
			user for user in users if has_approval_access(user, doc, transition) and user_has_permission(user) and check_project_permissions(user, doc)
		]
		if doc.get("owner") in filtered_users and not transition.get("send_email_to_creator"):
			filtered_users.remove(doc.get("owner"))
		for user in filtered_users:
			if not user_data_map.get(user):
				user_data_map[user] = frappe._dict(
					{
						"possible_actions": [],
						"email": frappe.db.get_value("User", user, "email"),
					}
				)

			user_data_map[user].get("possible_actions").append(
				frappe._dict(
					{
						"action_name": transition.action,
						"action_link": get_workflow_action_url(transition.action, doc, user),
					}
				)
			)
	return user_data_map

def check_project_permissions(user, doc):
	all_documents = [doc] + doc.get_all_children()
	
	for d in all_documents:
		meta = frappe.get_meta(d.doctype)
		for row in meta.get_link_fields():
			if row.options == "Project" and ((d.get(row.fieldname) and not frappe.db.exists("User Permission", {"user": user, "allow": "Project","for_value": d.get(row.fieldname)})) or not d.get(row.fieldname)):
				return False

	return True