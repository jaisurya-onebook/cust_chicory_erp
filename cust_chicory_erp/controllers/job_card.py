import frappe
from frappe.utils import flt


def calculate_job_card_loss(doc, method=None):
	"""Auto-calculate Measured Process Loss (Kg) on Job Card.

	Formula:
	    stage_process_loss_qty = max(0.0, flt(stage_input_qty) - flt(stage_output_qty))
	"""
	input_qty = flt(doc.get("stage_input_qty"))
	output_qty = flt(doc.get("stage_output_qty"))

	if input_qty or output_qty:
		doc.stage_process_loss_qty = max(0.0, flt(input_qty - output_qty, 2))
	else:
		doc.stage_process_loss_qty = 0.0
