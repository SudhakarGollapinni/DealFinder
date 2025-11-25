#!/bin/bash
# Script to package and deploy Lambda function

set -e

echo "📦 Packaging Lambda function..."

# Create deployment package directory
mkdir -p lambda_package
cd lambda_package

# Copy Lambda function
cp ../lambda_function.py .

# Copy required modules
cp -r ../database.py .
cp -r ../extractors.py .
cp -r ../filters.py .
cp -r ../utils.py .
cp -r ../cost_tracker.py .
cp -r ../html_generator.py .

# Install dependencies
pip install -r ../lambda/requirements.txt -t .

# Create zip file
zip -r ../lambda_deployment.zip . -x "*.pyc" -x "__pycache__/*" -x "*.dist-info/*"

cd ..
echo "✅ Lambda package created: lambda_deployment.zip"
echo ""
echo "Next steps:"
echo "1. Upload lambda_deployment.zip to AWS Lambda"
echo "2. Set environment variables:"
echo "   - OPENAI_API_KEY"
echo "   - TAVILY_API_KEY"
echo "   - NOTIFICATIONS_TABLE_NAME"
echo "   - FROM_EMAIL (for SES)"
echo "   - AWS_REGION"
echo "3. Set timeout to 5 minutes (300 seconds)"
echo "4. Set memory to at least 512 MB"
echo "5. Create EventBridge rule to trigger on schedule"

