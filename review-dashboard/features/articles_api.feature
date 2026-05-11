Feature: Article list API

  Scenario: Articles endpoint returns JSON with correct schema
    Given the review server is running with one test article
    When I GET /api/articles
    Then the response status is 200
    And the response Content-Type is application/json
    And the JSON body contains keys: total, articles, annotated, unannotated

  Scenario: Article list items have required metadata fields
    Given the review server is running with one test article
    When I GET /api/articles
    Then each article in "articles" has fields: id, title, url, source, has_annotations, annotation_count

  Scenario: Article list does not include full content
    Given the review server is running with one test article
    When I GET /api/articles
    Then no article in "articles" has a "full_content" field

Feature: Single article API

  Scenario: Fetching an existing article returns ok=true and full content
    Given the review server is running with a test article whose id is "test-article-001"
    When I GET /api/articles/test-article-001
    Then the response status is 200
    And the JSON body has ok=true
    And the article has a "full_content" field

  Scenario: Full content is non-empty
    Given the review server is running with a test article
    When I GET /api/articles/test-article-001
    Then the article "full_content" is not empty

  Scenario: Article metadata matches frontmatter
    Given the review server is running with a test article whose title is "Test Article"
    When I GET /api/articles/test-article-001
    Then the article "title" equals "Test Article"
