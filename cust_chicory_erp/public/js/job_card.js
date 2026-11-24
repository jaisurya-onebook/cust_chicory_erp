frappe.ui.form.on("Job Card", {
	stage_input_qty: function (frm) {
		calculate_job_card_loss(frm);
	},
	stage_output_qty: function (frm) {
		calculate_job_card_loss(frm);
	},
});

function calculate_job_card_loss(frm) {
	const input_qty = flt(frm.doc.stage_input_qty);
	const output_qty = flt(frm.doc.stage_output_qty);
	const loss = Math.max(0.0, flt(input_qty - output_qty, precision("stage_process_loss_qty", frm.doc)));
	frm.set_value("stage_process_loss_qty", loss);
}
