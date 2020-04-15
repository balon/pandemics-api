#!/bin/bash

if [ "$1" != "" ]; then
    apt update
    apt install -y mongodb
    sudo service mongodb start
    mongoimport --db resources --collection food_banks --file $1 --jsonArray
    mongo admin --eval "db.createUser({user: 'admin', pwd: 'changeme', roles: ['userAdminAnyDatabase', 'readWriteAnyDatabase']})"
    mongo admin --eval "db.createUser({user: 'food', pwd: 'changeme', roles: [{ role: 'read', db: 'resources' }]})"
    sudo sh -c 'echo "auth = true" >> /etc/mongodb.conf'
    sudo service mongodb restart
else
    echo "Please use following format: $0 <json_file_to_import>"
fi