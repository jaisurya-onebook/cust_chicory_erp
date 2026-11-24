import frappe
from frappe import _
from frappe.query_builder import DocType
from frappe.utils import flt


def execute(filters=None):
	filters = filters or {}
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	report_summary = get_report_summary(data)
	return columns, data, None, chart, report_summary


def get_columns():
	return [
		{
			"label": _("Work Order"),
			"fieldname": "work_order",
			"fieldtype": "Link",
			"options": "Work Order",
			"width": 180,
		},
		{
			"label": _("Operation"),
			"fieldname": "operation",
			"fieldtype": "Link",
			"options": "Operation",
			"width": 160,
		},
		{
			"label": _("Workstation"),
			"fieldname": "workstation",
			"fieldtype": "Link",
			"options": "Workstation",
			"width": 160,
		},
		{
			"label": _("Input Qty (Kg)"),
			"fieldname": "input_qty",
			"fieldtype": "Float",
			"width": 130,
		},
		{
			"label": _("Output Qty (Kg)"),
			"fieldname": "output_qty",
			"fieldtype": "Float",
			"width": 130,
		},
		{
			"label": _("Measured Loss (Kg)"),
			"fieldname": "measured_loss",
			"fieldtype": "Float",
			"width": 140,
		},
		{
			"label": _("Loss %"),
			"fieldname": "loss_pct",
			"fieldtype": "Percent",
			"width": 100,
		},
		{
			"label": _("Loss Reason"),
			"fieldname": "loss_reason",
			"fieldtype": "Data",
			"width": 180,
		},
		{
			"label": _("Operator Notes"),
			"fieldname": "operator_notes",
			"fieldtype": "Small Text",
			"width": 220,
		},
	]


def get_data(filters):
	jc = DocType("Job Card")

	query = (
		frappe.qb.from_(jc)
		.select(
			jc.name,
			jc.work_order,
			jc.operation,
			jc.workstation,
			jc.posting_date,
			jc.for_quantity,
			jc.total_completed_qty,
			jc.process_loss_qty,
			jc.remarks,
			jc.docstatus,
		)
		.where(jc.docstatus < 2)
	)

	# Check if custom fields exist in Job Card schema
	jc_meta = frappe.get_meta("Job Card")
	has_custom_stage_fields = jc_meta.has_field("stage_input_qty")

	if has_custom_stage_fields:
		query = query.select(
			jc.stage_input_qty,
			jc.stage_output_qty,
			jc.stage_process_loss_qty,
			jc.process_loss_reason,
		)

	if filters.get("work_order"):
		query = query.where(jc.work_order == filters.get("work_order"))

	if filters.get("from_date"):
		query = query.where(jc.posting_date >= filters.get("from_date"))

	if filters.get("to_date"):
		query = query.where(jc.posting_date <= filters.get("to_date"))

	query = query.orderby(jc.work_order).orderby(jc.creation)
	raw_records = query.run(as_dict=True)

	data = []
	for row in raw_records:
		input_qty = flt(row.get("stage_input_qty")) or flt(row.get("for_quantity")) or 0.0
		output_qty = flt(row.get("stage_output_qty")) or flt(row.get("total_completed_qty")) or 0.0

		measured_loss = flt(row.get("stage_process_loss_qty")) or flt(row.get("process_loss_qty"))
		if not measured_loss and input_qty > output_qty:
			measured_loss = max(0.0, input_qty - output_qty)

		loss_pct = round((measured_loss / input_qty) * 100.0, 2) if input_qty > 0 else 0.0

		loss_reason = row.get("process_loss_reason") or ""
		operator_notes = row.get("remarks") or ""

		data.append({
			"work_order": row.get("work_order"),
			"operation": row.get("operation"),
			"workstation": row.get("workstation"),
			"input_qty": input_qty,
			"output_qty": output_qty,
			"measured_loss": measured_loss,
			"loss_pct": loss_pct,
			"loss_reason": loss_reason,
			"operator_notes": operator_notes,
		})

	return data


def get_chart(data):
	if not data:
		return None

	operations = []
	loss_values = []
	for d in data:
		label = f"{d.get('operation')} ({d.get('work_order', '')})"
		operations.append(label)
		loss_values.append(d.get("measured_loss", 0.0))

	return {
		"data": {
			"labels": operations[:12],
			"datasets": [{"name": _("Measured Loss (Kg)"), "values": loss_values[:12]}],
		},
		"type": "bar",
	}


def get_report_summary(data):
	if not data:
		return []

	total_input = sum(flt(d.get("input_qty")) for d in data)
	total_output = sum(flt(d.get("output_qty")) for d in data)
	total_loss = sum(flt(d.get("measured_loss")) for d in data)
	overall_yield = round((total_output / total_input) * 100.0, 2) if total_input > 0 else 0.0

	return [
		{
			"value": total_input,
			"indicator": "Blue",
			"label": _("Total Stage Input (Kg)"),
			"datatype": "Float",
		},
		{
			"value": total_output,
			"indicator": "Green",
			"label": _("Total Stage Output (Kg)"),
			"datatype": "Float",
		},
		{
			"value": total_loss,
			"indicator": "Orange" if total_loss > 0 else "Grey",
			"label": _("Total Process Loss (Kg)"),
			"datatype": "Float",
		},
		{
			"value": overall_yield,
			"indicator": "Green" if overall_yield >= 70 else "Red",
			"label": _("Stage Yield %"),
			"datatype": "Percent",
		},
	]
