frappe.ui.form.on("ZATCA Business Settings", {
    setup: function (frm) {
        frm.set_df_property('other_ids', 'cannot_delete_rows', 1);
        frm.set_df_property('other_ids', 'cannot_add_rows', 1);
    },
    refresh: async function (frm) {
        add_other_ids_if_new(frm);
        filter_company_address(frm);
        if (!frm.is_new() && frm.doc.status === "Active") {
            await add_revoke_button(frm)
        }
        if (!frm.is_new() && frm.doc.status === "Revoked") {
            add_create_business_settings_button(frm)
        }

        frm.add_custom_button(__("Submit Feedback"), () => {
            ksa_compliance.feedback_dialog.show_feedback_dialog(__("Submit Feedback"), frm.doc.company);
        });
    },
    company: function (frm) {
        filter_company_address(frm);
    },
    setup_zatca_cli: async function (frm) {
        let response = await frappe.call({
            method: "ksa_compliance.zatca_cli.setup",
            args: {
                override_cli_download_url: frm.doc.override_cli_download_url || '',
                override_jre_download_url: frm.doc.override_jre_download_url || '',
            },
        })
        if (response.message) {
            frm.set_value('zatca_cli_path', response.message.cli_path);
            frm.set_value('java_home', response.message.jre_path);
            frm.save();
        }
    },
    check_zatca_cli: function (frm) {
        frappe.call({
            freeze: true,
            freeze_message: __('Please wait...'),
            method: "ksa_compliance.zatca_cli.check_setup",
            args: {
                zatca_cli_path: frm.doc.zatca_cli_path || '',
                java_home: frm.doc.java_home || '',
            }
        })
    },
    block_invoice_on_invalid_xml: async function (frm) {
        if (frm.doc.block_invoice_on_invalid_xml) {
            try {
                let result = await frappe.call({
                    freeze: true,
                    freeze_message: __('Please wait. Checking ZATCA CLI version...'),
                    method: "ksa_compliance.zatca_cli.check_validation_details_support",
                    args: {
                        zatca_cli_path: frm.doc.zatca_cli_path || '',
                        java_home: frm.doc.java_home || '',
                    }
                });

                if (!result.message.is_supported) {
                    frappe.throw(result.message.error);
                }
            } catch (e) {
                frm.set_value('block_invoice_on_invalid_xml', 0);
                throw e;
            }
        }
    },
    create_csr: function (frm) {
        frappe.prompt(__('OTP'), async ({ value }) => {
            await frappe.call({
                freeze: true,
                freeze_message: __('Please wait...'),
                method: "ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings.onboard",
                args: {
                    business_settings_id: frm.doc.name,
                    otp: value
                },
            });
            frm.reload_doc();
        });
    },
    perform_compliance_checks: function (frm) {
        if (!frm.doc.compliance_request_id) {
            frappe.throw(__('Please Onboard first to generate a compliance request ID'))
            return;
        }


        let simplified = frm.doc.type_of_business_transactions === 'Let the system decide (both)' ||
            frm.doc.type_of_business_transactions === 'Simplified Tax Invoices';
        let standard = frm.doc.type_of_business_transactions === 'Let the system decide (both)' ||
            frm.doc.type_of_business_transactions === 'Standard Tax Invoices';
        let customer_fields = [];
        if (simplified)
            customer_fields.push({
                label: 'Simplified Tax Customer',
                fieldname: 'simplified_customer_id',
                fieldtype: 'Link',
                options: 'Customer',
                reqd: 1,
                get_query: function () {
                    return {
                        query: "ksa_compliance.compliance_checks.customer_query",
                        filters: { "standard": false },
                    }
                }
            });

        if (standard) {
            customer_fields.push({
                label: 'Standard Tax Customer',
                fieldname: 'standard_customer_id',
                fieldtype: 'Link',
                options: 'Customer',
                reqd: 1,
                get_query: function () {
                    return {
                        query: "ksa_compliance.compliance_checks.customer_query",
                        filters: { "standard": true },
                    }
                }
            });
        }

        let fields = customer_fields.concat([
            {
                label: 'Item',
                fieldname: 'item_id',
                fieldtype: 'Link',
                options: 'Item',
                reqd: 1,
            },
            {
                label: 'Tax Category',
                fieldname: 'tax_category_id',
                fieldtype: 'Link',
                options: 'Tax Category',
                reqd: 1,
            },
        ])

        frappe.prompt(fields, values => {
            frappe.call({
                freeze: true,
                freeze_message: 'Please wait...',
                method: "ksa_compliance.compliance_checks.perform_compliance_checks",
                args: {
                    business_settings_id: frm.doc.name,
                    simplified_customer_id: values.simplified_customer_id || '',
                    standard_customer_id: values.standard_customer_id || '',
                    item_id: values.item_id,
                    tax_category_id: values.tax_category_id,
                },
            });
        });
    },
    get_production_csid: function (frm) {
        if (!frm.doc.compliance_request_id) {
            frappe.throw(__('Please Onboard first to generate a compliance request ID'))
            return;
        }

        frappe.prompt(__('OTP'), async ({ value }) => {
            const result = await frappe.call({
                freeze: true,
                freeze_message: 'Please wait...',
                method: "ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings.get_production_csid",
                args: {
                    business_settings_id: frm.doc.name,
                    otp: value
                },
            });

            if (result.message) {
                ksa_compliance.feedback_dialog.show_feedback_dialog(__("KSA Compliance Feedback"), frm.doc.company, true);
            }
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
    if (frm.doc.other_ids.length === 0) {
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
                type_name: "Other ID",
                type_code: "OTH",
            }
        );
        frm.set_value("other_ids", seller_id_list);
    }
}

function add_revoke_button(frm) {
    frm.add_custom_button("Revoke", async () => {
        frappe.confirm(
            __("Are you sure you want to revoke this Business Settings and CSID? This cannot be undone."),
            () => {
                frappe.call({
                    method: "ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings.revoke_business_settings",
                    args: {
                        settings_id: frm.doc.name,
                        company: frm.doc.company
                    },
                    callback(r){
                        frm.refresh()
                    }
                })
            }
        )
    }).addClass("btn-danger")
}

function add_create_business_settings_button(frm) {
    frm.add_custom_button("Create New Business Settings", () => {
            frappe.model.open_mapped_doc({
            method: "ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings.create_business_settings",
            frm: cur_frm,
        });
    });
}
