frappe.provide('ksa_compliance.feedback_dialog');

ksa_compliance.feedback_dialog = {
    show_feedback_dialog: async function (title, company=frappe.defaults.get_user_default("Company"), is_onboard_feedback = false) {
        const uploaded_files = [];
        const feedback_config = await this.get_feedback_configuration();

        const dialog = this.create_feedback_dialog(title, is_onboard_feedback, feedback_config, uploaded_files, company);
        dialog.show();
    },

    get_feedback_configuration: async function () {
        const response = await frappe.call({
            method: 'ksa_compliance.customer_feedback.get_feedback_settings',
            type: 'GET'
        });

        return response.message
    },

    create_feedback_dialog: function (title, is_onboard_feedback, config, uploaded_files, company) {
        const fields = [
            {
                label: __("Subject"),
                fieldname: "subject",
                fieldtype: "Select",
                reqd: 1,
                options: [
                    __("Bug Report"),
                    __("Feature Request"),
                    __("General Feedback"),
                    __("Compliance Issue"),
                    __("Other")
                ]
            },
            {
                label: __("Description"),
                fieldname: "description",
                fieldtype: "Text",
                reqd: 1,
                description: __("Maximum {0} characters", [config.MAX_DESCRIPTION_LENGTH])
            },
            {
                fieldtype: "HTML",
                fieldname: "company_info",
                options: `
                    <div style="margin-top: 10px; margin-bottom: 10px;">
                        <strong>${__("Company Information")}</strong><br>
                        ${__("Company Name")}: ${company}<br>
                    </div>
                `
            },
            {
                fieldtype: "HTML",
                fieldname: "external_link",
                options: `
                    <div style="margin-top: 10px; margin-bottom: 10px;">
                        ${__("Need help?")}
                        <a href="${config.LAVALOON_CONTACT_PAGE}" target="_blank" rel="noopener noreferrer">
                            ${__("Visit our Help Center")}
                        </a>.
                    </div>
                `
            },
            {
                fieldtype: "Button",
                fieldname: "upload_button",
                label: __("Upload Files"),
                click() {
                    ksa_compliance.feedback_dialog.create_file_uploader(config, uploaded_files);
                }
            },
            {
                fieldtype: "HTML",
                fieldname: "upload_warning",
                options: `<div class="alert alert-warning">
                    <strong>${__("Notes")}:</strong> ${__("Uploaded files will be publicly accessible and visible to us from your server. Please do not upload sensitive information.")}
                    <br>
                    ${__("We will use the company phone number and email to contact you regarding your feedback if they are provided.")}
                </div>`
            },
            {
                fieldtype: "HTML",
                fieldname: "file_preview",
                options: `
                    <div style="margin-top: 10px; margin-bottom: 10px;">
                        <strong>${__("Uploaded Files")}</strong><br>
                        <div id="file-preview-list">
                            ${uploaded_files.length ? uploaded_files.map(file => `
                                <div style="margin-top: 5px;">
                                    <a href="${file}" target="_blank">${file.split('/').pop()}</a>
                                </div>
                            `).join('') : __("No files uploaded yet.")}
                        </div>
                    </div>
                `
            }
        ];

        if (is_onboard_feedback) {
            fields.unshift({
                fieldtype: "HTML",
                fieldname: "onboard_feedback_message",
                options: `
                    <div style="margin-bottom: 10px; font-weight: 400;">
                        ${__("This feedback will be sent to the Application vendor.")}<br>
                        ${__("How was your experience configuring these settings?")}
                    </div>
                `
            });
        }

        const dialog = new frappe.ui.Dialog({
            title: title,
            fields: fields,
            size: 'large',
            primary_action_label: __('Submit'),
            async primary_action(values) {
                try {
                    if (!ksa_compliance.feedback_dialog.validate_feedback_submission(values, config)) {
                        return;
                    }

                    dialog.set_primary_action(__('Submitting...'), null);
                    await ksa_compliance.feedback_dialog.submit_feedback(values, uploaded_files, dialog, company);
                } catch (error) {
                    console.error('Error submitting feedback:', error);
                    frappe.show_alert({
                        message: __('Failed to submit feedback. Please try again.'),
                        indicator: 'red'
                    });
                    dialog.set_primary_action(__('Submit'), () => dialog.primary_action(values));
                }
            },
            secondary_action_label: __("Cancel"),
            secondary_action: () => {
                dialog.hide();
            }
        });

        return dialog;
    },    

    validate_feedback_submission: function (values, config) {
        if (values.description.length > config.MAX_DESCRIPTION_LENGTH) {
            frappe.msgprint(__("Description must be less than {0} characters", [config.MAX_DESCRIPTION_LENGTH]));
            return false;
        }

        return true;
    },

    create_file_uploader: function (config, uploaded_files) {
        new frappe.ui.FileUploader({
            allow_multiple: true,
            make_attachments_public: true,
            upload_notes: __("Upload up to {0} files (PDF, PNG, JPEG, DOCX), max {1}MB each",
                [config.MAX_NUMBER_OF_FILES, config.MAX_FILE_SIZE_MB]),
            restrictions: {
                allowed_file_types: config.ALLOWED_FILE_TYPES,
                max_file_size: config.MAX_FILE_SIZE_MB * 1024 * 1024,
                max_number_of_files: config.MAX_NUMBER_OF_FILES,
            },
            on_success(file) {
                uploaded_files.push(file.file_url);
                frappe.show_alert({
                    message: __("File uploaded: {0}", [file.file_name]),
                    indicator: 'green'
                });
                const file_preview = document.querySelector('#file-preview-list');
                if (file_preview) {
                    file_preview.innerHTML = uploaded_files.length ? uploaded_files.map(file => `
                        <div style="margin-top: 5px;">
                            <a href="${file}" target="_blank">${file.split('/').pop()}</a>
                        </div>
                    `).join('') : __("No files uploaded yet.");
                }
            },
            on_error(error) {
                frappe.show_alert({
                    message: __("Failed to upload file: {0}", [error.message]),
                    indicator: 'red'
                });
            }
        });
    },

    submit_feedback: async function (values, uploaded_files, dialog, company) {
        dialog.set_primary_action(__('Submitting...'), null);
        values.attachments = uploaded_files;

        try {
            const response = await frappe.call({
                method: 'ksa_compliance.customer_feedback.send_feedback_email',
                args: {
                    company: company,
                    subject: values.subject,
                    description: values.description,
                    attachments: values.attachments
                }
            });

            if (response.success) {
                frappe.show_alert({
                    message: response.message,
                    indicator: 'green'
                });
                dialog.hide();
            } else {
                throw new Error(response.message);
            }
        } catch (error) {
            frappe.show_alert({
                message: __("An error occurred while submitting your feedback"),
                indicator: 'red'
            });
            console.error(error);
        } finally {
            dialog.set_primary_action(__('Submit'), () => dialog.primary_action(values));
        }
    }
};