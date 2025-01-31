
import frappe
from frappe import _
from frappe.utils import now

def before_validate(self, method):
	previous_state = frappe.db.get_value(self.doctype,self.name,"workflow_state")

	if previous_state != self.workflow_state:
		workflow_state(self)

def workflow_state(self):
	user_doc = frappe.get_doc("User", frappe.session.user)
	user_roles = [role.role for role in user_doc.roles]
	role = user_roles[0] if user_roles else "No Role"
	user_name = frappe.db.get_value("User",frappe.session.user,"full_name")
	for row in self.state_change:
		if row.workflow_state == self.workflow_state:
			self.state_change = []
			user_name = row.username
	self.append('state_change', {
		'username': user_name,
		'modification_time': now(),
		"workflow_state": self.workflow_state,
		"role":role
	})

def before_insert(self, method):
	self.workflow_changes = []
