Feature: El Secretario - Local REST API Contract Integration Tests

  Background:
    * url apiBaseUrl
    * configure headers = { 'Authorization': '#("Bearer " + apiToken)', 'Accept': 'application/json' }

  Scenario: GET status returns standard application metadata and status
    Given path 'status'
    When method GET
    Then status 200
    And match response.app_name == 'El Secretario'
    And match response.version == '1.0.0'
    And match response.status == 'idle'
    And match response.processing_queue_backlog == 0

  Scenario: GET recordings returns array of recording summaries
    Given path 'recordings'
    When method GET
    Then status 200
    And match response == '#[]'
    And match each response == { id: '#number', title: '#string', date: '#string', duration_seconds: '#number', summary_generated: '#boolean', tags: '#[]' }

  Scenario: GET recordings/{id} retrieves full details of a specific record
    Given path 'recordings', 42
    When method GET
    Then status 200
    And match response.id == 42
    And match response.title == 'Mock Meeting'
    And match response.transcript == 'Hello'
    And match response.notes == 'None'
    And match response.summary == 'Some summary'
    And match response.tags == '#[]'

  Scenario: GET tasks board lists active tasks
    Given path 'tasks'
    When method GET
    Then status 200
    And match response == '#[]'
    And match each response == { id: '#number', title: '#string', description: '#string', due_date: '#string', completed: '#boolean' }

  Scenario: POST tasks programmatically inserts a card on the board
    Given path 'tasks'
    And request { title: 'Integration Test Task', description: 'Written via Karate Contract Test', due_date: '2026-09-30' }
    When method POST
    Then status 201
    And match response == { success: true, task_id: '#number', message: '#string' }

  Scenario: GET search retrieves semantic RAG matches with scores
    Given path 'search'
    And param query = 'hello'
    When method GET
    Then status 200
    And match response.query == 'hello'
    And match response.results == '#[]'
    And match each response.results == { source: '#string', source_id: '#number', title: '#string', text: '#string', relevance_score: '#number' }

  Scenario: POST record/start triggers microphone and POST record/stop ceases it
    Given path 'record/start'
    When method POST
    Then status 200
    And match response == { success: true, message: '#string' }

    # Stop recording
    Given path 'record/stop'
    When method POST
    Then status 200
    And match response == { success: true, message: '#string' }

  Scenario: GET status without Bearer token returns 401 Unauthorized
    Given path 'status'
    And configure headers = { 'Accept': 'application/json' }
    When method GET
    Then status 401
    And match response == { success: false, error: '#string' }
