Feature: Markdown rendering (JavaScript)

  Background:
    The markdownToHtml function is embedded in the HTML served at GET /.
    Tests verify that the correct JS patterns are present in the source.

  Scenario: Link rendering pattern is present
    Given the dashboard HTML source
    Then the source contains a JS regex for converting [text](url) to anchor tags

  Scenario: Code block rendering pattern is present
    Given the dashboard HTML source
    Then the source contains a JS regex for converting triple-backtick code blocks to <pre><code>

  Scenario: Image rendering from Markdown image syntax
    Given the dashboard HTML source
    Then the source contains a JS regex for converting ![alt](url) to <img> tags

  Scenario: Paragraph handling pattern is present
    Given the dashboard HTML source
    Then the source contains a JS replacement for double-newlines to </p><p>

  Scenario: Heading patterns are present
    Given the dashboard HTML source
    Then the source contains JS replacements for # h1, ## h2, and ### h3 headings

Feature: JavaScript parse verification

  Scenario: Module imports cleanly with no SyntaxWarnings
    Given the review_server.py source file
    When imported with Python's -W error flag
    Then no SyntaxWarning or SyntaxError is raised

  Scenario: DASHBOARD_HTML is a valid non-empty string
    Given the review_server module is imported
    Then DASHBOARD_HTML is a string
    And DASHBOARD_HTML length is greater than 1000 characters

  Scenario: JavaScript functions are present in DASHBOARD_HTML
    Given the review_server module is imported
    Then DASHBOARD_HTML contains function definitions for:
      markdownToHtml, loadArticles, selectArticle, escapeHtml, filterArticles
