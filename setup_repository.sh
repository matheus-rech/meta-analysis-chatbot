#!/bin/bash

# Setup script for Meta-Analysis Chatbot repository

echo "🚀 Setting up Meta-Analysis Chatbot repository..."

# Initialize git if not already initialized
if [ ! -d .git ]; then
    echo "Initializing git repository..."
    git init
fi

# Add all files
echo "Adding files to git..."
git add .

# Make initial commit
echo "Creating initial commit..."
git commit -m "Initial commit: Meta-Analysis AI Chatbot

- Natural language interface for meta-analysis using LLMs
- R statistical backend with meta and metafor packages  
- Multiple implementations (LangChain, basic, native Gradio)
- Docker support for Hugging Face Spaces deployment
- Complete MCP tool integration"

echo ""
echo "✅ Repository initialized successfully!"
echo ""
echo "Next steps:"
echo "1. Create a new repository on GitHub: https://github.com/new"
echo "2. Name it: meta-analysis-chatbot"
echo "3. Run these commands:"
echo ""
echo "   git remote add origin https://github.com/YOUR_USERNAME/meta-analysis-chatbot.git"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "For Hugging Face Spaces deployment:"
echo "1. Create a new Space at: https://huggingface.co/spaces"
echo "2. Choose 'Docker' as the SDK"
echo "3. Connect your GitHub repository"
echo "4. Add OPENAI_API_KEY or ANTHROPIC_API_KEY as a secret"
echo "5. Deploy!"