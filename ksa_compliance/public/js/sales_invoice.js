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
        await set_zatca_discount_reason(frm)
    },
})



async function set_zatca_discount_reason(frm) {
    const zatca_discount_reasons = await get_zatca_discount_reason_codes()
    frm.fields_dict.custom_zatca_discount_reason.set_data(zatca_discount_reasons)
}

async function set_zatca_integration_status(frm) {
    const res = await frappe.call({
        method: "ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields.get_zatca_integration_status",
        args: {
            invoice_id: frm.doc.name,
            doctype: frm.doc.doctype
        },
    });

    const status = res.integration_status;
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

async function get_zatca_discount_reason_codes() {
    const res = await frappe.call({
        method: "ksa_compliance.invoice.get_zatca_invoice_discount_reason_list"
    })
    return res.message
}