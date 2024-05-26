import base64

import frappe
from io import BytesIO
from frappe.utils.data import add_to_date, get_time, getdate
import datetime
from base64 import b64encode, b64decode
import pyqrcode


@frappe.whitelist()
def get_zatca_phase_1_qr_for_invoice(invoice_name: str) -> str:
    values_dict = get_qr_inputs(invoice_name)
    decoded_string = generate_decoded_string(values_dict)
    print("decoded_string",decoded_string)
    return generate_qrcode(decoded_string)


def get_qr_inputs(invoice_name):
    sales_invoice = frappe.get_doc("Sales Invoice", invoice_name)
    seller_name = sales_invoice.company
    if not frappe.get_value("ZATCA Phase 1 Business Settings", {"company": seller_name}):
        return None
    phase_1_settings = frappe.get_list("ZATCA Phase 1 Business Settings", filters={"company": seller_name}, fields=["*"])[0]
    if phase_1_settings.status == "Disabled":
        return None
    seller_vat_reg_no = phase_1_settings.vat_registration_number
    time = sales_invoice.posting_time
    timestamp = format_date(sales_invoice.posting_date, time)
    grand_total = sales_invoice.grand_total
    total_vat = sales_invoice.total_taxes_and_charges
    return {seller_name: [1], seller_vat_reg_no: [2], timestamp: [3], grand_total: [4], total_vat: [5]}


def generate_decoded_string(values_dict):
    encoded_text = ""
    for key in values_dict:
        encoded_text += encode_input(key, values_dict[key])
    # Decode hex result string into base64 format
    print("encoded_text",encoded_text)
    return b64encode(bytes.fromhex(encoded_text)).decode()


def encode_input(input, tag):
    """
        1- Convert bytes of tag into hex format.
        2- Convert bytes of encoded length of input into hex format.
        3- Convert encoded input itself into hex format.
        4- Concat All values into one string.
    """
    encoded_tag = bytes(tag).hex()
    if type(input) is str:
        encoded_length = bytes([len(input.encode('utf-8'))]).hex()
        encoded_value = input.encode('utf-8').hex()
    else:
        encoded_length = bytes([len(str(input).encode('utf-8'))]).hex()
        encoded_value = str(input).encode('utf-8').hex()
    return encoded_tag + encoded_length + encoded_value


def format_date(date, time):
    """
        Format date & time into UTC format something like : " 2021-12-13T10:39:15Z"
    """
    posting_date = getdate(date)
    time = get_time(time)
    combined_datetime = datetime.datetime.combine(posting_date, time)
    combined_utc = combined_datetime.astimezone(datetime.timezone.utc)
    time_stamp = combined_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
    return time_stamp


def generate_qrcode(data):
    if not data:
        return None
    qr = pyqrcode.create(data)
    with BytesIO() as buffer:
        qr.png(buffer, scale=7)
        buffer.seek(0)
        img_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return img_str
