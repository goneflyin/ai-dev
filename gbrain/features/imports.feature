Feature: Module import smoke tests

  Scenario: todoist_helper imports without errors
    Given the gbrain directory is on sys.path
    When "import todoist_helper" is executed
    Then no ImportError or SyntaxError is raised

  Scenario: review_matter imports without errors
    Given the gbrain directory is on sys.path
    When "import review_matter" is executed
    Then no ImportError or SyntaxError is raised

  Scenario: status_collect imports without errors
    Given the gbrain directory is on sys.path
    When "import status_collect" is executed
    Then no ImportError or SyntaxError is raised

  Scenario: sync_matter imports without errors (skipped if requests not installed)
    Given the gbrain directory is on sys.path
    When "import sync_matter" is executed
    Then no SyntaxError is raised
    And if requests is not installed the test is skipped
