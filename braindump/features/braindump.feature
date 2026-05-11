Feature: write_braindump creates correct file

  Scenario: Writing a basic braindump creates a Markdown file
    Given a temporary notes directory
    When write_braindump is called with topic "Test Topic" and body "Test body"
    Then a .md file is created in the notes directory

  Scenario: The file contains YAML frontmatter
    Given a temporary notes directory
    When write_braindump is called with topic "Test Topic" and body "Test body"
    Then the file starts with "---"
    And the frontmatter contains "topic: Test Topic"

  Scenario: The file contains the topic as an H1 heading
    Given a temporary notes directory
    When write_braindump is called with topic "Test Topic" and body "Test body"
    Then the file body contains "# Test Topic"

  Scenario: Tasks are written as checkboxes
    Given a temporary notes directory
    When write_braindump is called with tasks ["Task 1", "Task 2"]
    Then the file contains "- [ ] Task 1"
    And the file contains "- [ ] Task 2"

  Scenario: Files are listed under a Files Referenced section
    Given a temporary notes directory
    When write_braindump is called with files ["/path/to/file.py"]
    Then the file contains "## Files Referenced"
    And the file contains "`/path/to/file.py`"

  Scenario: Tags are included in frontmatter
    Given a temporary notes directory
    When write_braindump is called with tags ["python", "test"]
    Then the frontmatter contains "python"
    And the frontmatter contains "test"

Feature: last_braindump_age_hours

  Scenario: Returns None when no files exist
    Given an empty temporary notes directory
    When last_braindump_age_hours is called
    Then it returns None

  Scenario: Returns a small value for a recently created file
    Given a temporary notes directory with a file written just now
    When last_braindump_age_hours is called
    Then it returns a value less than 1

  Scenario: Returns a large value for an old file
    Given a temporary notes directory with a file whose mtime is 48 hours ago
    When last_braindump_age_hours is called
    Then it returns a value greater than 24

Feature: nudge_message

  Scenario: Returns a message when no files exist
    Given an empty temporary notes directory
    When nudge_message is called
    Then it returns a non-None string mentioning "/braindump"

  Scenario: Returns None when a recent file exists
    Given a temporary notes directory with a file written just now
    When nudge_message is called
    Then it returns None

  Scenario: Returns a message mentioning elapsed hours when overdue
    Given a temporary notes directory with a file whose mtime is 48 hours ago
    When nudge_message is called
    Then it returns a non-None string mentioning "48h"
