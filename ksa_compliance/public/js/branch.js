frappe.ui.form.on("Branch", {
    setup: function (frm) {
        frm.set_df_property('custom_branch_ids', 'cannot_delete_rows', 1);
        frm.set_df_property('custom_branch_ids', 'cannot_add_rows', 1);
    },
    refresh: async function (frm) {
        add_other_ids_if_new(frm)
        await filter_company_address(frm)
    },
    custom_company: async function (frm) {
        await filter_company_address(frm)
    }
})

async function fetch_company_address(frm) {
    if (frm.doc.custom_company) {
        const res = await frappe.call({
            method:
                "ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings.fetch_company_addresses",
            args: {
                company_name: frm.doc.custom_company,
            }
        });
        return res.message
    }
    return [];
}

async function filter_company_address(frm) {
    const addresses = await fetch_company_address(frm)
    frm.set_query("custom_company_address", function () {
        return {
            filters: {
                name: ["in", addresses],
            },
        };
    });
}

function add_other_ids_if_new(frm) {
    if (frm.doc.custom_branch_ids.length === 0) {
        var seller_id_list = [
            {
                type_name: "Commercial Registration Number",
                type_code: "CRN",
            }
        ];
        frm.set_value("custom_branch_ids", seller_id_list);
    }
}