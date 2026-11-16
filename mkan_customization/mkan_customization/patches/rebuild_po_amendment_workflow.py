from mkan_customization.setup_po_amendment import create_roles, create_workflow


def execute():
	"""Replace the first-version workflow (no Cancelled state, self-approval allowed) with the spec version."""
	create_roles()
	create_workflow(force=True)