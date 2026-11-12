Feature: Vendor lifecycle
  What happens across a vendor's whole life: documents replaced, reviews sent back and resubmitted,
  boundary dates, renames, and the list's search and paging. Each scenario crosses more than one
  request or role.

  Scenario: A re-uploaded document is the one that gets reviewed
    Given I am signed in as "member@northwind.test"
    And a draft vendor with extracted "insurance_certificate" and "contract" documents
    And I upload a "w9" whose legal name is "First Name LLC" and it is extracted
    And I upload another "w9" whose legal name is "Second Name LLC" and it is extracted
    When I submit the vendor and a reviewer opens the review queue
    Then the vendor's "w9" extraction in the queue shows legal name "Second Name LLC"
    And the vendor's documents list both uploads, oldest first

  Scenario: Rejecting one document sends the whole vendor back
    Given I am signed in as "reviewer@northwind.test"
    And a vendor in review with three pending extractions
    When I reject the "contract" extraction with the note "Wrong counterparty"
    Then the vendor status is "rejected"
    And audit events "extraction.rejected" and then "vendor.rejected" are recorded

  Scenario: Once a vendor is sent back, its other documents cannot be decided
    Given I am signed in as "reviewer@northwind.test"
    And a vendor in review whose "w9" extraction I have rejected
    When I approve its "contract" extraction
    Then the response status is 409
    And the error code is "vendor_not_in_review"

  Scenario: Resubmitting without replacing the rejected document is refused
    Given I am signed in as "member@northwind.test"
    And a vendor whose "w9" extraction a reviewer rejected
    When I submit the vendor for review again
    Then the response status is 409
    And the error code is "documents_incomplete"
    And the error lists missing kind "w9" only

  Scenario: After a replacement, only the new document waits for review
    Given I am signed in as "member@northwind.test"
    And a vendor whose "insurance_certificate" and "contract" extractions a reviewer approved and whose "w9" extraction a reviewer rejected
    When I upload a new "w9", wait for it to be extracted, and submit the vendor again
    Then the vendor status is "in_review"
    And the review queue lists the vendor with exactly one pending extraction, of kind "w9"

  Scenario: Approving the replacement approves a vendor whose other documents were already approved
    Given I am signed in as "reviewer@northwind.test"
    And a resubmitted vendor whose only pending extraction is a replacement "w9"
    When I approve the "w9" extraction
    Then the vendor status is "approved"
    And an audit event "vendor.approved" is recorded

  Scenario: A certificate that expires today can still be approved
    Given I am signed in as "reviewer@northwind.test"
    And a vendor in review whose insurance certificate expires today
    When I approve the "insurance_certificate" extraction
    Then the response status is 200
    And the extraction status is "approved"

  Scenario: A certificate whose expiry date could not be read cannot be approved
    Given I am signed in as "reviewer@northwind.test"
    And a vendor in review whose insurance certificate has the expiry date "next spring"
    When I approve the "insurance_certificate" extraction
    Then the response status is 409
    And the error code is "insurance_expiry_missing"
    And the extraction is still pending review

  Scenario: A vendor that was sent back can be edited again
    Given I am signed in as "member@northwind.test"
    And a vendor whose "contract" extraction a reviewer rejected
    When I change the vendor's name
    Then the response status is 200
    And the vendor has the new name

  Scenario: A vendor cannot be renamed to another vendor's name, whatever the case
    Given I am signed in as "member@northwind.test"
    And draft vendors named "Atlas Freight" and "Borealis Freight"
    When I rename "Borealis Freight" to "ATLAS FREIGHT"
    Then the response status is 409
    And the error code is "vendor_name_taken"
    And "Borealis Freight" keeps its name

  Scenario: Sign-in ignores the case of the email address
    When I sign in as "Member@Northwind.TEST" with the right password
    Then the response status is 200
    And the current user's email is "member@northwind.test"

  Scenario: An admin can review vendors
    Given I am signed in as "admin@northwind.test"
    And a vendor in review with three pending extractions
    When I open the review queue and approve the vendor's "w9" extraction
    Then the queue lists the vendor
    And the response status is 200

  Scenario: Search ignores case and matches part of a name
    Given I am signed in as "member@northwind.test"
    And a vendor named "Zephyrine Cold Storage"
    When I list vendors with search "COLD stor"
    Then the vendor is in the results

  Scenario: Search and the status filter apply together
    Given I am signed in as "member@northwind.test"
    And two vendors whose names contain the same unique word, one draft and one in review
    When I list vendors with that word as the search and status "in_review"
    Then the results are exactly the vendor in review
    And the total is 1

  Scenario: A page past the last vendor is empty but still reports the total
    Given I am signed in as "member@northwind.test"
    When I list vendors with an offset beyond the total number of vendors
    Then the response status is 200
    And the items are empty
    And the total is the same as for the first page
