import logging
import requests

class ResponseException(Exception):
    pass

class PostException(Exception):
    pass

class TimeoutException(Exception):
    pass

class LoginException(Exception):
    pass

class SSL_Error(Exception):
    pass

exception_map = {
    PostException: PostException,
    requests.exceptions.Timeout: TimeoutException
}

class RemapExceptions():
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        # logging.exception()
        if exc_type in exception_map:
            raise exception_map[exc_type]
