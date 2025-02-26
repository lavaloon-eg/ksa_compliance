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
    }
})