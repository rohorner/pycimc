from pycimc import *
import config

__author__ = 'Rob Horner (robert@horners.org)'

for address in config.SERVERS:
    server = UcsServer(address, config.USERNAME, config.PASSWORD)
    if server.login():

        if server.get_fw_versions():
            out_string = address + ','
            for key,value in server.fw_running.items():
                path_list = key.split('/')[2:]
                path = '/'.join(path_list)
                out_string += path + ',' + value + ','
            print out_string
        else:
            continue

        server.logout()
    else:
        continue
