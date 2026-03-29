FROM python:3.11-slim

WORKDIR /project

COPY parser/requirements.txt parser/requirements.txt
RUN pip install --no-cache-dir -r parser/requirements.txt

COPY parser/ parser/

ENV PYTHONPATH=/project

CMD ["python", "parser/main.py"]
