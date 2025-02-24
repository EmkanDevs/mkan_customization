import frappe

def validate(self,method):
    self.custom_created_by_user = self.owner