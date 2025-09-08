import os
import json
import urllib.parse
from typing import cast
import requests
from requests import HTTPError

import frappe
from frappe import _
from frappe.utils import get_url
from frappe.core.doctype.file.file import File
from erpnext.setup.doctype.company.company import Company

from ksa_compliance import logger


@frappe.whitelist(methods=['GET'])
def get_feedback_settings():
    """Get feedback settings from ZATCA Feedback Settings"""
    email_accounts = frappe.db.get_list('Email Account', fields=['email_id'], filters={'default_outgoing': 1}, limit=1)
    feedback_destination_site_url = (
        frappe.conf.get('feedback_destination_site_url', 'https://lavaloon.com/').rstrip('/') + '/'
    )

    api_url = urllib.parse.urljoin(
        feedback_destination_site_url, 'api/method/frappe_feedback.api.create_customer_feedback'
    )

    settings_dict = {
        'API_URL': api_url,
        'LAVALOON_CONTACT_PAGE': 'https://lavaloon.com/contact-us',
        'MAX_FILE_SIZE_MB': 5,
        'MAX_NUMBER_OF_FILES': 3,
        'ALLOWED_FILE_TYPES': ['.pdf', '.png', '.jpeg', '.docx'],
        'MAX_DESCRIPTION_LENGTH': 1500,
        'EMAIL_ACCOUNT': email_accounts[0].email_id if email_accounts else '',
    }

    return settings_dict


@frappe.whitelist()
def send_feedback_email(company: str, subject: str, description: str, attachments: str = None):
    """Send feedback email using the default email account"""
    try:
        config = get_feedback_settings()

        email_content = f"""
        <h3>Feedback Details</h3>
        <p>{description}</p>
        """

        company_doc = cast(Company, frappe.get_doc('Company', company))
        company_email = company_doc.email
        company_phone = company_doc.phone_no
        email_content += f"""
            <h4>Company Information:</h4>
            <p>Company Name: {company}</p>
            <p>Company Email: {company_email if company_email else 'N/A'}</p>
            <p>Company Phone: {company_phone if company_phone else 'N/A'}</p>
        """

        if attachments:
            attachments = json.loads(attachments)
            email_content += '<h4>Attachments:</h4><ul>'
            for attachment in attachments:
                file_doc = cast(File, frappe.get_doc('File', {'file_url': attachment}))
                file_extension = os.path.splitext(file_doc.file_name)[1].lower()
                if file_extension not in config['ALLOWED_FILE_TYPES']:
                    frappe.throw(_('Invalid file type: {0}').format(file_extension))
                if file_doc.file_size > config['MAX_FILE_SIZE_MB'] * 1024 * 1024:
                    frappe.throw(
                        _('File size exceeds the maximum limit of {0}MB: {1}').format(
                            config['MAX_FILE_SIZE_MB'], file_doc.file_name
                        )
                    )

                if file_doc.is_private:
                    existing_file = frappe.db.exists('File', {'content_hash': file_doc.content_hash, 'is_private': 0})
                    if existing_file:
                        file_doc = cast(File, frappe.get_doc('File', existing_file))
                    else:
                        file_doc.is_private = 0
                        file_doc.save(ignore_permissions=True)
                full_url = get_url(file_doc.file_url)
                email_content += f"<li><a href='{full_url}'>{file_doc.file_name}</a></li>"
            email_content += '</ul>'

        api_url = config['API_URL']
        body = {'subject': f'KSA Compliance App Feedback: {subject}', 'content': email_content}

        try:
            response = requests.post(api_url, json=body)
            response.raise_for_status()
            frappe.response['message'] = _('Feedback email sent successfully')
            frappe.response['http_status_code'] = 200
            frappe.response['success'] = True
        except frappe.exceptions.RateLimitExceededError as e:
            logger.error(f'Rate limit exceeded: {e}')
            frappe.response['message'] = _('Rate limit exceeded. Please try again later.')
            frappe.response['http_status_code'] = 429
            frappe.response['success'] = False
        except HTTPError as e:
            frappe.log_error(frappe.get_traceback(), 'Feedback Email Error')
            error = e.response
            logger.error(f'An HTTP error occurred: {error}')
            if e.response.text:
                logger.info(f'Response: {e.response.text}')

    except Exception as e:
        logger.error(f'An error occurred while sending feedback email: {e}')
        frappe.log_error(frappe.get_traceback(), 'Feedback Email Error')
        frappe.response['message'] = str(e)
        frappe.response['http_status_code'] = 500
        frappe.response['success'] = False
        return
