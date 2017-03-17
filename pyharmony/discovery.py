#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Python port of JavaScript Harmony discovery here:
# https://github.com/swissmanu/harmonyhubjs-discover

import socket
import time
import threading


UDP_IP = '0.0.0.0'
PORT_TO_ANNOUNCE = 61991


class Discovery:
    def ping_poll(self, listen_socket, retries, interval):
        sock = socket.socket(socket.AF_INET,      # Internet
                             socket.SOCK_DGRAM)   # UDP

        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

        message = '_logitech-reverse-bonjour._tcp.local.\n{}'.format(
                        PORT_TO_ANNOUNCE).encode('utf-8')
        while retries > 0:
            time.sleep(interval)
            sock.sendto(message, ('255.255.255.255', 5224))
            retries -= 1

        # Close our ping socket
        sock.close()

        # Closing the listen_socket will trigger the 'listen_socket.accept' to
        # bail out of its synced loop and return if no hubs ever respond
        listen_socket.close()

    def deserialize_response(self, response):
        pairs = {}
        for data_point in response.split(';'):
            key_value = data_point.split(':')
            pairs[key_value[0]] = key_value[1]
        return pairs

    def discover(self, retries, timeout):
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
            args=(listen_socket, retries, timeout,),
            daemon=True)
        thread.start()

        hubs = {}
        while thread.is_alive():
            try:
                client_connection, client_address = listen_socket.accept()
                request = client_connection.recv(1024)
                hub = self.deserialize_response(request.decode('UTF-8'))
                hubs[hub['uuid']] = hub
            except Exception as e:
                # error parsing result or no hubs found
                pass
        return [hubs[h] for h in hubs]


def discover(retries=3, timeout=2):
    """Creates a Harmony client and initializes session.

    Args:
        ip_address (str): Harmony device IP address
        port (str): Harmony device port
        token (str): Valid session token

    Returns:
        A connected HarmonyClient instance
    """
    return Discovery().discover(retries, timeout)
