# Issue Recommendation Service for Eclipse Plugin [![EPL 2.0](https://img.shields.io/badge/License-EPL%202.0-blue.svg)](https://www.eclipse.org/legal/epl-2.0/)

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

The approach provided by this code base is based on multi-attribute utility theory (MAUT) which uses the following set of attributes (meta-data) provided by Bugzilla
to rank the list of recommended issues. The weights have been learned based on historic data of Eclipse Bugzilla issues and express the relevance/importance.

| Attribute                 | Weight      | Description                                                                                   |
| ------------------------- | :---------: | --------------------------------------------------------------------------------------------- |
| `assigned_to`             |  2.5        | States whether the current user/developer is already assigned to the (unresolved) issue.      |
| `cc`                      |  1.7        | Number of cc-mail-recipients assigned to the issue                                            |
| `gerrit`                  |  2.2        | Number of source code contributions (i.e., commits for this issue in GIT)                     |
| `blocks`                  |  1.4        | Number of issues which block/depend on the issue                                              |
| `comments`                |  1.9        | Number of comments provided for the issue                                                     |
| `keywords`                |  2.8        | Number of keywords extracted from the issue matching the user's/developer's profile           |
| `component_belongingness` |  2.8        | Degree of the developer's past contributions in the Eclipse component of the issue            |
| `reward`                  |  2.0        | `TRUE` (i.e., 1) if the user/developer liked the issue `FALSE` (i.e., 0) otherwise            |
| `severity`                |  1.8        | Severity level defined for the issue                                                          |
| `priority`                |  2.2        | Estimated global priority level of the issue for the community                                |
| `age`                     | -4.2        | Age of the issue (negative weight indicates that the older the issue the less relevant it is) |


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
http://217.172.12.199:9002/ui/
```

The Swagger definition lives here:

```
http://217.172.12.199:9002/swagger.json
```

[Rendered Documentation](https://api.openreq.eu/#/services/issue-prioritizer-api)

### Notes for developers
See [Developer Guidelines](https://github.com/OpenReqEU/eclipse-issue-prioritizer/blob/master/developer.adoc "Developer Guidlines")

### Sources
None.

### How to contribute
See OpenReq project contribution [Guidlines](https://github.com/OpenReqEU/OpenReq/blob/master/CONTRIBUTING.md "Guidlines")

## License
Free use of this software is granted under the terms of the EPL version 2 ([EPL2.0](https://www.eclipse.org/legal/epl-2.0/)).
