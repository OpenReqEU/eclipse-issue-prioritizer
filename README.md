# Issue Recommendation Service for Eclipse Plugin

## Overview
This service includes a recommendation approach for the Eclipse Plugin that finds relevant issues for developers and ranks/priorizes them according to certain criteria such as individual relevance (e.g., "is this issue assigned to the active user?", "do the keywords overlap with the keywords of the active user's profile?", etc.) and community relevance (e.g., "number of comments", "does this issue block other issues and if so, how many other issues are blocked and how relevant are these blocked issues?", etc.).
This project uses the [Connexion](https://github.com/zalando/connexion) library on top of Flask.

## Requirements
Python 3.7.0+

## Usage
To run the server, please execute the following from the root directory:

```
pip3 install -r requirements.txt
python3 -m application
```

and open your browser to here:

```
http://localhost:9002/v1/ui/
```

Your Swagger definition lives here:

```
http://localhost:9002/v1/swagger.json
```

To launch the integration tests, use tox:
```
sudo pip install tox
tox
```

## Running with Docker

To run the server on a Docker container, please execute the following from the root directory:

```bash
# building the image
docker build -t application .

# starting up a container
docker run -p 9002:9002 application
```
