import frappe


def execute():
    """
    Add a custom HTML block to the ZATCA Workspace for feedback and link section.
    """
    block_name = 'ZATCA Workspace - Feedback and Link Section'

    html_content = """
                        <div>
                            <div>
                                <a href="javascript:void(0);" onclick="ksa_compliance.feedback_dialog.show_feedback_dialog(__('Submit Feedback'));" class="link-item" style="font-weight: bold;">
                                Give Feedback <span style="margin-left: 0.25rem;">📝</span>
                                </a>
                            </div>

                            <div>
                                <a href="https://lavaloon.com/contact-us" target="_blank" class="link-item">
                                LavaLoon Contact <span style="margin-left: 0.25rem;">↗</span>
                                </a>
                            </div>
                            <div>
                                <a href="https://github.com/lavaloon-eg/ksa_compliance" target="_blank" class="link-item">
                                KSA Compliance GitHub <span style="margin-left: 0.25rem;">↗</span>
                                </a>
                            </div>
                            <div>
                                <a href="https://lavaloon.com/wiki/E-INVOICE%20KSA%20(Zatca%20)" target="_blank" class="link-item">
                                ZATCA Wiki <span style="margin-left: 0.25rem;">↗</span>
                                </a>
                            </div>
                        </div>
                    """

    css_style = """
                    .link-item {
                        display: flex;
                        text-decoration: none;
                        font-size: var(--text-base);
                        font-weight: var(--weight-regular);
                        letter-spacing: 0.02em;
                        color: var(--text-color);
                        padding: 4px;
                        margin-left: -4px;
                        margin-bottom: 0px;
                        border-radius: var(--border-radius-md);
                        cursor: pointer;
                    }
                    .link-item:hover {
                        color: var(--primary-color);
                        text-decoration: none;
                    }

                    html[dir="rtl"] ul {
                        margin-right: 0px;
                    }

                    html[dir="rtl"] .link-item {
                        margin-left: 0px;
                        margin-right: -4px;
                    }
                """

    if frappe.db.exists('Custom HTML Block', block_name):
        custom_block_doc = frappe.get_doc('Custom HTML Block', block_name)
        custom_block_doc.html = html_content
        custom_block_doc.style = css_style
        custom_block_doc.save()
        frappe.db.commit()
        print(f'Custom HTML Block {block_name} updated successfully.')
    else:
        custom_block_doc = frappe.new_doc('Custom HTML Block')
        custom_block_doc.name = block_name
        custom_block_doc.html = html_content
        custom_block_doc.style = css_style
        custom_block_doc.insert()
        frappe.db.commit()
        print(f'Custom HTML Block {block_name} created successfully.')

    print('Done.')
