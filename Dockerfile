FROM python:3.12-slim
WORKDIR /app
COPY server.py test_performance.py test_race_condition.py test_rate_limiting.py ./
RUN pip install requests
ENV PORT=8080
EXPOSE 8080
CMD ["python", "server.py", "www"]
