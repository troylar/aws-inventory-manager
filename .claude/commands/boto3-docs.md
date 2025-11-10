# Boto3 Documentation Helper

Quick reference for AWS boto3 SDK methods.

## Task

Fetch and display boto3 documentation for AWS services to help with development.

## Steps

### 1. Ask User for Service

Ask the user which AWS service they want to look up:
- Common examples: ec2, s3, lambda, iam, rds, dynamodb, sns, sqs
- Full list available at: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/

### 2. Fetch Documentation

Use WebFetch to get documentation from boto3 docs:

```
URL: https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/<service>.html
```

### 3. Extract Relevant Information

Parse the documentation page and extract:

1. **Service Overview**
   - Service description
   - Client creation syntax

2. **Common Methods** (focus on these categories):
   - **List/Describe methods**: `list_*`, `describe_*` (for discovery)
   - **Create methods**: `create_*` (for resource creation)
   - **Delete methods**: `delete_*` (for cleanup)
   - **Update methods**: `update_*`, `modify_*` (for changes)
   - **Tag methods**: `tag_*`, `untag_*` (for tagging)

3. **Paginators**
   - Which methods support pagination
   - How to use paginators

4. **Common Patterns**
   - Tag format (Tags vs TagList)
   - ARN patterns
   - Response structure

### 4. Display Formatted Summary

Present information in a clear, developer-friendly format:

```
📚 Boto3 Documentation: <ServiceName>

════════════════════════════════════════════════════════════

🔧 Client Setup
───────────────────────────────────────────────────────────
import boto3

# Create client
client = boto3.client('<service>', region_name='us-east-1')

# Or with session
session = boto3.Session(profile_name='myprofile')
client = session.client('<service>', region_name='us-east-1')

📋 Common Methods
───────────────────────────────────────────────────────────

List/Describe Operations:
  • describe_<resources>() - List existing resources
  • list_<resources>() - Get resource identifiers
  • get_<resource>() - Get detailed resource info

Create Operations:
  • create_<resource>() - Create new resource

Update Operations:
  • update_<resource>() - Modify existing resource
  • modify_<resource>() - Alternative update syntax

Delete Operations:
  • delete_<resource>() - Remove resource

Tagging Operations:
  • tag_resource() - Add tags to resource
  • untag_resource() - Remove tags from resource
  • list_tags_for_resource() - Get resource tags

📄 Paginators
───────────────────────────────────────────────────────────
Available paginators for this service:
  • describe_<resources> - Paginate through resource lists
  • list_<resources> - Paginate through identifiers

Usage:
paginator = client.get_paginator('describe_<resources>')
for page in paginator.paginate():
    for item in page['<ResponseKey>']:
        print(item)

💡 Common Patterns
───────────────────────────────────────────────────────────

Tag Format:
  Tags = [
      {'Key': 'Environment', 'Value': 'prod'},
      {'Key': 'Team', 'Value': 'platform'}
  ]

ARN Pattern:
  arn:aws:<service>:<region>:<account-id>:<resource-type>/<resource-id>

Response Structure:
  {
      '<ResponseKey>': [...],  # List of resources
      'NextToken': '...'       # For pagination
  }

📖 Example: Describe Resources
───────────────────────────────────────────────────────────
import boto3

client = boto3.client('<service>', region_name='us-east-1')

# Using paginator (recommended)
paginator = client.get_paginator('describe_<resources>')
for page in paginator.paginate():
    for resource in page.get('<ResponseKey>', []):
        print(f"Resource: {resource['<NameKey>']}")
        print(f"ARN: {resource['<ArnKey>']}")
        print(f"Tags: {resource.get('Tags', [])}")

# Direct call (limited results)
response = client.describe_<resources>()
resources = response.get('<ResponseKey>', [])

📖 Example: Create Resource
───────────────────────────────────────────────────────────
response = client.create_<resource>(
    Name='my-resource',
    Tags=[
        {'Key': 'Environment', 'Value': 'prod'},
    ]
)
resource_arn = response['<ArnKey>']

🔗 Full Documentation
───────────────────────────────────────────────────────────
https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/<service>.html

💡 Quick Tips for Resource Collectors
───────────────────────────────────────────────────────────
1. Always use paginators for complete resource discovery
2. Handle ServiceNotEnabledException gracefully
3. Extract ARN, tags, and creation date
4. Compute config hash for change detection
5. Add proper error handling and logging
```

### 5. Service-Specific Examples

For commonly used services, provide additional context:

**EC2:**
- Covers: Instances, Volumes, VPCs, Security Groups, Subnets
- Multiple paginators available
- Complex tag handling

**S3:**
- Global service but buckets have regions
- list_buckets() is not paginated (returns all)
- get_bucket_location() needed for regional info

**Lambda:**
- list_functions() uses pagination
- get_function() for details
- Tags via list_tags() separate call

**IAM:**
- Global service (region='us-east-1')
- Multiple resource types (roles, users, policies)
- Pagination required for all list operations

### 6. Integration with Collector Generator

If user is creating a new collector, suggest:

```
💡 Ready to Create a Collector?

Use the /new-collector command to scaffold a collector for this service!

Example:
  /new-collector

Then provide:
  Service: <ServiceName>
  Client: <service>
  Method: describe_<resources>
```

## Example Usage

**Basic:**
```
/boto3-docs

User: ec2
```

**Response shows EC2 documentation with common methods, paginators, examples**

**Advanced:**
```
/boto3-docs

User: efs

Shows EFS documentation
Explains describe_file_systems()
Shows tag format
Provides collector example
```

## Use Cases

1. **Creating new collectors** - Quick reference for API methods
2. **Debugging collectors** - Verify method names and response structure
3. **Understanding pagination** - Check which methods support paginators
4. **Tag handling** - See tag format for specific service
5. **ARN construction** - Understand ARN patterns

## Notes

- Focus on methods relevant to resource collection
- Highlight pagination support (critical for completeness)
- Show actual code examples (copy-pasteable)
- Link to full docs for deep dive
- Tailor examples to collector pattern used in this project

## Quick Service Reference

Common services and their key methods:

| Service | Client | List Method | Paginator? |
|---------|--------|-------------|------------|
| EC2 | ec2 | describe_instances | ✓ |
| S3 | s3 | list_buckets | ✗ |
| Lambda | lambda | list_functions | ✓ |
| RDS | rds | describe_db_instances | ✓ |
| DynamoDB | dynamodb | list_tables | ✓ |
| IAM | iam | list_roles | ✓ |
| SNS | sns | list_topics | ✓ |
| SQS | sqs | list_queues | ✗ |
| ECS | ecs | list_clusters | ✓ |
| EKS | eks | list_clusters | ✓ |

## Error Handling

If service docs not found:
- Verify service name is correct
- Suggest using AWS CLI docs as alternative
- Provide link to full boto3 service list

## Alternative Sources

If WebFetch fails:
- Use boto3 help() in Python interactive session
- AWS CLI documentation
- Check local boto3 installation docs
