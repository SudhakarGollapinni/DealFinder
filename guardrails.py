"""
Simple guardrails for DealFinder AI app
"""
import os
from openai import OpenAI
from typing import Dict, Tuple
import re


class SimpleGuardrails:
    """Easy-to-use guardrails using OpenAI Moderation API and basic validation"""
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key) if api_key else None
        
        # Configure limits
        self.max_input_length = 1000
        self.min_input_length = 3
        
        # Blocked patterns (customize as needed)
        self.blocked_patterns = [
            r"ignore (previous|all|your) instruction",
            r"you are now",
            r"roleplay as",
            r"pretend (you are|to be)",
            r"disregard.*rules",
            r"reveal.*system prompt",
            r"reveal.*prompt",
        ]
    
    def check_input(self, user_input: str) -> Tuple[bool, str]:
        """
        Check if user input is safe and valid
        
        Returns:
            (is_safe, message) - True if safe, False if blocked with reason
        """
        
        # 1. Basic validation
        if not user_input or not user_input.strip():
            return False, "Input cannot be empty"
        
        if len(user_input) < self.min_input_length:
            return False, f"Input too short (minimum {self.min_input_length} characters)"
        
        if len(user_input) > self.max_input_length:
            return False, f"Input too long (maximum {self.max_input_length} characters)"
        
        # 2. Check for prompt injection attempts
        user_input_lower = user_input.lower()
        for pattern in self.blocked_patterns:
            if re.search(pattern, user_input_lower, re.IGNORECASE):
                return False, "Input contains potentially unsafe instructions"
        
        # 3. OpenAI Moderation API check
        if self.client:
            try:
                moderation = self.client.moderations.create(input=user_input)
                result = moderation.results[0]
                
                if result.flagged:
                    # Get which categories were flagged
                    flagged_categories = [
                        cat for cat, flagged in result.categories.model_dump().items()
                        if flagged
                    ]
                    return False, f"Content flagged as inappropriate: {', '.join(flagged_categories)}"
                
            except Exception as e:
                print(f"Moderation API error: {e}")
                # Fail open (allow) if moderation API is down, but log it
                # Change to fail closed (block) if you prefer stricter safety
        else:
            print("Warning: OpenAI API key not set. Moderation checks disabled.")
        
        return True, "OK"
    
    def check_output(self, output: str) -> Tuple[bool, str]:
        """
        Check if AI output is safe before showing to user
        
        Returns:
            (is_safe, message) - True if safe, False if should be filtered
        """
        if not output or not output.strip():
            return False, "Empty output"
        
        # Check output with moderation API
        if self.client:
            try:
                moderation = self.client.moderations.create(input=output)
                result = moderation.results[0]
                
                if result.flagged:
                    flagged_categories = [
                        cat for cat, flagged in result.categories.model_dump().items()
                        if flagged
                    ]
                    return False, f"Output flagged: {', '.join(flagged_categories)}"
                
            except Exception as e:
                print(f"Output moderation error: {e}")
        
        return True, "OK"
    
    def sanitize_for_deals(self, user_input: str) -> str:
        """
        Sanitize and normalize input for deal finding
        
        - Removes excessive whitespace/newlines
        - Removes potentially dangerous characters
        - Normalizes common patterns
        - Removes URLs (to prevent scraping redirects)
        """
        # Basic cleanup
        sanitized = user_input.strip()
        
        # Remove multiple spaces/newlines/tabs - normalize to single space
        sanitized = re.sub(r'\s+', ' ', sanitized)
        
        # Remove URLs (people might paste product URLs which could be malicious)
        sanitized = re.sub(r'http[s]?://\S+', '', sanitized)
        
        # Remove HTML tags (in case someone tries to inject HTML)
        sanitized = re.sub(r'<[^>]+>', '', sanitized)
        
        # Remove common SQL-like patterns (defense in depth)
        sql_patterns = [
            r'(union|select|insert|update|delete|drop|create|alter)\s+(all|distinct|from|into|table)',
        ]
        for pattern in sql_patterns:
            sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
        
        # Remove excessive punctuation (!!!!!!, ????)
        sanitized = re.sub(r'([!?.]){3,}', r'\1\1', sanitized)
        
        # Remove special characters that might break search engines
        # Keep: letters, numbers, spaces, basic punctuation (.,!?-$%)
        sanitized = re.sub(r'[^\w\s.,!?\-$%]', '', sanitized)
        
        # Normalize common deal-related terms (optional - helps with consistency)
        # e.g., "cheapest" -> "cheap", "best prices" -> "best price"
        # You can add more normalization rules here as needed
        
        # Final cleanup
        sanitized = sanitized.strip()
        
        return sanitized


# Rate limiting helper
class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = {}  # {ip: [(timestamp, ...)]}
    
    def is_allowed(self, identifier: str) -> Tuple[bool, str]:
        """Check if request is allowed for this identifier (e.g., IP address)"""
        import time
        
        current_time = time.time()
        
        if identifier not in self.requests:
            self.requests[identifier] = []
        
        # Clean old requests
        self.requests[identifier] = [
            ts for ts in self.requests[identifier]
            if current_time - ts < self.window_seconds
        ]
        
        # Check limit
        if len(self.requests[identifier]) >= self.max_requests:
            return False, f"Rate limit exceeded. Max {self.max_requests} requests per {self.window_seconds} seconds"
        
        # Add current request
        self.requests[identifier].append(current_time)
        return True, "OK"

