Feature: Error handling

  Scenario: Requesting a non-existent article returns 404
    Given the review server is running
    When I GET /api/articles/nonexistent-id-xyz
    Then the response status is 404
    And the JSON body has ok=false
    And the JSON body contains an "error" field

  Scenario: Requesting an unknown path returns 404
    Given the review server is running
    When I GET /api/notarealendpoint
    Then the response status is 404

  Scenario: POST with non-integer Content-Length is handled gracefully
    Given the review server is running
    When I POST to /api/action with Content-Length set to "notanumber"
    Then the server does not crash (returns any HTTP response)

  Scenario: POST with invalid JSON body returns 400
    Given the review server is running
    When I POST to /api/action with body "not valid json"
    Then the response status is 400
    And the JSON body has ok=false
