#!/bin/bash -x

OPTIONS="-avPi --no-owner --no-group"

rsync $OPTIONS /nfs/${CONFIG} /config/
rsync $OPTIONS /nfs/${CSS} /css/
rsync $OPTIONS /nfs/${MODULES} /modules --exclude=default

