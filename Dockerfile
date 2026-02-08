FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY carma_scraper.py .
COPY home_assistant_api.py .
COPY query_power_data.py .

# Create volume mount point for database
VOLUME ["/app/data"]

# Expose API port
EXPOSE 5000

# Run the API server
CMD ["python", "home_assistant_api.py"]