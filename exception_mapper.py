import logging
import requests

class ResponseError(Exception):
    pass

class PostError(Exception):
    pass

class TimeoutError(Exception):
    pass

class LoginException(Exception):
    pass

class SSL_Error(Exception):
    pass

class ConnectionError(Exception):
    pass

exception_map = {
    PostError: PostError,
    requests.exceptions.Timeout: TimeoutError,
    requests.exceptions.ConnectionError: ConnectionError,
}

class RemapExceptions():
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        # logging.exception()
        if exc_type in exception_map:
            raise exception_map[exc_type](exc_val)
