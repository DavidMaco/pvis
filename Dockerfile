FROM python:3.11-slim
WORKDIR /app
COPY pinned-requirements.txt ./
RUN pip install --no-cache-dir -r pinned-requirements.txt
COPY . /app
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
EXPOSE 5000
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--workers", "2"]
