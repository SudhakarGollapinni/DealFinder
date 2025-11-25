"""
AWS Lambda function to check prices for tracked products and send notifications.
Triggered by EventBridge on a schedule (e.g., every 6 hours).
"""
import os
import json
import boto3
from typing import Dict, List
from datetime import datetime

# Import your existing modules
# Note: You'll need to package these with the Lambda deployment
from database import (
    get_products_with_notifications,
    get_notifications_for_product,
    update_product_price
)
from extractors import parse_products_with_extract
from utils import extract_price_value

# Initialize clients
ses_client = boto3.client("ses", region_name=os.getenv("AWS_REGION", "us-east-1"))
sns_client = boto3.client("sns", region_name=os.getenv("AWS_REGION", "us-east-1"))

# Configuration
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@yourdomain.com")
SNS_TOPIC_ARN = os.getenv("SNS_TOPIC_ARN", None)  # Optional: SNS topic for SMS


def lambda_handler(event, context):
    """
    Main Lambda handler function.
    Checks prices for all tracked products and sends notifications.
    """
    print(f"Starting price check at {datetime.utcnow().isoformat()}")
    
    try:
        # Get all products with active notifications
        products = get_products_with_notifications()
        print(f"Found {len(products)} products to check")
        
        if not products:
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "No products to check"})
            }
        
        # Initialize agent for price checking (reuse your existing setup)
        from strands import Agent
        from strands.models.openai import OpenAIModel
        from strands_tools.tavily import tavily_search, tavily_extract
        
        model = OpenAIModel(
            client_args={"api_key": os.getenv("OPENAI_API_KEY")},
            model_id="gpt-4o-mini",
            params={"max_tokens": 1000, "temperature": 0.7}
        )
        agent = Agent(
            model=model,
            tools=[tavily_search, tavily_extract],
            system_prompt="You are a price checker for products."
        )
        
        notifications_sent = 0
        errors = []
        
        for product_name in products:
            try:
                print(f"Checking price for: {product_name}")
                
                # Search for current price
                search_result = agent.tool.tavily_search(
                    query=f"{product_name} price",
                    search_depth="basic",
                    max_results=3,
                    include_raw_content=True
                )
                
                # Extract products from search results
                # (Reuse your existing extraction logic)
                # Note: Lambda handler can't be async, so we'll use sync version
                import asyncio
                products_found = asyncio.run(extract_current_price(search_result, product_name, agent))
                
                if not products_found:
                    print(f"⚠️ Could not find price for {product_name}")
                    continue
                
                # Get the best match (lowest price)
                best_match = products_found[0]
                current_price_str = best_match.get("price", "")
                current_price = extract_price_value(current_price_str)
                
                if current_price == float('inf'):
                    print(f"⚠️ Invalid price for {product_name}: {current_price_str}")
                    continue
                
                # Get all subscribers for this product
                subscribers = get_notifications_for_product(product_name)
                print(f"Found {len(subscribers)} subscribers for {product_name}")
                
                for subscriber in subscribers:
                    last_price = subscriber.get("last_price")
                    
                    # Update the price in database
                    update_product_price(
                        product_name,
                        subscriber["subscription_id"],
                        current_price
                    )
                    
                    # Check if price dropped
                    if last_price is not None and current_price < last_price:
                        price_drop = last_price - current_price
                        price_drop_percent = (price_drop / last_price) * 100
                        
                        print(f"💰 Price drop detected for {product_name}: ${last_price} → ${current_price} (${price_drop:.2f} off, {price_drop_percent:.1f}%)")
                        
                        # Send notification
                        sent = send_notification(
                            subscriber,
                            product_name,
                            last_price,
                            current_price,
                            price_drop,
                            price_drop_percent,
                            best_match.get("url", "")
                        )
                        
                        if sent:
                            notifications_sent += 1
                    elif last_price is None:
                        # First time checking, just update the price
                        print(f"📝 First price check for {product_name}: ${current_price}")
                    else:
                        print(f"📊 No price change for {product_name}: ${current_price}")
                
            except Exception as e:
                error_msg = f"Error checking {product_name}: {str(e)}"
                print(f"❌ {error_msg}")
                errors.append(error_msg)
                continue
        
        result = {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Price check completed",
                "products_checked": len(products),
                "notifications_sent": notifications_sent,
                "errors": errors
            })
        }
        
        print(f"✅ Price check completed. Sent {notifications_sent} notifications")
        return result
        
    except Exception as e:
        print(f"❌ Fatal error in price check: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


def extract_current_price(search_result, product_name: str, agent) -> List[Dict]:
    """
    Extract current price from search results.
    Simplified version of your existing extraction logic.
    """
    try:
        # Parse search results
        text_block = search_result["content"][0]["text"]
        import ast
        inner_data = ast.literal_eval(text_block)
        results = inner_data.get("results", [])
        
        if not results:
            return []
        
        # Use your existing extraction logic
        from extractors import parse_products_with_extract
        from cost_tracker import create_cost_tracker
        import asyncio
        
        cost_tracker = create_cost_tracker()
        products = asyncio.run(parse_products_with_extract(
            results[:3],  # Check top 3 results
            product_name,
            agent,
            cost_tracker
        ))
        
        return products
    except Exception as e:
        print(f"Error extracting price: {e}")
        return []


def send_notification(
    subscriber: Dict,
    product_name: str,
    old_price: float,
    new_price: float,
    price_drop: float,
    price_drop_percent: float,
    product_url: str
) -> bool:
    """
    Send notification via email or SMS.
    
    Returns:
        True if sent successfully, False otherwise
    """
    email = subscriber.get("email")
    phone = subscriber.get("phone")
    
    message = f"""
🎉 Price Drop Alert!

{product_name}

Price dropped from ${old_price:.2f} to ${new_price:.2f}
You save ${price_drop:.2f} ({price_drop_percent:.1f}% off!)

View deal: {product_url}

Happy shopping! 🛍️
    """.strip()
    
    success = False
    
    # Send email if provided
    if email:
        try:
            ses_client.send_email(
                Source=FROM_EMAIL,
                Destination={"ToAddresses": [email]},
                Message={
                    "Subject": {"Data": f"💰 Price Drop: {product_name}"},
                    "Body": {"Text": {"Data": message}}
                }
            )
            print(f"✅ Email sent to {email}")
            success = True
        except Exception as e:
            print(f"❌ Failed to send email to {email}: {e}")
    
    # Send SMS if provided (via SNS)
    if phone and SNS_TOPIC_ARN:
        try:
            # For SMS via SNS, you'd typically use SNS topic or direct SMS
            # This is a simplified version
            sns_client.publish(
                PhoneNumber=phone,
                Message=message
            )
            print(f"✅ SMS sent to {phone}")
            success = True
        except Exception as e:
            print(f"❌ Failed to send SMS to {phone}: {e}")
    
    return success

