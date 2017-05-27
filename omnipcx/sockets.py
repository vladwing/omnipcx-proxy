import socket
import time
from omnipcx.logging import Loggable


class Server(Loggable):
    def __init__(self, config):
        super(Server, self).__init__()
        self.opera_port = config['opera_port']
        self.old_port = config['old_port']
        self.cdr_port = config['cdr_port']
        self.old_address = config['old_address']
        self.cdr_address = config['cdr_address']
        self.timeout = 5.0
        self.retries = config['retries']
        self.retry_sleep = config['retry_sleep']

    def listen(self):
        server = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        address = "::" # socket.gethostname()
        self.logger.info("Listening on [%s]:%d ...", address, self.opera_port)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((address, self.opera_port))
        server.listen(1)
        while True:
            self.logger.info("Waiting for client connection ...")
            try:
                yield server.accept()
            except KeyboardInterrupt:
                self.logger.warn("Stopped by Control+C")
                return

    def connect(self, address, port):
        try:
            skt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            skt.settimeout(self.timeout)
            self.logger.info("Trying to open a connection to %s:%s" %(address, port))
            skt.connect((address, port),)
            return skt
        except ConnectionRefusedError:
            return None

    def socket_tuples(self):
        for skt_old, address in self.listen():
            skt_old.settimeout(self.timeout)
            retries = self.retries
            skt_cdr = None
            skt_opera = None
            while retries > 0:
                if skt_cdr is None:
                    skt_cdr = self.connect(self.cdr_address, self.cdr_port)
                if skt_opera is None:
                    skt_opera = self.connect(self.old_address, self.old_port)
                if skt_opera is None or skt_cdr is None:
                    retries -= 1
                    self.logger.warn("Couldn't open connection. Waiting ...")
                    time.sleep(self.retry_sleep)
                    continue
                else:
                    retries = 0
            if skt_opera is None or skt_cdr is None:
                if skt_opera:
                    self.logger.info("Closing connection to Opera")
                    skt_opera.close()
                if skt_cdr:
                    self.logger.info("Closing connection to CDR collector")
                    skt_cdr.close()
                self.logger.error("Couldn't connect to OLD or CDR collector. Giving up.")
                skt_old.close()
                continue
            yield skt_old, skt_opera, skt_cdr

