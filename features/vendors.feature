Feature: Manage vendors
  Members create vendor records and keep them up to date until they are submitted for review.
  Vendors are always scoped to the signed-in user's tenant.

  Background:
    Given I am signed in as "member@northwind.test"

  Scenario: Create a vendor
    When I create a vendor named "Acme Freight" in category "logistics" with contact "ops@acmefreight.example"
    Then the response status is 201
    And the vendor status is "draft"
    And an audit event "vendor.created" is recorded

  Scenario Outline: Reject invalid vendor fields
    When I create a vendor with <field> set to <value>
    Then the response status is 422
    And the error code is "validation_error"
    And the error names the field "<field>"

    Examples:
      | field         | value             |
      | name          | "A"               |
      | category      | "furniture"       |
      | contact_email | "not-an-email"    |

  Scenario: Vendor names are unique within a tenant
    Given a vendor named "Acme Freight" already exists in my tenant
    When I create a vendor named "acme freight" in category "logistics" with contact "ops@acmefreight.example"
    Then the response status is 409
    And the error code is "vendor_name_taken"

  Scenario: The same vendor name is allowed in a different tenant
    Given a vendor named "Acme Freight" exists in tenant "Globex Procurement"
    When I create a vendor named "Acme Freight" in category "logistics" with contact "ops@acmefreight.example"
    Then the response status is 201

  Scenario: List vendors with search, status filter, and pagination
    Given my tenant has 25 vendors, 5 of which are "approved"
    When I list vendors with status "approved"
    Then I receive 5 vendors and a total of 5
    When I list vendors with limit 10 and offset 20
    Then I receive 5 vendors and a total of 25
    When I search vendors for "freight"
    Then every returned vendor name contains "freight", ignoring case

  Scenario: Pagination limits are enforced
    When I list vendors with limit 101
    Then the response status is 422

  Scenario: Vendors from another tenant are invisible
    Given a vendor exists in tenant "Globex Procurement"
    When I request that vendor by id
    Then the response status is 404
    And the error code is "vendor_not_found"

  Scenario: Update a draft vendor
    Given a vendor in status "draft"
    When I change its contact email to "billing@acmefreight.example"
    Then the response status is 200
    And an audit event "vendor.updated" is recorded

  Scenario: A vendor under review cannot be edited
    Given a vendor in status "in_review"
    When I change its contact email to "billing@acmefreight.example"
    Then the response status is 409
    And the error code is "vendor_locked"
