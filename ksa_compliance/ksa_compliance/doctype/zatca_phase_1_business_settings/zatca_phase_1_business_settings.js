// Copyright (c) 2024, LavaLoon and contributors
// For license information, please see license.txt

frappe.ui.form.on("ZATCA Phase 1 Business Settings", {
    company(frm) {
        fetch_company_primary_address(frm)
        filter_address_by_company(frm)
    },
});


function fetch_company_primary_address(frm) {
    frappe.call({
        method: "ksa_compliance.ksa_compliance.doctype.zatca_phase_1_business_settings.zatca_phase_1_business_settings.get_company_primary_address",
        args: {
            company: frm.doc.company,
        },
        callback: function (r) {
            if (r.message.length === 0) {
                frm.set_value("address", "")
            } else {
                frm.set_value("address", r.message[0].name)
            }
        }
    });
}

function filter_address_by_company(frm) {
    frappe.call({
        method: "ksa_compliance.ksa_compliance.doctype.zatca_phase_1_business_settings.zatca_phase_1_business_settings.get_all_company_addresses",
        args: {
            company: frm.doc.company
        },
        callback: function (r) {
            if (r.message) {
                frm.set_query("address", function () {
                    return {
                        filters: {
                            name: ["in", r.message]
                        }
                    }
                })
            }
        }
    });
}
