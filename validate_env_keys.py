#!/usr/bin/env python3
"""
Validation script to check if API keys are properly configured for Playwright tests.
This script can be used to test the environment setup both locally and in CI.
"""

import os
import sys

def validate_api_keys():
    """Validate that at least one required API key is available."""
    print("🔍 Validating API key configuration for Playwright tests...")
    
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    
    print(f"   OPENAI_API_KEY: {'✓ SET' if openai_key else '✗ NOT SET'}")
    print(f"   ANTHROPIC_API_KEY: {'✓ SET' if anthropic_key else '✗ NOT SET'}")
    
    if not openai_key and not anthropic_key:
        print("❌ VALIDATION FAILED:")
        print("   Neither OPENAI_API_KEY nor ANTHROPIC_API_KEY is set.")
        print("   At least one API key is required for Playwright tests to run.")
        print("   In GitHub Actions, these should reference repository secrets:")
        print("   - OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}")
        print("   - ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}")
        return False
    
    print("✅ VALIDATION PASSED:")
    print("   At least one API key is available for Playwright tests.")
    
    # Additional check: validate the keys are not empty
    if openai_key and not openai_key.strip():
        print("⚠️  WARNING: OPENAI_API_KEY is set but appears to be empty.")
    if anthropic_key and not anthropic_key.strip():
        print("⚠️  WARNING: ANTHROPIC_API_KEY is set but appears to be empty.")
    
    return True

def main():
    """Main entry point."""
    success = validate_api_keys()
    
    if not success:
        print("\n💡 To fix this issue:")
        print("   1. Ensure repository secrets are configured in GitHub")
        print("   2. Verify the workflow references these secrets in the env section")
        print("   3. For local testing, set at least one API key in your environment")
        
        sys.exit(1)
    
    print("\n🎉 Environment is properly configured for Playwright tests!")
    return 0

if __name__ == "__main__":
    sys.exit(main())