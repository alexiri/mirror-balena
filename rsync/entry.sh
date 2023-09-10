#!/bin/bash -x

FSTYPE="${FSTYPE:-nfs}"
MOUNT_OPTIONS="${MOUNT_OPTIONS:-ro}"
MOUNTPOINT="/nfs"

mkdir -p "$MOUNTPOINT"

rpc.statd & rpcbind -f &
mount -t "$FSTYPE" -o "$MOUNT_OPTIONS" "$SERVER:$SHARE" "$MOUNTPOINT"
mount | grep nfs

while true; do
  sync.sh

  sleep 10m
done

