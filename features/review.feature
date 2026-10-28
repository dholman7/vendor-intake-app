Feature: Review vendors
  A member submits a vendor once all three documents are extracted. Reviewers approve or
  reject each extraction. A vendor is approved when every extraction is approved.

  Scenario: Submit a vendor with all documents extracted
    Given I am signed in as "member@northwind.test"
    And a draft vendor with extracted "w9", "insurance_certificate", and "contract" documents
    When I submit the vendor for review
    Then the response status is 200
    And the vendor status is "in_review"
    And an audit event "vendor.submitted" is recorded

  Scenario: Submitting with missing documents lists what is missing
    Given I am signed in as "member@northwind.test"
    And a draft vendor with only an extracted "w9" document
    When I submit the vendor for review
    Then the response status is 409
    And the error code is "documents_incomplete"
    And the error lists missing kinds "contract" and "insurance_certificate"

  Scenario: The review queue shows lowest confidence first
    Given I am signed in as "reviewer@northwind.test"
    And two vendors are in review, one with an insurance expiry date that could not be parsed
    When I open the review queue
    Then the vendor with the unparsed date is listed before the other
    And the queue is ordered by each item's lowest field confidence, lowest first

  Scenario: Members cannot see the review queue
    Given I am signed in as "member@northwind.test"
    When I open the review queue
    Then the response status is 403
    And the error code is "forbidden"

  Scenario: Approving every extraction approves the vendor
    Given I am signed in as "reviewer@northwind.test"
    And a vendor in review with three pending extractions
    When I approve all three extractions
    Then the vendor status is "approved"
    And an audit event "vendor.approved" is recorded

  Scenario: Rejecting an extraction requires a note and returns the vendor to the member
    Given I am signed in as "reviewer@northwind.test"
    And a vendor in review with three pending extractions
    When I reject the W-9 extraction without a note
    Then the response status is 422
    When I reject the W-9 extraction with note "Tax ID does not match"
    Then the vendor status is "rejected"
    And an audit event "extraction.rejected" is recorded

  Scenario: An expired insurance certificate cannot be approved
    Given I am signed in as "reviewer@northwind.test"
    And a vendor in review whose insurance certificate expired yesterday
    When I approve the insurance certificate extraction
    Then the response status is 409
    And the error code is "insurance_expired"

  Scenario Outline: Insurance expiring within 30 days is flagged
    Given a vendor whose insurance certificate expires in <days> days
    When I request the vendor
    Then the vendor flags <include> "insurance_expiring_soon"

    Examples:
      | days | include         |
      | 0    | include         |
      | 30   | include         |
      | 31   | do not include  |
