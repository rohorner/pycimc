#!/usr/bin/env python

from pycimc import *
import config
from pprint import pprint

ADDRESS = '192.168.200.101'
USERNAME = 'admin'
PASSWORD = 'password'


with UcsServer(ADDRESS, USERNAME, PASSWORD) as server:
    out_string = server.ipaddress
    if server.get_interface_inventory():
        for int in server.inventory['adaptor']:
            out_string += ',SLOT-'+int['pciSlot']
            for port in int['port']:
                out_string += ',port-'+str(port['portId'])+','+port['adminSpeed']+','+port['linkState']
                for vnic in port['vnic']:
                    out_string += ','+str(vnic['name'])+','+str(vnic['mac'])
            print out_string
    else:
        print 'get_interface_inventory() returned False'