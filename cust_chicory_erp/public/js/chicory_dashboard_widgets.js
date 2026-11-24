frappe.provide("cust_chicory_erp.dashboard");

cust_chicory_erp.dashboard.is_on_chicory_dashboard = function () {
	const route = frappe.get_route();
	if (!route || !route.length) return false;
	const route_str = route.join("/");
	return (
		route_str.includes("Chicory Manufacturing") ||
		route_str.includes("dashboard-view/Chicory%20Manufacturing") ||
		route_str.includes("cust-chicory-erp") ||
		(frappe.dashboard && frappe.dashboard.dashboard_name === "Chicory Manufacturing")
	);
};

cust_chicory_erp.dashboard.render_widget_rows = function ($widget, rows) {
	const escape = frappe.utils.escape_html;
	const $body = $widget.find(".chicory-process-widget-body");
	$body.empty();
	rows = (rows || []).slice(0, 5);
	if (!rows.length) {
		$body.append(`<div class="text-muted p-2 text-center">${__("All stock levels normal.")}</div>`);
		return;
	}
	rows.forEach((row) => {
		const $item = $(`
			<div class="chicory-process-list-item">
				<div class="chicory-process-item-main">
					<div class="chicory-process-item-title" title="${escape(row.title || "")}">
						${escape(row.title || "")}
					</div>
					<div class="chicory-process-item-subtitle" title="${escape(row.subtitle || "")}">
						${escape(row.subtitle || "")}
					</div>
				</div>
				<div class="chicory-process-metric-primary">${escape(row.metric_primary || "")}</div>
				<span class="chicory-badge ${escape(row.badge_color || "blue")}">${escape(row.badge_label || "")}</span>
				<div class="text-muted ml-1" style="font-size: 10px;">${frappe.utils.icon("chevron-right", "xs")}</div>
			</div>
		`);

		if (row.doctype && row.docname) {
			$item.on("click", (e) => {
				if (e.ctrlKey || e.metaKey) {
					frappe.open_in_new_tab = true;
				}
				frappe.set_route("Form", row.doctype, row.docname);
			});
		}
		$body.append($item);
	});
};

cust_chicory_erp.dashboard.build_widget_card = function (widget_data) {
	const escape = frappe.utils.escape_html;
	const $widget = $(`
		<div class="chicory-process-widget-box">
			<div class="widget-head">
				<div class="widget-title">
					<span title="${escape(widget_data.title || "")}">
						${escape(widget_data.title || "")}
					</span>
				</div>
				<div class="widget-control"></div>
			</div>
			<div class="chicory-process-widget-body"></div>
			<div class="chicory-process-widget-footer"></div>
		</div>
	`);

	const $control = $widget.find(".widget-control");

	if (widget_data.categories && widget_data.categories.length) {
		const category_method = widget_data.category_method;
		const activeCat = widget_data.active_category || "All";
		const optionsHtml = widget_data.categories
			.map(
				(cat) =>
					`<option value="${escape(cat)}" ${cat === activeCat ? "selected" : ""}>${escape(cat)}</option>`
			)
			.join("");

		const $select = $(`
			<select class="chicory-category-filter-select" title="${__("Filter by Category")}">
				${optionsHtml}
			</select>
		`);

		$select.on("change", function (e) {
			e.stopPropagation();
			const selectedCat = $(this).val();
			frappe
				.xcall(category_method, { category: selectedCat })
				.then((rows) => {
					cust_chicory_erp.dashboard.render_widget_rows($widget, rows || []);
				});
		});

		$control.append($select);
	}

	if (widget_data.primary_action?.doctype) {
		const $addBtn = $(`
			<button class="btn btn-xs btn-default ml-1" title="${escape(widget_data.primary_action.label || __("Create New"))}">
				${frappe.utils.icon("plus", "xs")}
			</button>
		`);
		$addBtn.on("click", (e) => {
			e.stopPropagation();
			frappe.new_doc(widget_data.primary_action.doctype);
		});
		$control.append($addBtn);
	}

	cust_chicory_erp.dashboard.render_widget_rows($widget, widget_data.rows);

	const $footer = $widget.find(".chicory-process-widget-footer");
	if (widget_data.footer_action?.route) {
		const $seeAll = $(`
			<button class="chicory-see-all-btn">${escape(widget_data.footer_action.label || __("View List"))} &rarr;</button>
		`);
		$seeAll.on("click", () => {
			frappe.set_route(...widget_data.footer_action.route);
		});
		$footer.append($seeAll);
	}

	return $widget;
};

