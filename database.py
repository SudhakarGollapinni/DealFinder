"""
Database module for storing product price drop notifications.
Uses DynamoDB for serverless, scalable storage.
"""
import os
import boto3
from datetime import datetime
from typing import List, Dict, Optional
from botocore.exceptions import ClientError

# DynamoDB configuration
TABLE_NAME = os.getenv("NOTIFICATIONS_TABLE_NAME", "deal-finder-notifications")
REGION = os.getenv("AWS_REGION", "us-east-1")

# Initialize DynamoDB client
# Use local fallback if AWS credentials not available
try:
    dynamodb = boto3.resource("dynamodb", region_name=REGION)
    _dynamodb_available = True
except Exception as e:
    print(f"⚠️ DynamoDB not available (this is OK for local dev): {e}")
    dynamodb = None
    _dynamodb_available = False

table = None


def get_table():
    """Get or create DynamoDB table."""
    global table
    if not _dynamodb_available:
        raise RuntimeError("DynamoDB not available. Set AWS credentials for production use.")
    if table is None:
        table = dynamodb.Table(TABLE_NAME)
    return table


def init_database():
    """Initialize the database and create table if it doesn't exist."""
    if not _dynamodb_available:
        print("⚠️ DynamoDB not available. Notifications feature will not work.")
        print("   Set AWS credentials and region to enable notifications.")
        return
    
    try:
        # Check if table exists
        table = get_table()
        table.load()  # This will raise exception if table doesn't exist
        print(f"✅ DynamoDB table '{TABLE_NAME}' already exists")
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "ResourceNotFoundException":
            print(f"⚠️ Table '{TABLE_NAME}' not found. Creating...")
            try:
                create_table()
            except Exception as create_error:
                print(f"❌ Failed to create table: {create_error}")
                print("   Notifications feature will not work until table is created.")
        else:
            print(f"⚠️ Error checking table: {e}")
            print("   Notifications feature may not work properly.")
    except Exception as e:
        print(f"⚠️ Error initializing DynamoDB: {e}")
        print("   Notifications feature will not work.")


def create_table():
    """Create the DynamoDB table."""
    try:
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[
                {
                    "AttributeName": "product_name",
                    "KeyType": "HASH"  # Partition key
                },
                {
                    "AttributeName": "subscription_id",
                    "KeyType": "RANGE"  # Sort key
                }
            ],
            AttributeDefinitions=[
                {
                    "AttributeName": "product_name",
                    "AttributeType": "S"  # String
                },
                {
                    "AttributeName": "subscription_id",
                    "AttributeType": "S"  # String (email or phone)
                }
            ],
            BillingMode="PAY_PER_REQUEST"  # On-demand pricing
        )
        table.wait_until_exists()
        print(f"✅ DynamoDB table '{TABLE_NAME}' created successfully")
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            print(f"✅ Table '{TABLE_NAME}' already exists")
        else:
            raise


def add_notification(product_name: str, email: Optional[str] = None, phone: Optional[str] = None) -> bool:
    """
    Add a notification subscription for a product.
    
    Args:
        product_name: Name of the product to track
        email: Email address (optional)
        phone: Phone number (optional)
    
    Returns:
        True if added successfully, False if already exists
    """
    if not email and not phone:
        raise ValueError("At least one of email or phone must be provided")
    
    if not _dynamodb_available:
        raise RuntimeError("DynamoDB not available. Cannot add notification.")
    
    try:
        table = get_table()
        
        # Create subscription ID from email or phone
        subscription_id = email if email else phone
        
        # Check if subscription already exists
        try:
            response = table.get_item(
                Key={
                    "product_name": product_name,
                    "subscription_id": subscription_id
                }
            )
            if "Item" in response:
                return False  # Already exists
        except ClientError:
            pass
        
        # Add new subscription
        item = {
            "product_name": product_name,
            "subscription_id": subscription_id,
            "email": email,
            "phone": phone,
            "created_at": datetime.utcnow().isoformat(),
            "last_price": None,  # Will be updated when we check prices
            "last_checked": None
        }
        
        table.put_item(Item=item)
        return True
        
    except ClientError as e:
        print(f"Error adding notification: {e}")
        raise


def get_notifications_for_product(product_name: str) -> List[Dict]:
    """
    Get all notification subscriptions for a product.
    
    Args:
        product_name: Name of the product
    
    Returns:
        List of notification records
    """
    try:
        table = get_table()
        response = table.query(
            KeyConditionExpression="product_name = :pn",
            ExpressionAttributeValues={":pn": product_name}
        )
        return response.get("Items", [])
    except ClientError as e:
        print(f"Error getting notifications: {e}")
        return []


def get_all_notifications() -> List[Dict]:
    """
    Get all notification subscriptions.
    
    Returns:
        List of all notification records
    """
    try:
        table = get_table()
        response = table.scan()
        return response.get("Items", [])
    except ClientError as e:
        print(f"Error getting all notifications: {e}")
        return []


def delete_notification(product_name: str, subscription_id: str) -> bool:
    """
    Delete a notification by product name and subscription ID.
    
    Args:
        product_name: Name of the product
        subscription_id: Email or phone of the subscription
    
    Returns:
        True if deleted, False if not found
    """
    try:
        table = get_table()
        table.delete_item(
            Key={
                "product_name": product_name,
                "subscription_id": subscription_id
            }
        )
        return True
    except ClientError as e:
        print(f"Error deleting notification: {e}")
        return False


def get_products_with_notifications() -> List[str]:
    """
    Get list of all unique product names that have notifications.
    
    Returns:
        List of product names
    """
    try:
        table = get_table()
        response = table.scan(
            ProjectionExpression="product_name"
        )
        # Extract unique product names
        products = set()
        for item in response.get("Items", []):
            products.add(item["product_name"])
        return list(products)
    except ClientError as e:
        print(f"Error getting products: {e}")
        return []


def update_product_price(product_name: str, subscription_id: str, price: float, current_time: str = None):
    """
    Update the last known price for a product subscription.
    
    Args:
        product_name: Name of the product
        subscription_id: Email or phone of the subscription
        price: Current price
        current_time: ISO format timestamp (defaults to now)
    """
    if current_time is None:
        current_time = datetime.utcnow().isoformat()
    
    try:
        table = get_table()
        table.update_item(
            Key={
                "product_name": product_name,
                "subscription_id": subscription_id
            },
            UpdateExpression="SET last_price = :price, last_checked = :time",
            ExpressionAttributeValues={
                ":price": price,
                ":time": current_time
            }
        )
    except ClientError as e:
        print(f"Error updating price: {e}")
        raise
