#!/bin/bash

SOURCE_FILE=$1
DESTINATION_DIR=$2
DESTINATION_FILE=$3
USERNAME=$4
PASSWORD=$5

echo $SOURCE_FILE
echo $DESTINATION_DIR
echo $DESTINATION_FILE

rsync -avI --block-size=131072 -P --ignore-existing -e ssh --log-file=rsync.log --rsync-path="mkdir -p ${DESTINATION_DIR} && rsync"  --rsh="/usr/bin/sshpass -p ${PASSWORD} ssh -o StrictHostKeyChecking=no -l ${USERNAME}" "${SOURCE_FILE}" "${DESTINATION_FILE}"