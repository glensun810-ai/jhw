{
  "testEnvironment": "node",
  "testMatch": ["**/tests/**/*.test.js"],
  "collectCoverageFrom": [
    "services/**/*.js",
    "utils/**/*.js",
    "api/**/*.js",
    "!**/node_modules/**"
  ],
  "coverageThreshold": {
    "global": {
      "branches": 50,
      "functions": 50,
      "lines": 50,
      "statements": 50
    }
  },
  "verbose": true,
  "collectCoverage": true,
  "coverageReporters": ["text", "html", "json-summary"]
}
