# sigmsg
sigmsg is a python implementation of a client using [signal-cli](https://github.com/AsamK/signal-cli).  You can find other client implementations on the [signal-cli wiki](https://github.com/AsamK/signal-cli/wiki#signal-cli-scriptsexamples).  

## Key differentiators:
1. signal-cli docker: Relies directly on [signal-cli docker builds](https://gitlab.com/packaging/signal-cli/container_registry) instead of a lengthy install
2. Utilizes the json-rpc capability of signal-cli (and therefore, sockets to communicate with signal-cli)
3. Utilizes aiohttp to receive external commands

## Installation
Installation assumes you have git, docker, python, pip and/or virtualenv installed
```
# pull the repo
git clone git@github.com:digitalbodhi/sigmsg

# go into the repo
cd sigmsg

# start the docker image (prefix with sudo if needed)
docker compose up --build

# login to the docker shell to run signal-cli commands (prefix with sudo if needed)
docker exec -u 0 -it signal-cli /bin/bash

# perform the steps to setup your phone with signal-cli -- example using linking below, more options @ https://github.com/AsamK/signal-cli/ under "Usage"
signal-cli link -n "seconddevice" | tee >(xargs -L 1 qrencode -t utf8)

# load the packages used to run the program
pip install -r requirements.txt

# Then make sure to modify the config.yaml with your specific host, port, phone number, etc...
vim config.yaml
```

## Usage
```
# start the program
python3 signalclient.py

# send a REST API request to the server (e.g., localhost:8080) to send a message to your phone number of choice (e.g., +12345678901)
curl -X POST localhost:8080 \
  -H 'Content-Type: application/json'
  -d '{"recipients": ["+12345678901"], "message": "hi"}'
```
