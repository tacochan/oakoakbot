FROM python:3.9

# You'll want to make sure docker reuses cache for building these
COPY build-requirements.txt /
RUN pip install --upgrade pip && \
    pip install -r build-requirements.txt && \
    rm /build-requirements.txt

# Fetch images from Google Drive
RUN pip install gdown && \
    gdown https://drive.google.com/uc?id=18WGxDw-ZYmT-0rcxtTm33_kXJMzvJtV- && \
    mkdir /app && \
    unzip -q images.zip -d /app/data && \
    rm images.zip

# Install quick-to-install python requirements
COPY requirements.txt /
RUN pip install --extra-index-url https://www.piwheels.org/simple -r /requirements.txt && \
    rm /requirements.txt

# Copy lightweight data
COPY data /app/data

# Copy code and entry point
COPY oakoakbot /app/oakoakbot
COPY oakoakbot.py /app
WORKDIR /app

# Launch the bot by default
ENTRYPOINT ["python", "-u", "oakoakbot.py"]
CMD ["start"]

