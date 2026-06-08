FROM python:3.11-slim
WORKDIR /app
COPY ../requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir streamlit langchain langchain-openai langchain-community \
    openai python-dotenv sqlalchemy psycopg2-binary pandas
COPY . /app
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
