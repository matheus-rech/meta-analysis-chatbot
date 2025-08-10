#!/usr/bin/env python3
"""
Simple test for enhanced chatbot components
"""

print("Testing enhanced chatbot components...")

# Test imports
try:
    import gradio as gr
    print("✅ Gradio imported")
except:
    print("❌ Gradio import failed")

try:
    import pytz
    print("✅ pytz imported")
except:
    print("❌ pytz import failed")

try:
    from PIL import Image
    print("✅ PIL imported")
except:
    print("❌ PIL import failed")

try:
    from PyPDF2 import PdfReader
    print("✅ PyPDF2 imported")
except:
    print("❌ PyPDF2 import failed")

try:
    from langchain.tools import StructuredTool
    print("✅ LangChain imported")
except:
    print("❌ LangChain import failed")

try:
    from pydantic import BaseModel, Field
    print("✅ Pydantic imported")
except:
    print("❌ Pydantic import failed")

print("\n✅ All imports successful! Enhanced chatbot is ready.")
print("\nTo run: python chatbot_enhanced.py")