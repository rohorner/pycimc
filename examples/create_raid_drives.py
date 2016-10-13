#!/usr/bin/env python

from pycimc import *
from collections import namedtuple
import config

__author__ = 'Rob Horner (robert@horners.org)'

'''
    Query the server for existing virtual drives and physical drives. Create a RAID1 array of the
    first two HDDs to install the OS, and create single-drive RAID0 virtual drives for the remainder
'''

VirtualDrive = namedtuple('VirtualDrive',['controller_path', 'virtual_drive_name', 'raid_level', 'raid_size', 'drive_group', 'write_policy'])

remove_vds = False

IP_ADDRESS = '192.168.200.100'

print '\n=== Server '+IP_ADDRESS+' ==='

with UcsServer(IP_ADDRESS, config.USERNAME, config.PASSWORD) as server:

    print '=== Get Drive Inventory ==='
    if server.get_drive_inventory():
        server.print_drive_inventory()
    else:
        print "Couldn't retrieve drive inventory"

    # Build two lists - current VirtualDrive inventory and PhysicalDisk inventory to pass into pycimcexpect
    print '=== Building lists for drive modification ==='

    virt_drive_list = [virt_drive['id'] for virt_drive in server.inventory['drives']['storageVirtualDrive']]

    print 'Virtual Drive list:', virt_drive_list
    new_virtual_drive_list = []
    for phys_drive in server.inventory['drives']['storageLocalDisk']:
        # confirm that the first two drives are the same size so that we can create RAID1 for the OS
        # if (phys_drive['id'] == '1') and (phys_drive['pdStatus'] == 'Unconfigured Good'):
        #     first_drive_size = phys_drive['coercedSize']
        # elif (phys_drive['id'] == '2') and (phys_drive['pdStatus'] == 'Unconfigured Good'): # check if second drive is same size as the first drive
        #     if phys_drive['coercedSize'] != first_drive_size:
        #         print "First two drives are not the same size. Can't build a RAID1 array for the OS!"
        #     else: # special case in PD list for the first two drives to become RAID1
        #         phys_drive_list.append({'id':'1,2', 'size':phys_drive['coercedSize'], 'raid_level':'1', 'name':'RAID1_12'})
        # All other drives become single RAID0
        # Only build RAID on HDDs, not SSDs
        ### FOR NOW ONLY DO RAID1 FOR OS ###
        if (phys_drive['mediaType'] == 'HDD') and (phys_drive['pdStatus'] == 'Unconfigured Good'):
            # remove the phys drive piece at the end to get the controller path
            # e.g. sys/rack-unit-1/board/storage-SAS-SLOT-2/pd-1 => sys/rack-unit-1/board/storage-SAS-SLOT-2
            full_path = phys_drive['dn']
            controller_path = full_path[:full_path.rfind('/')]
            new_virtual_drive = VirtualDrive(controller_path, 'RAID0_'+phys_drive['id'], '0', phys_drive['coercedSize'], phys_drive['id'], write_policy='Write Back Good BBU')
            new_virtual_drive_list.append(new_virtual_drive)
    print 'New Virtual Drive list:'
    pprint(new_virtual_drive_list)
    print 'New Virtual Drive list is length',len(new_virtual_drive_list)
    for virtual_drive in new_virtual_drive_list:
        #   create_virtual_drive(self, controller_path, virtual_drive_name, raid_level, raid_size, drive_group, write_policy='Write Back Good BBU', force=False):
        if server.create_virtual_drive(virtual_drive.controller_path,
                                    virtual_drive.virtual_drive_name,
                                    virtual_drive.raid_level,
                                    virtual_drive.raid_size,
                                    virtual_drive.drive_group,
                                    force=True):
            print "Successfully created drive", virtual_drive.virtual_drive_name

    if server.get_drive_inventory():
        server.print_drive_inventory()

