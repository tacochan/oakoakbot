FROM python:3.9

# You'll want to make sure docker reuses cache for building these
COPY build-requirements.txt /
RUN pip install --upgrade pip && \
    pip install -r build-requirements.txt && \
    rm /build-requirements.txt

COPY data /app/data

COPY requirements.txt /
RUN pip install --extra-index-url https://www.piwheels.org/simple -r /requirements.txt && \
    rm /requirements.txt

COPY oakoakbot /app/oakoakbot
COPY oakoakbot.py /app
WORKDIR /app

CMD ["python", "-u", "oakoakbot.py"]

