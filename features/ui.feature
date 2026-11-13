# No test in this repo covers these scenarios, on purpose. They are agent-eval-gate's UI
# benchmark (benchmarks/vendor-intake-ui), whose reference tests live there. An agent writing a
# UI test from one of them must not find an existing test to copy.
Feature: Use the web app
  What people see and do in the browser. The API behavior behind these screens is specified in
  the other feature files; these scenarios cover what the screens show and allow.

  Scenario: Filter the vendor list by status
    Given I am signed in as "member@northwind.test"
    And a draft vendor and a vendor in review
    When I filter the vendor list by status "In review"
    Then the vendor in review is listed
    And the draft vendor is not listed
    And the page address keeps the filter, so the view can be shared

  Scenario: A search that matches nothing says so
    Given I am signed in as "member@northwind.test"
    When I search the vendor list for a name no vendor has
    Then the list says "No vendors match these filters."

  Scenario: Page through the vendor list
    Given I am signed in as "member@northwind.test"
    And more than 10 vendors exist
    When I go to the next page of the vendor list
    Then the list shows vendors 11 onward, for example "Showing 11–20 of 34"
    And "Previous" can be used to go back

  Scenario: Requesting changes needs a note
    Given I am signed in as "reviewer@northwind.test"
    And a vendor in review
    When I request changes to its W-9 without writing a note
    Then I see "Add a note so the member knows what to fix."
    And the vendor is still in the review queue

  Scenario: An expired insurance certificate is flagged in the vendor list
    Given I am signed in as "member@northwind.test"
    And a vendor whose insurance certificate expired on 2020-01-31
    When I find that vendor in the vendor list
    Then its row says "Insurance expired"

  Scenario: Insurance expiring within 30 days is flagged on the vendor page
    Given I am signed in as "member@northwind.test"
    And a vendor whose insurance certificate expires 10 days from today
    When I open the vendor's page
    Then it says "Insurance expires within 30 days"

  Scenario: The activity log lists what happened in order
    Given I am signed in as "member@northwind.test"
    And a vendor I created and then uploaded a W-9 to
    When I open the vendor's page
    Then the activity log shows "Created the vendor" before "Uploaded a document"

  Scenario: A vendor can't be submitted until every document is extracted
    Given I am signed in as "member@northwind.test"
    And a draft vendor with only an extracted W-9
    When I open the vendor's page
    Then "Submit for review" is disabled
    And the page says "Still needed: Insurance certificate, Contract"

  Scenario: The review queue shows the lowest-confidence vendor first
    Given I am signed in as "reviewer@northwind.test"
    And two vendors in review, one with an insurance expiry date that couldn't be read
    When I open the review queue
    Then the vendor with the unreadable date is listed above the other

  Scenario: An uploaded document can be replaced
    Given I am signed in as "member@northwind.test"
    And a draft vendor with an uploaded W-9
    When I open the vendor's page
    Then the W-9 control reads "Replace W-9"
    And the contract control still reads "Upload Contract"
