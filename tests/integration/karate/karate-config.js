function fn() {
  var baseUrl = java.lang.System.getProperty('apiBaseUrl') || 'http://127.0.0.1:12800/api/v1';
  var token = java.lang.System.getProperty('apiToken') || 'mock_token';
  return {
    apiBaseUrl: baseUrl,
    apiToken: token
  };
}
