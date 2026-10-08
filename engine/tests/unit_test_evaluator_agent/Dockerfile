FROM python:3.12-alpine

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY __init__.py ./
COPY evaluator_agent_9000.py ./

EXPOSE 9000

CMD [ "python", "./evaluator_agent_9000.py", "--host=127.0.0.1" ]
