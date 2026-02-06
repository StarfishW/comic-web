FROM python:3.11-slim

WORKDIR /app

# Copy and install jmcomic package first
COPY jmcomic /app/jmcomic
RUN cd /app/jmcomic && pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple

# Install backend dependencies
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# Copy backend code
COPY backend /app/backend
WORKDIR /app/backend

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
