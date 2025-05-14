// Copyright (c) 2025, LavaLoon and contributors
// For license information, please see license.txt

frappe.ui.form.on("ZATCA Invoice Fix Rejection", {
	setup(frm) {
        frm.set_df_property('items', 'cannot_delete_rows', 1);
        frm.set_df_property('items', 'cannot_add_rows', 1);
	},
    async onload(frm) {
        await set_invoice_filters(frm)
        await set_amounts(frm)
    },
    async invoice_type(frm) {
        await set_invoice_filters(frm)
    },
    async invoice(frm) {
        await set_amounts(frm)
    }
});

async function set_amounts(frm) {
    if (!frm.doc.invoice) {
        return null
    }
    const invoice_amounts = await frappe.call({
            method: "ksa_compliance.ksa_compliance.doctype.zatca_invoice_fix_rejection.zatca_invoice_fix_rejection.fetch_invoice_amounts_details",
            args: {
                invoice_type: frm.doc.invoice_type,
                invoice: frm.doc.invoice
            }
        })
    frm.set_value("total_tax_amount", invoice_amounts.message.total_tax_amount)
    frm.set_value("total_amount_without_taxes_and_discount", invoice_amounts.message.total_amount_without_taxes_and_discount)
    frm.set_value("total_amount_without_taxes", invoice_amounts.message.total_amount_without_taxes)
    frm.set_value("total_amount_with_taxes_and_discount", invoice_amounts.message.total_amount_with_taxes_and_discount)
    frm.set_value("total_discount_amount", invoice_amounts.message.total_discount_amount)

    let items = []
    for (let it of invoice_amounts.message.items) {
        items.push(
            {
                "item": it.item_code,
                "qty": it.qty,
                "amount_without_taxes": it.amount_without_taxes,
                "tax_amount": it.tax_amount,
                "discount_amount": it.discount_amount,
            }
        )
    }
    frm.set_value("items", items)
}

async function set_invoice_filters(frm) {
    const res = await frappe.db.get_list("Sales Invoice Additional Fields", {
        fields: ['sales_invoice'],
        filters: {
            "integration_status": "Rejected",
            "invoice_doctype": frm.doc.invoice_type
        },
        pluck: "sales_invoice"
    })

    frm.set_query("invoice", () => {
        return {
            filters: {
                "name": ["in", res || []]
            }
        }
    })
}