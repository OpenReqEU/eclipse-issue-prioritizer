# Issue Recommendation Service for Eclipse Plugin https://img.shields.io/badge/License-EPL%202.0-blue.svg["EPL 2.0", link="https://www.eclipse.org/legal/epl-2.0/"]

This service was created as a result of the OpenReq project funded by the European Union Horizon 2020 Research and Innovation programme under grant agreement No 732463.
It includes a recommendation approach for the Eclipse Plugin that finds relevant issues for developers and ranks/prioritizes them according to certain criteria such as individual relevance (e.g., "is this issue assigned to the active user?", "do the keywords overlap with the keywords of the active user's profile?", etc.) and community relevance (e.g., "number of comments", "does this issue block other issues and if so, how many other issues are blocked and how relevant are these blocked issues?", etc.).
This project uses the [Connexion](https://github.com/zalando/connexion) library on top of Flask.

## Technical description
### What does the service do
This service provides the backend server-side functionality of Vogella's OpenReq Eclipse Plugin (see: https://github.com/OpenReqEU/eclipse-plugin-vogella).
This service addresses the Eclipse developer community.
It supports the individual Eclipse developers in their daily work by recommending relevant bugs/issues to them.
These recommended bugs/issues are then delivered to Vogella's Eclipse plugin.
The service fetches bugs/issues from the Bugzilla API of Eclipse (http://bugs.eclipse.org) and
estimates how relevant these bugs/issues are for the current developer.
The estimation of a bug/issue is based on the computation of a priority value by exploiting characteristic meta-information of the bug/issue.
After the estimation, the recommended list of issues (sorted by their priorities) is finally sent to the Eclipse plugin.
Issues with very low priorities are excluded from the recommended list.


### Which technologies are used
This service requires Python 3.7.0+

- Docker (-> https://www.docker.com/)
- Flask Connexion (-> https://github.com/zalando/connexion)
- Flask (-> https://github.com/pallets/flask)
- PickleDB (-> https://github.com/patx/pickledb)
- CacheTools (-> https://github.com/tkem/cachetools)
- PyYaml (-> https://github.com/yaml/pyyaml)
- NLTK (-> https://github.com/nltk/nltk)
- Requests (-> https://github.com/requests/requests)
- Requests-Futures (-> https://github.com/ross/requests-futures)


### How to install it
To run the server and to install all dependencies, please execute the following commands from the project root directory:

```
pip3 install -r requirements.txt
python3 -m application
```

To launch the integration tests, use tox:
```
sudo pip install tox
tox
```

### Running with Docker

To run the server on a Docker container, please execute the following commands from the project root directory:

```bash
# building the image
docker build -t application .

# starting up a container
docker run -p 9002:9002 application
```

## How to use it (high-level description)

Once the server is running, open your browser and call the following URL to see the API documentation:

```
http://localhost:9002/v1/ui/
```

The Swagger definition lives here:

```
http://localhost:9002/v1/swagger.json
```

### Notes for developers
None.

### Sources
None.

### How to contribute
See OpenReq project contribution [Guidlines](https://github.com/OpenReqEU/OpenReq/blob/master/CONTRIBUTING.md "Guidlines")

## License
Free use of this software is granted under the terms of the EPL version 2 (EPL2.0).
