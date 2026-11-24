import frappe
from frappe.utils import flt


def calculate_weighbridge_weights(doc, method=None):
	"""Auto-calculate Net Weight and Net Payable Weight on Purchase Receipt.

	Formula:
	    net_weight = max(0.0, flt(gross_weight) - flt(tare_weight))
	    deduction = net_weight * (flt(dirt_moisture_deduction_pct) / 100.0)
	    net_payable_weight = max(0.0, net_weight - deduction)
	"""
	gross = flt(doc.get("gross_weight"))
	tare = flt(doc.get("tare_weight"))

	if gross or tare:
		doc.net_weight = max(0.0, flt(gross - tare, 2))
	elif not doc.get("net_weight"):
		doc.net_weight = 0.0

	deduction_pct = flt(doc.get("dirt_moisture_deduction_pct"))
	if doc.net_weight and deduction_pct:
		deduction_qty = flt(doc.net_weight * deduction_pct / 100.0, 2)
		doc.net_payable_weight = max(0.0, flt(doc.net_weight - deduction_qty, 2))
	else:
		doc.net_payable_weight = flt(doc.net_weight, 2)
