# Meta-Analysis Chatbot Docker Image
FROM python:3.11

WORKDIR /app
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-chatbot.txt

# Run the main application
CMD ["python", "chatbot_langchain.py"]