from pycimc import *
import config

__author__ = 'Rob Horner (robert@horners.org)'

for address in config.SERVERS:
    server = UcsServer(address, config.USERNAME, config.PASSWORD)
    if server.login():
        print 'server:', address
        server.get_fw_versions()
        server.logout()
    else:
        continue
