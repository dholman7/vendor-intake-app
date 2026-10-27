Feature: Vendor audit trail
  Every state change on a vendor and its documents is recorded and can be listed in order.

  Scenario: Audit events are listed oldest first with actor and action
    Given I am signed in as "member@northwind.test"
    And I created a vendor and uploaded a W-9 for it
    When I request the vendor's audit trail
    Then the response status is 200
    And the actions are "vendor.created", "document.uploaded", "document.extracted" in that order
    And each event names the actor and a timestamp

  Scenario: Audit trails from another tenant are invisible
    Given I am signed in as "member@northwind.test"
    And a vendor exists in tenant "Globex Procurement"
    When I request that vendor's audit trail
    Then the response status is 404
