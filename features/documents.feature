Feature: Upload vendor documents
  Each vendor needs a W-9, an insurance certificate, and a contract. Uploaded documents are
  processed in the background and fields are extracted with a confidence score per field.

  Background:
    Given I am signed in as "member@northwind.test"
    And a vendor in status "draft"

  Scenario: Upload a document
    When I upload "insurance_certificate.txt" as kind "insurance_certificate"
    Then the response status is 201
    And the document status is "processing"
    And an audit event "document.uploaded" is recorded

  Scenario: Extraction completes in the background
    Given I uploaded "insurance_certificate.txt" as kind "insurance_certificate"
    When processing finishes
    Then the document status is "extracted"
    And the extraction has fields "insurer", "policy_number", "coverage_amount", "expiry_date"
    And every field has a confidence between 0 and 1

  Scenario: Fields that cannot be parsed get low confidence
    Given I uploaded an insurance certificate whose expiry date is "next spring"
    When processing finishes
    Then the "expiry_date" field has a null value and confidence below 0.5

  Scenario Outline: Reject invalid uploads
    When I upload <file> as kind "<kind>"
    Then the response status is <status>
    And the error code is "<code>"

    Examples:
      | file                         | kind                  | status | code                 |
      | an empty file                | w9                    | 422    | empty_file           |
      | a file of exactly 10 MiB + 1 | w9                    | 413    | file_too_large       |
      | a ".exe" file                | w9                    | 415    | unsupported_type     |
      | a valid text file            | passport              | 422    | validation_error     |

  Scenario: A file of exactly 10 MiB is accepted
    When I upload a text file of exactly 10 MiB as kind "contract"
    Then the response status is 201

  Scenario: Documents cannot be added to a vendor under review
    Given the vendor is in status "in_review"
    When I upload "w9.txt" as kind "w9"
    Then the response status is 409
    And the error code is "vendor_locked"

  Scenario: Documents from another tenant are invisible
    Given a document exists in tenant "Globex Procurement"
    When I request that document by id
    Then the response status is 404
    And the error code is "document_not_found"
