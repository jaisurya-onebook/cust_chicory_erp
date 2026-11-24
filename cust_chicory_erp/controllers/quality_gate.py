import frappe
from frappe import _


def validate_batch_quality(doc, method=None):
	"""Validate that items in Stock Entry or Delivery Note do not use batches
	with quality_status in ('On Hold', 'Rejected').
	Raises frappe.ValidationError preventing consumption or dispatch.
	"""
	batches_to_check = set()
	bundles = []

	for item in doc.get("items", []):
		if item.get("batch_no"):
			batches_to_check.add(item.batch_no)
		if item.get("serial_and_batch_bundle"):
			bundles.append(item.serial_and_batch_bundle)

	if bundles:
		bundle_batches = frappe.get_all(
			"Serial and Batch Entry",
			filters={"parent": ["in", bundles]},
			pluck="batch_no",
		)
		for b in bundle_batches:
			if b:
				batches_to_check.add(b)

	if not batches_to_check:
		return

	blocked_batches = frappe.get_all(
		"Batch",
		filters={
			"name": ["in", list(batches_to_check)],
			"quality_status": ["in", ["On Hold", "Rejected"]],
		},
		fields=["name", "quality_status"],
	)

	if blocked_batches:
		first_blocked = blocked_batches[0]
		frappe.throw(
			_("Batch {0} is currently {1} and cannot be consumed or dispatched.").format(
				first_blocked.name, first_blocked.quality_status
			),
			frappe.ValidationError,
		)
