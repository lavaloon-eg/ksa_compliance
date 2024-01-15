# KSA Compliance App

## Description

We are building an app for KSA E-invoice to inregrate with Zakat, Tax and Customs Authority (ZATCA)

## Technical Background

To ingtegrate with ZATCA they suggest a three phases approach:

First thing is to integrate with their SDK (offline dowladable Command Line Interface program)

Secondly to integrate with their sandbox APIs that are very similar but not identical to their production version.

Finally, every thing can be tested and validated for production environment.

The creation of E-invoice requires sending up to 150 fields in an xml specified format to ZATCA and to store and send to user QR code with the XML data to validate the transaction

Data fields and validations excel sheet Link: https://lavaloon.sharepoint.com/:x:/s/LavaDo/EUM58LvaNq1BqPHVD0SgjjMB3vN1xOEnutvtZ3Fo2Et3iQ?e=cvAzbc

## Technical Approach and Challenges

Implement a python class in KSA Compliance app that maps the fields with their validations to xml library element tree builder.

Also, there are some fields that will need like in the cryptographic stamp identifier (CSID) field that will include a hashed key using SHA-256 and Certificate Signing Request (CSR) that will need a more complex structing and mapping.

Example CSID field

```xml
In the UBL extension
<ext:UBLExtensions>
        <ext:UBLExtension>
            <ext:ExtensionURI>urn:oasis:names:specification:ubl:dsig:enveloped:xades</ext:ExtensionURI>
            <ext:ExtensionContent>
                <sig:UBLDocumentSignatures xmlns:sac="urn:oasis:names:specification:ubl:schema:xsd:SignatureAggregateComponents-2" xmlns:sbc="urn:oasis:names:specification:ubl:schema:xsd:SignatureBasicComponents-2" xmlns:sig="urn:oasis:names:specification:ubl:schema:xsd:CommonSignatureComponents-2">
                    <sac:SignatureInformation>
                        <cbc:ID>urn:oasis:names:specification:ubl:signature:1</cbc:ID>
                        <sbc:ReferencedSignatureID>urn:oasis:names:specification:ubl:signature:Invoice</sbc:ReferencedSignatureID>
                        <ds:Signature Id="signature" xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
                            <ds:SignedInfo>
                                <ds:CanonicalizationMethod Algorithm="http://www.w3.org/2006/12/xml-c14n11"/>
                                <ds:SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#ecdsa-sha256"/>
                                <ds:Reference Id="invoiceSignedData" URI="">
                                    <ds:Transforms>
                                        <ds:Transform Algorithm="http://www.w3.org/TR/1999/REC-xpath-19991116">
                                            <ds:XPath>not(//ancestor-or-self::ext:UBLExtensions)</ds:XPath>
                                        </ds:Transform>
                                        <ds:Transform Algorithm="http://www.w3.org/TR/1999/REC-xpath-19991116">
                                            <ds:XPath>not(//ancestor-or-self::cac:Signature)</ds:XPath>
                                        </ds:Transform>
                                        <ds:Transform Algorithm="http://www.w3.org/TR/1999/REC-xpath-19991116">
                                            <ds:XPath>not(//ancestor-or-self::cac:AdditionalDocumentReference[cbc:ID='QR'])</ds:XPath>
                                        </ds:Transform>
                                        <ds:Transform Algorithm="http://www.w3.org/2006/12/xml-c14n11"/>
                                    </ds:Transforms>
                                    <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                                    <ds:DigestValue>tIgyb6RmuRm+rvj8tL5cbwK5eRk=</ds:DigestValue>
                                </ds:Reference>
                                <ds:Reference Type="http://www.w3.org/2000/09/xmldsig#SignatureProperties" URI="#xadesSignedProperties">
                                    <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                                    <ds:DigestValue>skZ+8g6hyUFzbbTZvJZRyAREMiM=</ds:DigestValue>
                                </ds:Reference>
                            </ds:SignedInfo>
                            <ds:SignatureValue>J3dQSz3nEQd8wagH2CBlip1fj03NTccYAQTGiU/4IhBYzylKxjB09OMBb5vXj2Lv7eXhciRoMmvSF+A9eIUd2a4b5aEm7VBkxIbyGgltNHR8u3oZ7Ee+HNWRAQU+IFCKpZoVA68Bo/g4Gy3pqNQoC7AOghUUXTjvFEBcHVgpt/5wDC8U3PwNfx9hzpU00t/b042GyLECGjPDzr8mGbI09mobT7sSb9oPPzxsC71dph+oU0ug+TAh2NheVih+HWCe870hFJvH3mZ9YcC/lcMXb80Ot+LSjgV8gcTSDz/BaOYLjEGvZrOxmoK2doUZNPi811tbq6nC4jjlrU+NRr5kQA==</ds:SignatureValue>
                            <ds:KeyInfo>
                                <ds:X509Data>
                                    <ds:X509Certificate>MIIDaDCCAlCgAwIBAgIKlswlvJ8beIpd9jANBgkqhkiG9w0BAQsFADBiMRkwFwYDVQQDExBNb2hkIEtoYWxpZmEgUDEyMRAwDgYDVQQKEwd0ZXMgcHdjMQkwBwYDVQQLEwAxGzAZBgkqhkiG9w0BCQEWDFRlc3RAcHdjLmNvbTELMAkGA1UEBhMCQUUwHhcNMjEwMjI1MTI1NjU3WhcNMjYwMjI1MTI1NjU3WjBiMRkwFwYDVQQDExBNb2hkIEtoYWxpZmEgUDEyMRAwDgYDVQQKEwd0ZXMgcHdjMQkwBwYDVQQLEwAxGzAZBgkqhkiG9w0BCQEWDFRlc3RAcHdjLmNvbTELMAkGA1UEBhMCQUUwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDWaRBaLHqhlZDDAf+YH2H2xgtHT9tMcg3vmGuP4YT2aeG77RWnIu0bqtNiNrOK+ph7UE+B2ClyW+CRixDx82Qkn9IUX+nw28QO7ux9UBDt3nIeL6euAUPMxrnyESALXXRjTLrJK3p6vsFr3hNbP4V0t/ZDAtk36PAn6WfKZICMI63GnzWLAQz6QOGvVmOYNym93Q84W9Ttn844yfun1EVj/+XC3bYmysTPbAgPZ/vT1UgeolOrvnsEKeDR8w43C1Juuw9CVi3duekYf1WVjfuNNClocjZ0N4D7dYdg536bqtc4F8C6sBmk/2YfG/Fsqb6DSU0FU1dSj+rjZvaR6tIDAgMBAAGjIDAeMA8GCSqGSIb3LwEBCgQCBQAwCwYDVR0PBAQDAgeAMA0GCSqGSIb3DQEBCwUAA4IBAQDACtfjpOtcy5dPp1tS31rB9lJ7aeQ6dayxJGyXGovhjYZ8N60sAR/0Yfe1EkjbFLV25AGw/06jZV7Fy8jK2jR7TJnv2QnxZz4ldg2k8DolC6J4YZqI5R0THFnd09MNHcgV6ChGJNzivRRkTrwFM0qWErTCh/5wA/GHgqRKjWUA/S2P7UbKbjIA5Ba6N3K/zT4DfspxvvCp50jigPyh1e/UilQdexNFUmkUyZBisKEhpdHURHCJY2ip0iH8wZtG4oiGtisLEHJT+ZREWIzjTUKlw9ImXu2e4ptzrPBPLMGdWdQ153YCkXFKLbV97JBUzilUhJ7GouDYKj3PnUzLMCSd</ds:X509Certificate>
                                </ds:X509Data>
                            </ds:KeyInfo>
                            <ds:Object>
                                <xades:QualifyingProperties Target="signature" xmlns:xades="http://uri.etsi.org/01903/v1.3.2#">
                                    <xades:SignedProperties Id="xadesSignedProperties">
                                        <xades:SignedSignatureProperties>
                                            <xades:SigningTime>2021-02-25T12:57:51Z</xades:SigningTime>
                                            <xades:SigningCertificate>
                                                <xades:Cert>
                                                    <xades:CertDigest>
                                                        <ds:DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
                                                        <ds:DigestValue>p6/1GNOqntK37JwfUub56vSecg0=</ds:DigestValue>
                                                    </xades:CertDigest>
                                                    <xades:IssuerSerial>
                                                        <ds:X509IssuerName>C=SA,  E=Test@test Taxpayer.com, OU=&quot;&quot;, O=test Taxpayer, CN=EGS0001</ds:X509IssuerName>
                                                        <ds:X509SerialNumber>1234</ds:X509SerialNumber>
                                                    </xades:IssuerSerial>
                                                </xades:Cert>
                                            </xades:SigningCertificate>
                                        </xades:SignedSignatureProperties>
                                    </xades:SignedProperties>
                                </xades:QualifyingProperties>
                            </ds:Object>
                        </ds:Signature>
                    </sac:SignatureInformation>
                </sig:UBLDocumentSignatures>
            </ext:ExtensionContent>
        </ext:UBLExtension>
    </ext:UBLExtensions>


In the main UBL
<cac:Signature>
        <cbc:ID>urn:oasis:names:specification:ubl:signature:Invoice</cbc:ID>
        <cbc:SignatureMethod>urn:oasis:names:specification:ubl:dsig:enveloped:xades</cbc:SignatureMethod>
    </cac:Signature>



```

