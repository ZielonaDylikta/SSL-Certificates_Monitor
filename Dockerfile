FROM python:3.12-slim
WORKDIR /app
RUN mkdir -p /app/data
COPY certcheck.py .
COPY template.html .
COPY sites.csv .
EXPOSE 7921
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7921/health')" || exit 1
CMD ["python", "certcheck.py"]
