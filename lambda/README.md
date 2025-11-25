# Lambda Function for Price Checking

## Overview
This Lambda function runs on a schedule (via EventBridge) to check prices for all tracked products and send notifications when prices drop.

## Deployment Steps

### 1. Install Dependencies Locally
```bash
cd lambda
pip install -r requirements.txt -t ../lambda_package
```

### 2. Package Lambda Function
```bash
chmod +x deploy.sh
./deploy.sh
```

This creates `lambda_deployment.zip` in the project root.

### 3. Create Lambda Function in AWS

**Via AWS Console:**
1. Go to Lambda → Functions → Create function
2. Choose "Author from scratch"
3. Function name: `check-product-prices`
4. Runtime: Python 3.11
5. Architecture: x86_64
6. Click "Create function"

**Upload code:**
1. Go to Code tab
2. Click "Upload from" → ".zip file"
3. Upload `lambda_deployment.zip`

### 4. Configure Lambda

**Basic Settings:**
- Timeout: 5 minutes (300 seconds)
- Memory: 512 MB (or more if needed)

**Environment Variables:**
```
OPENAI_API_KEY=your-key
TAVILY_API_KEY=your-key
NOTIFICATIONS_TABLE_NAME=deal-finder-notifications
FROM_EMAIL=noreply@yourdomain.com
AWS_REGION=us-east-1
```

**IAM Role Permissions:**
The Lambda execution role needs:
- DynamoDB: Query, Scan, UpdateItem on notifications table
- SES: SendEmail (if using email)
- SNS: Publish (if using SMS)

### 5. Create EventBridge Rule

**Via AWS Console:**
1. Go to EventBridge → Rules → Create rule
2. Name: `check-product-prices-schedule`
3. Rule type: Schedule
4. Schedule pattern: `rate(6 hours)`
5. Target: Lambda function → `check-product-prices`
6. Create rule

**Via AWS CLI:**
```bash
# Create rule
aws events put-rule \
    --name check-product-prices-schedule \
    --schedule-expression "rate(6 hours)" \
    --state ENABLED

# Allow EventBridge to invoke Lambda
aws lambda add-permission \
    --function-name check-product-prices \
    --statement-id allow-eventbridge \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn arn:aws:events:REGION:ACCOUNT_ID:rule/check-product-prices-schedule

# Add Lambda as target
aws events put-targets \
    --rule check-product-prices-schedule \
    --targets "Id=1,Arn=arn:aws:lambda:REGION:ACCOUNT_ID:function:check-product-prices"
```

## Testing

### Test Locally
```python
# test_lambda_local.py
import json
import asyncio
from lambda_function import lambda_handler

event = {}
context = {}

result = lambda_handler(event, context)
print(json.dumps(result, indent=2))
```

### Test in AWS
```bash
# Invoke manually
aws lambda invoke \
    --function-name check-product-prices \
    --payload '{}' \
    response.json

# View logs
aws logs tail /aws/lambda/check-product-prices --follow
```

## Monitoring

### CloudWatch Metrics
- Invocations
- Duration
- Errors
- Throttles

### CloudWatch Logs
- Function logs: `/aws/lambda/check-product-prices`
- Check for errors, price drops detected, notifications sent

## Cost Optimization

- Use appropriate timeout (don't set too high)
- Start with 512 MB memory, adjust based on performance
- Consider checking prices less frequently (12 hours instead of 6)
- Use DynamoDB on-demand billing (pay per request)

## Troubleshooting

**Timeout errors:**
- Increase timeout to 5 minutes
- Increase memory allocation
- Check if Tavily/OpenAI APIs are slow

**Permission errors:**
- Verify IAM role has DynamoDB permissions
- Check SES/SNS permissions if using notifications

**Price extraction failing:**
- Verify API keys are set correctly
- Check CloudWatch logs for specific errors
- Ensure Lambda has internet access (not in private VPC)

