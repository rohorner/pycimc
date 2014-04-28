from pycimc import UcsServer
import config

for address in config.SERVERS:
    with UcsServer(address, config.USERNAME, config.PASSWORD) as server:
        server.get_fw_versions()
        out_string = server.ipaddress + ','
        for key,value in server.inventory['fw'].items():
            path_list = key.split('/')[2:]
            path = '/'.join(path_list)
            out_string += path + ',' + value + ','
        print out_string
