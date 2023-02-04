# WISdoM OSS - Golang Microservice Template
![GitHub go.mod Go version (subdirectory of monorepo)](https://img.shields.io/github/go-mod/go-version/wisdom-oss/microservice-template?filename=src%2Fgo.mod&style=for-the-badge)


This repository contains the source code for a new microservice. You may use this source code
for creating a new microservice which automatically registers at the api gateway and sets up
a route on the gateway if needed.

**DO NOT FORK THIS REPOSITORY SINCE THE COMMIT HISTORY WILL BE TRANSFERRED INTO THE NEW REPOSITORY**

## Development Steps
0. Install Golang on your development machine if not already installed
1. Download the repository as archive to your development machine
2. Create a new empty repository for your new service
3. Decompress the downloaded archive into the empty repository
4. You may now make your initial commit in the repository
5. Look for all TODOs in the files and act according to the TODOs
6. Enjoy writing your own microservice

## Configuration

The microservice template is configurable via the following environment variables:
- `CONFIG_LOGGING_LEVEL` &#8594; Set the logging verbosity [optional, default `INFO`]
- `CONFIG_API_GATEWAY_HOST` &#8594; Set the host on which the API Gateway runs on **[required]**
- `CONFIG_API_GATEWAY_ADMIN_PORT` &#8594; Set the port on which the API Gateway listens on **[required]**
- `CONFIG_API_GATEWAY_SERVICE_PATH` &#8594; Set the path under which the service shall be reachable. _Do not prepend the path with `/api`. Only set the last part of the desired path_ **[required]**
- `CONFIG_HTTP_LISTEN_PORT` &#8594; The port on which the built-in webserver will listen on [optional, default `8000`]
- `CONFIG_SCOPE_FILE_PATH` &#8594; The location where the scope definition file is stored [optional, default `/microservice/res/scope.json]

