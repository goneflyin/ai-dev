Feature: Server starts and responds

  Scenario: Server starts on configured port
    Given the review server is started on a random port
    Then GET / returns status 200
    And the response Content-Type is text/html

  Scenario: Dashboard route responds
    Given the review server is started on a random port
    When I GET /dashboard
    Then the response status is 200

  Scenario: Response body contains dashboard title
    Given the review server is started on a random port
    When I GET /
    Then the HTML body contains "gBrain Review Dashboard"
