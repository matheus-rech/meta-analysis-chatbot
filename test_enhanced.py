#!/usr/bin/env python3
"""
Test script for the enhanced meta-analysis chatbot
"""

import sys
import os

# Check for required packages
required_packages = {
    'gradio': 'gradio',
    'pytz': 'pytz', 
    'PIL': 'pillow',
    'PyPDF2': 'PyPDF2',
    'cv2': 'opencv-python-headless',
    'langchain': 'langchain',
    'pydantic': 'pydantic'
}

print("🔍 Checking required packages...")
missing_packages = []

for module_name, package_name in required_packages.items():
    try:
        if module_name == 'PIL':
            from PIL import Image
        elif module_name == 'cv2':
            import cv2
        else:
            __import__(module_name)
        print(f"✅ {module_name} is installed")
    except ImportError:
        print(f"❌ {module_name} is missing")
        missing_packages.append(package_name)

if missing_packages:
    print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
    print(f"Install with: pip install {' '.join(missing_packages)}")
    sys.exit(1)

print("\n✅ All required packages are installed!")

# Test basic imports from the enhanced chatbot
print("\n🔍 Testing enhanced chatbot imports...")
try:
    # Add the directory to path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    # Try importing key components
    from chatbot_enhanced import (
        EnhancedMCPToolWrapper,
        InitializeMetaAnalysisInput,
        generate_filename,
        SYSTEM_PROMPT
    )
    
    print("✅ Enhanced chatbot modules imported successfully")
    
    # Test basic functionality
    print("\n🔍 Testing basic functionality...")
    
    # Test filename generation
    test_filename = generate_filename("test analysis", "md")
    print(f"✅ Generated filename: {test_filename}")
    
    # Test Pydantic model
    test_input = InitializeMetaAnalysisInput(
        name="Test Study",
        study_type="clinical_trial",
        effect_measure="OR",
        analysis_model="random"
    )
    print(f"✅ Pydantic model created: {test_input.name}")
    
    # Test tool wrapper initialization
    wrapper = EnhancedMCPToolWrapper()
    print("✅ Tool wrapper initialized")
    
    print("\n🎉 All tests passed! The enhanced chatbot is ready to use.")
    print("\nTo run the enhanced chatbot:")
    print("  python chatbot_enhanced.py")
    
except Exception as e:
    print(f"\n❌ Error testing enhanced chatbot: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)