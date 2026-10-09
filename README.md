# API Test Framework

A reusable Groovy-based framework for data-driven API integration testing with WireMock downstream service validation.

## Overview

This framework provides a complete toolkit for testing APIs that orchestrate multiple downstream services. It supports:

- **Data-driven testing** via YAML configuration (base + test-specific configs with deep merge)
- **WireMock integration** for downstream service stubbing and journal-based verification
- **Correlation strategies** (`default` timestamp-based and `fieldValue` extraction-based) for parallel test isolation
- **Field mapping validation** with extensible transformer registry
- **Auto-detection** of XML/JSON message formats
- **Allure reporting** with step-level annotations

## Package Structure

```
au.com.tpgtelecom.apitest
├── base/
│   ├── BaseApiSpec.groovy           # Core API testing spec (REST Assured + WireMock + Allure)
│   └── BaseDataDrivenApiSpec.groovy # Data-driven spec with YAML config + correlation
└── util/
    ├── EnvConfigHelper.groovy       # Environment-specific config loading
    ├── FieldTransformer.groovy      # Extensible field transformation registry
    ├── MessageProcessor.groovy      # XML/JSON auto-detection and field extraction
    ├── TestConfigLoader.groovy      # YAML config loading with deep merge + caching
    └── WireMockSupport.groovy       # WireMock journal analysis trait
```

## Quick Start

### 1. Add Dependency

**Gradle (composite build)**:
```groovy
// settings.gradle
includeBuild '../api-test-framework'  // or wherever the framework lives

// build.gradle
dependencies {
    testImplementation 'au.com.tpgtelecom:api-test-framework:1.0.0-SNAPSHOT'
}
```

**Gradle (published artifact)**:
```groovy
dependencies {
    testImplementation 'au.com.tpgtelecom:api-test-framework:1.0.0-SNAPSHOT'
}
```

### 2. Write a Test Spec

```groovy
package com.example.specs

import au.com.tpgtelecom.apitest.base.BaseDataDrivenApiSpec
import spock.lang.Unroll

class MyApiSpec extends BaseDataDrivenApiSpec {
    static String API_NAME = "my-api"

    @Unroll
    def "should execute my-api test: #testName"() {
        given: "Test configuration and payload are loaded"
        loadTestConfig(API_NAME, configFile)
        loadPayload()

        when: "The API service is called"
        def response = executeConfigurableApiCall()

        then: "Validate API response and downstream calls"
        validateConfigurableApiResponse(response)
        validateConfigurableDownstreamIntegrations()

        where:
        testName          | configFile           | description
        "Success_Flow"    | "success.yaml"       | "Happy path test"
        "Missing_Field"   | "missing-field.yaml" | "Validation error test"
    }
}
```

### 3. Create Config Files

**Base config** (`src/test/resources/api-configs/my-api/my-api-api-base.yaml`):
```yaml
apiUnderTest:
  path: "/api/my-endpoint"
  method: "POST"
  expectedStatusCode: 200

responseValidations:
  - fieldPath: "status"
    expectedValue: "SUCCESS"

downstreamValidations:
  downstream-service:
    urlPattern: "/downstream/.*${correlationId}.*"
    expectedMethod: "POST"
    expectedCalls: 0
    bodyFilter: false
    correlationStrategy: "default"
    correlationField: ""
    fieldMappings:
      - ["sourceField", "targetField", "identity"]
```

**Test config** (`src/test/resources/api-configs/my-api/test-configs/success.yaml`):
```yaml
apiUnderTest:
  payloadFile: "success-request.xml"
downstreamValidations:
  downstream-service:
    expectedCalls: 1
```

## Configuration

### Configurable Paths

The framework uses sensible defaults but allows overriding:

```groovy
// Override config base path (default: "src/test/resources/api-configs/")
TestConfigLoader.configBasePath = "custom/path/to/configs/"

// Override env config path (default: "src/test/resources/env-config")
EnvConfigHelper.envConfigBasePath = "custom/path/to/env-config"
```

### Custom Field Transformers

Register project-specific transformers:

```groovy
import au.com.tpgtelecom.apitest.util.FieldTransformer

// Register a single transformer
FieldTransformer.registerTransformer("removeSpaces") { String val, Object[] args ->
    val?.replaceAll("\\s", "")
}

// Register multiple transformers at once
FieldTransformer.registerTransformers([
    "maskPhone": { String val, Object[] args -> val ? "****${val[-4..-1]}" : null },
    "toBoolean": { String val, Object[] args -> val?.equalsIgnoreCase("yes") ? "true" : "false" }
])
```

### Built-in Transformers

| Name | Description | Args |
|------|-------------|------|
| `identity` | Returns value unchanged | - |
| `uppercase` | Converts to uppercase | - |
| `lowercase` | Converts to lowercase | - |
| `phoneFormat` | Strips non-digit characters | - |
| `dateFormat` | Appends `T00:00:00.000Z` to date string | - |
| `truncate` | Truncates to N characters | length |
| `addPrefix` | Prepends a prefix string | prefix |
| `staticValue` | Returns a constant value (ignores source) | value |
| `yToTrue` | Converts "Y" → "true", else "false" | - |

## Building

```bash
cd framework
./gradlew build
./gradlew publishToMavenLocal  # publish to ~/.m2 for local consumption
```

## Dependencies

| Library | Version | Purpose |
|---------|---------|---------|
| Groovy | 4.0.23 | Language |
| Spock | 2.3-groovy-4.0 | Test framework |
| REST Assured | 5.4.0 | HTTP client |
| WireMock | 3.13.1 | Service stubbing |
| Allure | 2.29.0 | Reporting |
| SnakeYAML | 2.0 | YAML parsing |
| SLF4J + Logback | 2.0.9 / 1.4.14 | Logging |
