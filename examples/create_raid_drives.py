from pycimc import *
import config

__author__ = 'Rob Horner (robert@horners.org)'

'''
    Query the server for existing virtual drives and physical drives. Create a RAID1 array of the
    first two HDDs to install the OS, and create single-drive RAID0 virtual drives for the remainder
'''

remove_vds = True


for IP_ADDRESS in config.SERVERS:
    print '\n=== Server '+IP_ADDRESS+' ==='
    myserver = UcsServer(IP_ADDRESS, config.USERNAME, config.PASSWORD)

    try:
        myserver.login()

        print '=== Get Drive Inventory ==='
        if myserver.get_drive_inventory():
            myserver.print_drive_inventory()
        else:
            print "Couldn't retrieve drive inventory"

        # Build two lists - current VirtualDrive inventory and PhysicalDisk inventory to pass into pycimcexpect
        print '=== Building pycimcexpect lists for drive modification ==='

        vd_list = [vd['id'] for vd in myserver.drive_inventory['storageVirtualDrive']]

        print 'VD list:', vd_list
        pd_list = []
        for pd in myserver.drive_inventory['storageLocalDisk']:
            # confirm that the first two drives are the same size so that we can create RAID1 for the OS
            if (pd['id'] == '1') and (pd['pdStatus'] == 'Unconfigured Good'):
                first_drive_size = pd['coercedSize']
            elif (pd['id'] == '2') and (pd['pdStatus'] == 'Unconfigured Good'): # check if second drive is same size as the first drive
                if pd['coercedSize'] != first_drive_size:
                    print "First two drives are not the same size. Can't build a RAID1 array for the OS!"
                else: # special case in PD list for the first two drives to become RAID1
                    pd_list.append({'id':'1,2', 'size':pd['coercedSize'], 'raid_level':'1', 'name':'RAID1_12'})
            # All other drives become single RAID0
            # Only build RAID on HDDs, not SSDs
            ### FOR NOW ONLY DO RAID1 FOR OS ###
            # if (pd['mediaType'] == 'HDD') and (pd['pdStatus'] == 'Unconfigured Good'):
            #    pd_list.append({'id':pd['id'], 'size':pd['coercedSize'], 'raid_level':'0', 'name':'RAID0_'+pd['id']})
        print 'PD list:'
        pprint(pd_list)
        print 'PD list is length',len(pd_list)

        with AutoLogout(myserver):
            session = pycimcexpect.login(IP_ADDRESS, config.USERNAME, config.PASSWORD)
            # Use pycimcexpect remove_virtualdrives method to remove any existing VDs,
            # and the create_virtualdrives method to create new RAID0 VDs.

            # remove all existing VDs
            if (remove_vds == True) and (vd_list > 0):
                print '======  Removing existing virtual drives ======'
                pycimcexpect.remove_virtualdrives(session, vd_list, 'SLOT-4')

            # Create new RAID VDs from existing physical drives
            if pd_list:
                print '====== Creating new virtual drives ======'
                for pd in pd_list:
                    pycimcexpect.create_virtualdrives(session, pd, 'SLOT-4')
                    if len(pd_list)>1:  # allow the controller to settle between configs
                        sleep(20)
                # Reread the server's drive inventory
                sleep(5)

            # Refresh the drive inventory
            myserver.get_drive_inventory()
            myserver.print_drive_inventory()

            pycimcexpect.logout(session)

