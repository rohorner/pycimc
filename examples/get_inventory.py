#!/usr/bin/env python

from pycimc import *
import config
from pprint import pprint

__author__ = 'Rob Horner (robert@horners.org)'

for address in config.SERVERS:
    server = UcsServer(address, config.USERNAME, config.PASSWORD)
    if server.login():
        print 'server:', address
        server.get_interface_inventory()
        # pprint(server.inventory['adaptor'])
        for int in server.inventory['adaptor']:
            out_string = 'SLOT-'+int['pciSlot']
            for port in int['port']:
                out_string += ',port-'+str(port['portId'])+','+port['adminSpeed']+','+port['linkState']
                for vnic in port['vnic']:
                    out_string += ','+str(vnic['name'])+','+str(vnic['mac'])
            print out_string
        server.logout()
    else:
        continue
