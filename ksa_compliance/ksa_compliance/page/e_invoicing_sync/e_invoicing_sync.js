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
    let submitBtn = document.getElementsByClassName("btn-sm")[0];
    submitBtn.disabled = true;
    if (!batch_date) {
        submitBtn.disabled = false;
        frappe.throw(__("Select a date first."));
    }
    //show_alert with indicator
    frappe.show_alert({
        message:__("Start Invoices Syncing...."),
        indicator:'green'
    }, 3);
    frappe.call({
        method: "ksa_compliance.background_jobs.add_batch_to_background_queue",
        args: {
            "check_date": batch_date
        },
        callback: function(r) {
            if (!r.exc) {
                frappe.msgprint("Syncing End.....");
            }
        }
    });
    submitBtn.disabled = true;
    console.log(batch_date);
}