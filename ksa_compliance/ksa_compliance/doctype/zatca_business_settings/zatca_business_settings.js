frappe.ui.form.on("ZATCA Business Settings", {
    setup: function(frm){
        frm.set_df_property('other_ids', 'cannot_delete_rows', 1);
        frm.set_df_property('other_ids', 'cannot_add_rows', 1);
    },
    refresh: function (frm) {
        add_other_ids_if_new(frm);
        filter_company_address(frm);
    },
    company: function (frm) {
        filter_company_address(frm);
    },
    check_lava_zatca: function (frm) {
        frappe.call({
            freeze: true,
            freeze_message: __('Please wait...'),
            method: "ksa_compliance.zatca_cli.version",
            args: {
                zatca_path: frm.doc.lava_zatca_path,
            }
        })
    },
    create_csr: function (frm) {
        frappe.prompt(__('OTP'), ({value}) => {
            frappe.call({
                freeze: true,
                freeze_message: __('Please wait...'),
                method: "ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings.onboard",
                args: {
                    business_settings_id: frm.doc.name,
                    otp: value
                },
            });
        });
    },
    perform_compliance_checks: function (frm) {
        if (!frm.doc.compliance_request_id) {
            frappe.throw(__('Please Onboard first to generate a compliance request ID'))
            return;
        }

        frappe.prompt([
            {
                label: 'Customer',
                fieldname: 'customer_id',
                fieldtype: 'Link',
                options: 'Customer'
            },
            {
                label: 'Item',
                fieldname: 'item_id',
                fieldtype: 'Link',
                options: 'Item'
            }
        ], values => {
            frappe.call({
                freeze: true,
                freeze_message: 'Please wait...',
                method: "ksa_compliance.compliance_checks.perform_compliance_checks",
                args: {
                    business_settings_id: frm.doc.name,
                    customer_id: values.customer_id,
                    item_id: values.item_id,
                },
            });
        });
    },
    get_production_csid: function (frm) {
        if (!frm.doc.compliance_request_id) {
            frappe.throw(__('Please Onboard first to generate a compliance request ID'))
            return;
        }

        frappe.prompt(__('OTP'), ({value}) => {
            frappe.call({
                freeze: true,
                freeze_message: 'Please wait...',
                method: "ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings.get_production_csid",
                args: {
                    business_settings_id: frm.doc.name,
                    otp: value
                },
            });
        });
    },
});

function filter_company_address(frm) {
    frappe.call({
        method:
            "ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings.fetch_company_addresses",
        args: {
            company_name: frm.doc.company,
        },
        callback: function (r) {
            if (r.message) {
                frm.set_query("company_address", function () {
                    return {
                        filters: {
                            name: ["in", r.message],
                        },
                    };
                });
            }
        },
    });
}

function add_other_ids_if_new(frm) {
    // TODO: update permissions for child doctype
    if (frm.is_new()) {
        var seller_id_list = [];
        seller_id_list.push(
            {
                type_name: "Commercial Registration Number",
                type_code: "CRN",
            },
            {
                type_name: "MOMRAH License",
                type_code: "MOM",
            },
            {
                type_name: "MHRSD License",
                type_code: "MLS",
            },
            {
                type_name: "700 Number",
                type_code: "700",
            },
            {
                type_name: "MISA License",
                type_code: "SAG",
            },
            {
                type_name: "Other OD",
                type_code: "OTH",
            }
        );
        frm.set_value("other_ids", seller_id_list);
    }
}
