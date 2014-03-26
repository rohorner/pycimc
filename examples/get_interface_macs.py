import config

__author__ = 'Rob Horner (robert@horners.org)'

for address in config.SERVERS:
    server = UcsServer(address, config.USERNAME, config.PASSWORD)
    if server.login():

        server.get_eth_settings()
        interface_string = address + '\t'
        for interface in server.adaptor_host_eth_list:
            adaptor = interface['dn'].split('/')[2]
            interface_name = adaptor + '-' + interface['name']
            mac = interface['mac']
            interface_string += interface_name + '\t' + mac + '\t'

        print interface_string

        server.logout()
    else:
        continue