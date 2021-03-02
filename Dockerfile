FROM python:3.9

# TODO Pull data from somewhere
COPY data /app/data

COPY requirements.txt /
RUN pip install --upgrade pip && \
    pip install -r /requirements.txt && \
    rm /requirements.txt

COPY oakoakbot /app/oakoakbot
COPY oakoakbot.py /app
WORKDIR /app


CMD ["python", "-u", "oakoakbot.py"]

