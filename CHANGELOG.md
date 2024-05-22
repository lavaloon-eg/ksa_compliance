# Overview

This file should contain release notes between tagged versions of the product. Please update this file with your pull
requests so that whoever deploys a given version can file the relevant changes under the corresponding version.

Add changes to the "Unreleased Changes" section. Once you create a version (and tag it), move the unreleased changes
to a section with the version name.

## Unreleased Changes

## 0.8.0

* Add Qr Image to sales invoice additional fields, to be used in print format.
* Create print format for all types of invoices
* Add Purchase Order Reference to Zatca generated XML file.

## 0.7.0

* Ignore permissions when inserting ZATCA integration log
* Fix item total amount in sales invoice additional fields for return invoices
* Abort submission for sales invoice additional field document if the status is resend.
* Update ZATCA integration log with Zatca status.
* Autoname method for ZATCA integration log.
* Add Last Attempt field in additional field doctype.
* Update incorrect sales invoice additional fields.
  * Set blank integration status to Resend.
  * Draft the updated documents to resend them again.
* Update NULL last attempt in sales invoice additional fields set equal to modified.
* Fix invoice submission error when lava_custom is not installed

## 0.6.0

* Add support for precomputed invoices from POS devices
* Make precomputed invoice and sales invoice additional fields UUID unique to safeguard against bugs causing double ZATCA submissions

## 0.5.0

* Update e-invoice sync patch
  * Change timeout to 58 minutes so that we can run it hourly
  * Run it hourly
  * Sort additional fields by creation (oldest first)
  * Run in batches (of 100 by default)
  * Add more logging


## 0.4.0

* Ignore permissions when creating sales invoice additional fields
* Skip additional fields for invoices issued before 2024-03-01
* Add a flag to control ZATCA XML validation and make it disabled by default
* Switch signed invoice XML from an attachment to a field for performance reasons

## 0.3.0

* Submit Sales invoice additional field directly only if the sync mode is live.
* Initialize e_invoicing_sync page to run the batch mode.
* Fix error when storing ZATCA API result
* Update invoice counter/hash logic to use locking to guarantee serialization
* Fix buyer details street name being included in the XML if not defined (used to insert an error as the street name)
* Fix payable amount in XML to be set using grand total.
* Adding Tax Total with Subtotal in XML To handle sending tax currency code.  
* Adding integration status field in sales invoice additional fields depends on response status code.
* Set invoice hash in sales invoice additional fields read only.
* E Invoicing Sync page to be shown in search bar.
* Fix taxable amount and Line price amount in XML to be net amount.
* Fix Credit note invoice submission issue.
* Skip additional fields if ZATCA settings are missing or setup is incomplete
* Add mode of payment "payment means code" custom field
* Use payment means code when generating XML to pass credit note validation
* Add support for compliance checks

## 0.2.0

* Use a hard-coded private key if the configured URL is for the sandbox environment
* Do not use ':' in XML filenames (from timestamp)
* Various fixes to simplified invoice format to pass validation
* Add invoice validation; messages/errors show up on a validation tab on the Sales Invoice Additional Fields doctype
* Improve API response handling

## 0.1.3

* Make the temp prefix is random

## 0.1.2

* Use a temporary prefix with temp file names to avoid clashes

## 0.1.1

* Fix certificate extraction from production CSID
* Fix previous invoice hash

## 0.1.0

* XML Templates:
    * Create Tax invoice template.
    * Create Simplified tax invoice template.
    * Add a method to generate XML regarding invoice type.
* Create E-Invoicing-Sync page to run the sync batch.
    * Initiate the batch flow to Sync E-invoices Individually.
* ZATCA Business Settings
    * Onboarding: Compliance and production CSID support
    * Signing and QR generation
    * Invoice reporting and clearance support, although it currently fails with bad request
