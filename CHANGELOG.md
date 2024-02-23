# Overview

This file should contain release notes between tagged versions of the product. Please update this file with your pull
requests so that whoever deploys a given version can file the relevant changes under the corresponding version.

Add changes to the "Unreleased Changes" section. Once you create a version (and tag it), move the unreleased changes
to a section with the version name.

## Unreleased Changes

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