Feature: Sign in
  Users sign in with email and password. Every other endpoint requires a session.

  Background:
    Given the seeded user "member@northwind.test" with role "member" in tenant "Northwind Supply"

  Scenario: Successful sign-in returns a session
    When I sign in as "member@northwind.test" with password "demo-password"
    Then the response status is 200
    And the response contains an access token
    And a "session" cookie is set as HttpOnly

  Scenario: Wrong password is rejected without revealing which field was wrong
    When I sign in as "member@northwind.test" with password "wrong-password"
    Then the response status is 401
    And the error code is "invalid_credentials"

  Scenario: Unknown email is rejected the same way as a wrong password
    When I sign in as "nobody@northwind.test" with password "demo-password"
    Then the response status is 401
    And the error code is "invalid_credentials"

  Scenario: Current user is returned for a valid session
    Given I am signed in as "member@northwind.test"
    When I request my profile
    Then the response status is 200
    And the profile shows role "member" and tenant "Northwind Supply"

  Scenario: Requests without a session are rejected
    When I request my profile without signing in
    Then the response status is 401
    And the error code is "not_authenticated"

  Scenario: Signing out clears the session cookie
    Given I am signed in as "member@northwind.test"
    When I sign out
    Then the response status is 204
    And the "session" cookie is cleared
