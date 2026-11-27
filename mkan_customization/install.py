"""Install-time setup. `bench install-app` does not run patches, so seed data goes here too."""
from mkan_customization.mkan_customization.doctype.supplier_scorecard_settings.defaults import seed_settings


def after_install():
	seed_settings()
