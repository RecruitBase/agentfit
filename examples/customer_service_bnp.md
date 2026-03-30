# Profile: Customer Service Agent

## Metadata
- Organization: TechCorp Support
- Domain: customer_service
- Description: AI agent for handling customer support inquiries with API integrations
- Agent Name: SupportBot Pro
- Tags: support, customer-service, api-integration

## Agent Requirements
- Task Understanding: Can correctly interpret customer issues and context (required, priority: critical)
- Tool Use: Can call support APIs to retrieve tickets and customer data (required, priority: critical)
- Error Recovery: Can handle API errors gracefully and retry appropriately (required, priority: high)
- Step Completion: Can break down complex issues into logical steps (required, priority: high)
- Response Quality: Provides helpful and professional responses (required, priority: medium)

## Evaluation Setup
- Complexity: moderate
- Dimensions:
  - task_competence: 0.6
  - tool_use: 0.4

## Constraints
- Max Latency: 5000ms
- Max Errors per Task: 2

## Compliance
- GDPR compliant data handling
- PII redaction in logs
- Audit trail maintenance
