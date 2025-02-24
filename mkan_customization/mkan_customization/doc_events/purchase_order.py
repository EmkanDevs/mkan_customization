import frappe

def after_insert(self, method):
    self.custom_bid_tabulation_check = 1
    self.db_set("custom_bid_tabulation_check", 1)