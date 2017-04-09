#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Python port of JavaScript Harmony discovery here:
# https://github.com/swissmanu/harmonyhubjs-discover

import socket
import time
import threading
import logging

UDP_IP = '0.0.0.0'
PORT_TO_ANNOUNCE = 61991

logger = logging.getLogger(__name__)


class Discovery:
    def ping_poll(self, listen_socket, scan_attempts, interval):
        """Broadcasts a hub discovery message across network"""

        sock = socket.socket(socket.AF_INET,      # Internet
                             socket.SOCK_DGRAM)   # UDP

        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        message = '_logitech-reverse-bonjour._tcp.local.\n{}'.format(
                        PORT_TO_ANNOUNCE).encode('utf-8')

        attempts = scan_attempts
        while attempts > 0:
            try:
                logger.debug('Pinging network on port %s', PORT_TO_ANNOUNCE)
                sock.sendto(message, ('255.255.255.255', 5224))
            except Exception as e:
                logger.error('Error pinging network: %s', e)

            time.sleep(interval)
            attempts -= 1

        # Close our ping socket
        sock.close()

        # Closing the listen_socket will trigger the 'listen_socket.accept' to
        # bail out of its synced loop and return if no hubs ever respond
        listen_socket.close()

    def deserialize_response(self, response):
        """Parses `key:value;` formatted string into dictionary"""
        pairs = {}
        if not response.strip():
            return False

        for data_point in response.split(';'):
            key_value = data_point.split(':')
            pairs[key_value[0]] = key_value[1]
        return pairs

    def discover(self, scan_attempts, scan_interval):
        # https://ruslanspivak.com/lsbaws-part1/
        listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listen_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listen_socket.bind((
            UDP_IP,
            PORT_TO_ANNOUNCE,
            ))
        listen_socket.listen(1)

        thread = threading.Thread(
            target=self.ping_poll,
            args=(listen_socket, scan_attempts, scan_interval,),
            daemon=True)
        thread.start()

        hubs = {}
        try:
            while thread.is_alive():
                client_connection, client_address = listen_socket.accept()
                while True:
                    request = client_connection.recv(1024)
                    if not request:
                        break

                    hub = self.deserialize_response(
                        request.decode('UTF-8'))

                    if hub:
                        uuid = hub['uuid']
                        if uuid not in hubs:
                            logger.debug('Found new hub %s', uuid)
                            hubs[hub['uuid']] = hub
                        else:
                            logger.debug('Found existing hub %s', uuid)

                client_connection.close()
        except ConnectionAbortedError as e:
            # Thread (possibly) closed the socket after no hubs found
            pass
        return [hubs[h] for h in hubs]


def discover(scan_attempts=10, scan_interval=1):
    """Creates a Harmony client and initializes session.

    Args:
        scan_attempts (int): Number of times to scan the network
        scan_interval (int): Seconds between running each network scan

    Returns:
        A list of Hub devices found and their configs
    """
    return Discovery().discover(scan_attempts, scan_interval)
