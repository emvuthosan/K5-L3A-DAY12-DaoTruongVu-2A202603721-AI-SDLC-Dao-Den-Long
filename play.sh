#!/bin/sh
# Starts the game server and prints the URL. Needs Python 3.9+ only.
exec python3 -m game.server "$@"
