frappe.ui.form.on('Sales Invoice', {
    setup: function (frm) {
        frm.set_query('custom_return_against_additional_references', function (doc) {
            // Similar to logic in erpnext/public/js/controllers/transaction.js for return_against
            let filters = {
                'docstatus': 1,
                'is_return': 0,
                'company': doc.company
            };
            if (frm.fields_dict['customer'] && doc.customer) filters['customer'] = doc.customer;
            if (frm.fields_dict['supplier'] && doc.supplier) filters['supplier'] = doc.supplier;

            return {
                filters: filters
            };
        });
    },
    async refresh(frm) {
        await set_zatca_integration_status(frm)
    }
})

async function set_zatca_integration_status(frm) {
    const res = await frappe.db.get_value("Sales Invoice Additional Fields", {
            "sales_invoice": frm.doc.name,
            "is_latest": 1
    }, "integration_status");
    const status = res.message.integration_status
    if (status) {
        let color = "blue"
        if (status === 'Accepted') {
            color = "green"
        } else if (["Rejected", "Resend"].includes(status)) {
            color = "red"
        }
        frm.set_intro(`<b>Zatca Status: ${status}</b>`, color)
    }
}
