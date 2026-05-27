#!/bin/bash
cd /root/pos-erp-v6
docker compose build api
docker compose stop api
docker compose rm -f api
docker compose create api
docker compose start api
