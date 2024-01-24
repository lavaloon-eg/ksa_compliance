frappe.pages['e-invoicing-sync'].on_page_load = function(wrapper) {
	var me = frappe.ui.make_app_page({
		parent: wrapper,
		single_column: true
	});
	me.page = wrapper.page;
	me.page.set_title(__("Sync Invoices"));

	// Calling Initialization method
	let batch_date;
	initialize(me, batch_date);
}

function initialize(page, batch_date) {
    // Initialization implementation
    let field = page.add_field({
        label : "Batch Date",
        fieldtype: "Date",
        fieldname: "batch_date",
        change() {
            batch_date = field.get_value();
        }
    });
    let $btn = page.set_primary_action("submit", () => sync_invoices(batch_date));
}

function sync_invoices(batch_date) {
    // calling server side method to sync the invoices.
    if (!batch_date)
        frappe.throw(__("Select a date first."))
    console.log(batch_date);
}