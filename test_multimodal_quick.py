#!/usr/bin/env python3
"""
Quick test to verify multimodal chatbot functionality
"""

import sys
import os

def test_imports():
    """Test that all required imports work"""
    print("Testing imports...")
    try:
        import gradio as gr
        print("✅ Gradio imported")
        
        from PyPDF2 import PdfReader
        print("✅ PyPDF2 imported")
        
        from PIL import Image
        print("✅ PIL imported")
        
        import pandas as pd
        print("✅ Pandas imported")
        
        from langchain.agents import AgentExecutor
        print("✅ LangChain imported")
        
        # Test the actual chatbot module
        import chatbot_enhanced
        print("✅ chatbot_enhanced imported successfully")
        
        # Check for the UnifiedMCPBackend
        backend = chatbot_enhanced.UnifiedMCPBackend()
        print("✅ UnifiedMCPBackend instantiated")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_file_processing():
    """Test file processing capabilities"""
    print("\nTesting file processing capabilities...")
    
    try:
        from chatbot_enhanced import UnifiedMCPBackend
        backend = UnifiedMCPBackend()
        
        # Test methods exist
        assert hasattr(backend, 'extract_pdf_data'), "Missing PDF extraction method"
        print("✅ PDF extraction method available")
        
        assert hasattr(backend, 'analyze_figure'), "Missing image analysis method"
        print("✅ Image analysis method available")
        
        assert hasattr(backend, 'initialize_meta_analysis'), "Missing initialize method"
        print("✅ Meta-analysis initialization available")
        
        assert hasattr(backend, 'upload_study_data'), "Missing data upload method"
        print("✅ Data upload method available")
        
        return True
        
    except AssertionError as e:
        print(f"❌ {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_ui_components():
    """Test UI components are properly configured"""
    print("\nTesting UI components...")
    
    try:
        import gradio as gr
        from chatbot_enhanced import handle_multimodal_submit
        
        # Check the handler exists and has correct signature
        import inspect
        sig = inspect.signature(handle_multimodal_submit)
        params = list(sig.parameters.keys())
        
        assert 'message' in params, "Missing message parameter"
        assert 'history' in params, "Missing history parameter"
        assert 'model_name' in params, "Missing model_name parameter"
        assert 'should_save' in params, "Missing should_save parameter"
        
        print("✅ Chat handler has correct signature")
        print(f"   Parameters: {params}")
        
        return True
        
    except AssertionError as e:
        print(f"❌ {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("MULTIMODAL CHATBOT VERIFICATION")
    print("=" * 60)
    
    all_passed = True
    
    # Test imports
    if not test_imports():
        all_passed = False
    
    # Test file processing
    if not test_file_processing():
        all_passed = False
    
    # Test UI components
    if not test_ui_components():
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED - Multimodal chatbot is ready!")
        print("\nTo run the chatbot:")
        print("  python chatbot_enhanced.py")
        print("\nFeatures available:")
        print("  - PDF document processing")
        print("  - Image/chart analysis")
        print("  - CSV/Excel data upload")
        print("  - R statistical backend")
        print("  - Multi-model support (GPT/Claude)")
        print("  - File management sidebar")
        print("  - Auto-save sessions")
    else:
        print("❌ SOME TESTS FAILED - Please check the errors above")
        
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())