cust_chicory_erp.dashboard.render_top_widgets = function (dashboard_instance) {
	const db = dashboard_instance || frappe.dashboard;
	if (!db || !db.container || !cust_chicory_erp.dashboard.is_on_chicory_dashboard()) {
		$(".chicory-dashboard-section").remove();
		return Promise.resolve();
	}

	return frappe
		.xcall("cust_chicory_erp.analysis.process_dashboard_widgets.get_process_dashboard_widgets", {
			dashboard_name: "Chicory Manufacturing",
		})
		.then((res) => {
			if (!cust_chicory_erp.dashboard.is_on_chicory_dashboard()) {
				$(".chicory-dashboard-section").remove();
				return;
			}
			const widgets = res?.widgets || [];
			const queue = res?.operations_queue || [];
			if (!widgets.length && !queue.length) return;

			let $section = db.container.find(".chicory-dashboard-section");
			if (!$section.length) {
				$section = $(`<div class="chicory-dashboard-section"></div>`);
				const $cardGroup = db.container.find(".number-widget-box").closest(".widget-group");
				if ($cardGroup.length) {
					$section.insertAfter($cardGroup.last());
				} else {
					$section.prependTo(db.container);
				}
			}

			$section.empty();

			// 1. Stock Alerts & Low Stock Action Priority
			if (widgets.length) {
				$section.append(`
					<div class="chicory-section-header">
						<span>${frappe.utils.icon("alert-triangle", "sm")}</span>
						<span>${__("Inventory Alerts & Low Stock Action Priority")}</span>
					</div>
				`);
				const $grid1 = $(`<div class="chicory-top-widgets-grid mb-4"></div>`).appendTo($section);
				widgets.forEach((w) => {
					$grid1.append(cust_chicory_erp.dashboard.build_widget_card(w));
				});
			}

			// 2. Live Operations & Manufacturing Pipeline
			if (queue.length) {
				$section.append(`
					<div class="chicory-section-header">
						<span>${frappe.utils.icon("activity", "sm")}</span>
						<span>${__("Live Operations Queue & Traceability Pipeline")}</span>
					</div>
				`);
				const $grid2 = $(`<div class="chicory-top-widgets-grid"></div>`).appendTo($section);
				queue.forEach((q) => {
					$grid2.append(cust_chicory_erp.dashboard.build_widget_card(q));
				});
			}

			// Ensure position after number cards
			const $cardGroup = db.container.find(".number-widget-box").closest(".widget-group");
			if ($cardGroup.length && $section.index() < $cardGroup.last().index()) {
				$section.insertAfter($cardGroup.last());
			}
		});
};

cust_chicory_erp.dashboard.patch_dashboard_view = function () {
	const db = frappe.dashboard;
	if (db && !db.__chicory_top_widgets_patched) {
		db.__chicory_top_widgets_patched = true;
		const orig_refresh = db.refresh?.bind(db);
		db.refresh = function () {
			if (orig_refresh) {
				return frappe.run_serially([
					() => orig_refresh(),
					() => cust_chicory_erp.dashboard.render_top_widgets(this),
				]);
			}
		};
	}

	if (cust_chicory_erp.dashboard.is_on_chicory_dashboard()) {
		setTimeout(() => cust_chicory_erp.dashboard.render_top_widgets(db), 100);
	} else {
		$(".chicory-dashboard-section").remove();
	}
};

$(document).on("page-change startup", () => {
	setTimeout(() => cust_chicory_erp.dashboard.patch_dashboard_view(), 100);
});

$(() => {
	if (frappe.router?.on) {
		frappe.router.on("change", () => {
			setTimeout(() => cust_chicory_erp.dashboard.patch_dashboard_view(), 100);
		});
	}
	setTimeout(() => cust_chicory_erp.dashboard.patch_dashboard_view(), 200);
});
