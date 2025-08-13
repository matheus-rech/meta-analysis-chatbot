# Meta-Analysis Chatbot Docker Image
FROM python:3.11

WORKDIR /app
COPY . /app

# Set environment variable to allow rpy2 to install without R present during build
ENV RPY2_CFFI_MODE=ABI

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-chatbot.txt

# Run the main application
CMD ["python", "chatbot_langchain.py"]