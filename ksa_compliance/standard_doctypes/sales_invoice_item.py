import frappe
import json


def calculate_tax_amount(self, method):
    if self.items:
        for item in self.items:
            item_tax_rate = json.loads(item.item_tax_rate)["Expenses Included In Valuation - KD"]
            item.custom_tax_total = (item.amount * item_tax_rate) / 100
            item.custom_total_after_tax = item.amount + item.custom_tax_total
            item.save()
