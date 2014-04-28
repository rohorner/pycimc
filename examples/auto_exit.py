class AutoLogout:
    'Context manager for automatic logout'
    def __init__(self, server):
        self.server = server
    def __enter__(self):
        return self.server
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.server.logout()