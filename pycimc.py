__author__ = 'Rob Horner (robert@horners.org)'

import xml.etree.ElementTree as ET
from collections import namedtuple, defaultdict
import time
import inspect
import pprint

import requests

LOGIN_TIMEOUT = 5.0
REQUEST_TIMEOUT = 10.0

Version = namedtuple('Version',['major','minor'])   # Class variable - data shared

##### Create XML template strings
'''
Sample:
<configConfMo cookie="%s">
    <inConfig>
        <biosVfDemandScrub
            dn="sys/rack-unit-1/bios/bios-settings/Demand-Scrub-Param"
            vpDemandScrub="disabled">
        </biosVfDemandScrub>
    </inConfig>
</configConfMo>
'''

configConfMo_prepend_string = '''<configConfMo cookie="%s" dn="sys/rack-unit-1/bios/bios-settings" inHierarchical="true">
  <inConfig>
    <biosSettings dn="sys/rack-unit-1/bios/bios-settings">\n'''
configConfMo_template = '      <{item.tag} rn="{item.rn}" {item.setting}></{item.tag}>\n'
configConfMo_append_string = '''    </biosSettings>
  </inConfig>
</configConfMo>
'''


#########
#### Command String dictionary ####
command_strings = {
    'chassis':       '<configResolveClass    cookie="%s" inHierarchical="false" classId="computeRackUnit"/>',
    'cimc':          '<configResolveClass    cookie="%s" inHierarchical="false" classId="mgmtIf"/>',
    'boot_order':    '<configResolveChildren cookie="%s" inHierarchical="false"    inDn="sys/rack-unit-1/boot-policy"/>',
    'local_disk':    '<configResolveClass    cookie="%s" inHierarchical="false" classId="storageLocalDisk"/>',
    'virtual_drive': '<configResolveClass    cookie="%s" inHierarchical="false" classId="storageVirtualDrive"/>',
    'adaptors':      '<configResolveClass    cookie="%s" inHierarchical="false" classId="adaptorUnit"/>',
    'ports':         '<configResolveClass    cookie="%s" inHierarchical="false" classId="adaptorExtEthIf"/>',
    'vnics':         '<configResolveClass    cookie="%s" inHierarchical="false" classId="adaptorHostEthIf"/>',
    'pci':           '<configResolveClass    cookie="%s" inHierarchical="false" classId="pciEquipSlot"/>',
    'bios':          '<configResolveClass    cookie="%s" inHierarchical="true"  classId="biosSettings"/>',
    'fw':            '<configResolveClass    cookie="%s" inHierarchical="false" classId="firmwareRunning"/>',
}
####

# timeit decorator for, you know, timing testing
def timeit(method):
    def timed(*args, **kw):
        tstart = time.time()
        result = method(*args, **kw)
        tend = time.time()
        print '%r (%r, %r) %2.2f sec' % \
              (method.__name__, args, kw, tend-tstart)
        return result
    return timed

class ResponseException(Exception):
    pass

class PostException(Exception):
    pass

class TimeoutException(Exception):
    pass

class LoginException(Exception):
    pass

class SSLError(Exception):
    pass

class InventoryDict(defaultdict):

    # pprint doesn't know how to handle defaultdict - it wants a dict __repr__.
    # Let's override its __repr__ method so that it prints out like a regular dict
    __repr__ = dict.__repr__

class UcsServer():

    version = Version(0,2)

    def __init__(self, ipaddress, username, password):
        self.session_cookie = None
        self.session_refresh_period = None
        self.status_message = ''
        self.ipaddress = ipaddress
        self.username = username
        self.password = password
        self.serial_no = 'not queried'
        self.model = 'not queried'
        self.total_memory = 0
        self.inventory = InventoryDict()

    # Context Manager
    def __enter__(self):
        if self.login():
            return self

    def __exit__(self, exctype, excinst, exctb):
        if exctype is not None:
            print '%s' % excinst.args[0]
            return True
        # print 'Returning None which is a false value, meaning, no execeptions were handled'
        self.logout()

    def login(self):
        '''
        Log in to the CIMC using the instance's ipaddress, username, and password configured during init()

        XML Query:
        <aaaLogin inName='admin' inPassword='password'></aaaLogin>" -X POST https://172.29.85.36/nuova --insecure
        XML Response:
        <aaaLogin cookie="" response="yes" outCookie="1394044707/539306f8-f3e0-13e0-8005-1af7ea354e4c" outRefreshPeriod="600"
            outPriv="admin" outSessionId="43" outVersion="1.5(4)"> </aaaLogin>

        '''
        command_string = "<aaaLogin inName='%s' inPassword='%s'></aaaLogin>" % (self.username, self.password)
        try:
            response = post_request(self.ipaddress, command_string, timeout=LOGIN_TIMEOUT)
            if 'outCookie' in response.attrib:
                self.session_cookie = response.attrib['outCookie']
            if 'outRefreshPeriod' in response.attrib:
                self.session_refresh_period = response.attrib['outRefreshPeriod']
            if 'outVersion' in response.attrib:
                self.version = response.attrib['outVersion']
            return True
        except ResponseException as e:
            print '%s: pycimc.login ResponseException: %s' % (self.ipaddress, e)
            return False
        except TimeoutException as e:
            print '%s: pycimc.login TimeoutException: %s' % (self.ipaddress, e)
            return False
        except PostException as e:
            print '%s: pycimc.login PostException: %s' % (self.ipaddress, e)
            return False

    def logout(self):
        '''
        Log out of the server instance. Invalidates the current session cookie in self.session_cookie
        '''
        command_string = "<aaaLogout cookie='%s' inCookie='%s'></aaaLogout>" % (self.session_cookie, self.session_cookie)
        auth_response = post_request(self.ipaddress, command_string)

        if 'errorCode' in auth_response:
            self.status_message = "Logout Error: Server returned status code %s: %s" % (auth_response['errorCode'], auth_response['errorDescr'])
            raise Exception
        else:
            return True

    def set_power_state(self, power_state, force=False):
        '''
        Change the power state of the server.

        power_state options from the XML Schema are
                "up", "down", "soft-shut-down", "cycle-immediate",
                "hard-reset-immediate", bmc-reset-immediate",
                "bmc-reset-default", "cmos-reset-immediate",
                "diagnostic-interrupt"
        '''
        if force:
            command_string = '''<configConfMo cookie="%s" dn="sys/rack-unit-1" inHierarchical="false">\
            <inConfig>\
            <computeRackUnit dn="sys/rack-unit-1" adminPower="%s"></computeRackUnit>
            </inConfig>\
            </configConfMo>''' % (self.session_cookie, power_state)
            response_element = post_request(self.ipaddress, command_string)
            return True
        else:
            print 'power() must be called with "force=True" to change the power status of the server'
            return False

    def refresh_cookie(self):
        pass

    def get_chassis_info(self):
        '''
        Get the top-level chassis info and record useful info like serial number, model, memory, etc, in server.inventory['chassis'] sub-dictionary
        '''
        chassis_dict = {}
        try:
            command_string = '<configResolveClass cookie="%s" inHierarchical="false" classId="computeRackUnit"/>' % self.session_cookie
            response_element = post_request(self.ipaddress, command_string)
            for key,value in response_element.find('.//computeRackUnit').items():
                chassis_dict[key] = value
            self.inventory['chassis'] = chassis_dict
            self.serial_no = self.inventory['chassis']['serial']
            self.model = self.inventory['chassis']['model']
            self.total_memory = self.inventory['chassis']['totalMemory']
            self.name = self.inventory['chassis']['name']
            self.operPower = self.inventory['chassis']['operPower']
            return True
        except PostException as e:
            print 'pycimc.get_chassis_info: post_request returned error:', e
            return False

    def get_cimc_info(self):
        cimc_dict = {}
        try:
            command_string = '<configResolveChildren cookie="%s" inHierarchical="true" inDn="sys/rack-unit-1/mgmt"/>' % self.session_cookie
            response_element = post_request(self.ipaddress, command_string)
            out_configs = response_element.find('outConfigs')
            self.inventory['cimc'] = out_configs.find('mgmtIf').attrib
        except PostException as e:
            print 'pycimc.get_cimc_info: post_request returned error:', e
        except TimeoutException as e:
            print 'pycimc.get_cimc_info:', e
        else:
            return True
        return False

    def get_boot_order(self):
        bootorder_dict = {}
        try:
            command_string = '<configResolveChildren cookie="%s" inHierarchical="false" inDn="sys/rack-unit-1/boot-policy"/>' % self.session_cookie
            response_element = post_request(self.ipaddress, command_string)
            out_configs = response_element.find('outConfigs')
            for i in out_configs.getchildren():
                bootorder_dict[i.attrib['order']] = i.attrib['type']
            # represent the boot order as an ordered list from the returned dict based on the 'order' key
            #   {'1': 'virtual-media', '3': 'storage', '2': 'lan'} becomes ['virtual-media', 'lan', 'storage']
            self.inventory['boot_order'] = [bootorder_dict[key] for key in sorted(bootorder_dict)]
            return True
        except PostException as e:
            print 'pycimc.get_boot_order: post_request returned error:', e
            return False
        except TimeoutException as e:
            print 'pycimc.get_boot_order:', e
            return False

    def get_drive_inventory(self):
        '''
        Retrieve both physical and virtual drive inventories.
        Populate <instance>.drive_inventory with the resulting dictionary
        '''

        drive_dict = {'storageLocalDisk':[], 'storageVirtualDrive':[]}
        command_string = ['<configResolveClass cookie="%s" inHierarchical="false" classId="storageLocalDisk"/>' % self.session_cookie,
                          '<configResolveClass cookie="%s" inHierarchical="false" classId="storageVirtualDrive"/>' % self.session_cookie]
        try:
            for command in command_string:
                response_element = post_request(self.ipaddress, command)
                out_configs = response_element.find('outConfigs')
                for config in out_configs.getchildren():
                    drive_dict[config.tag].append(config.attrib)
            self.inventory['drives'] = drive_dict
            return True
        except SyntaxError as e:
            print 'post_request returned error:', e
            return False

    def print_drive_inventory(self):
        '''
        Print out the drive inventory dict in a user-friendly format.
        '''
        if any(self.inventory['drives']):
            if 'storageVirtualDrive' in self.drive_inventory:
                print 'Virtual Drives:'
                for vd in self.inventory['drives']['storageVirtualDrive']:
                    print "{id:>2} {dn:<48} {size:>11}  {raidLevel}  {name}".format(**vd)
                print 'Physical Drives:'
                for pd in self.inventory['drives']['storageLocalDisk']:
                    print "{id:>2} {dn:<48} {coercedSize:>11}  {pdStatus}".format(**pd)
            #print self.inventory['drives']
        else:
            print 'No drive inventory found! Please run "get_drive_inventory() on the server instance first.'

    #@timeit
    def get_interface_inventory(self):
        '''
        Get network interface inventory with three calls:
            query adaptorUnit classId to find all adaptors
            query adaptorExtEthIf classId to find all physical network interfaces
            query adaptorHostEthIf classId to find all vNIC interfaces
        Combine all of the results in a hierarchical dict structure and return it in self.inventory['interfaces']
        '''

        adaptorUnit_list = []
        adaptorHostEthIf_list = []
        adaptorExtEthIf_list = []
        try:
            # query adaptorUnit classId to find all adaptors
            #  {'dn': 'sys/rack-unit-1/adaptor-2', 'cimcManagementEnabled': 'no', 'vendor': 'Cisco Systems Inc', 'description': '', 'presence': 'equipped', 'model': 'UCSC-PCIE-CSC-02', 'adminState': 'policy', 'pciSlot': '2', 'pciAddr': '64', 'serial': 'FCH17457FSM', 'id': '2'}
            #  {'dn': 'sys/rack-unit-1/adaptor-5', 'cimcManagementEnabled': 'no', 'vendor': 'Cisco Systems Inc', 'description': '', 'presence': 'equipped', 'model': 'UCSC-PCIE-CSC-02', 'adminState': 'policy', 'pciSlot': '5', 'pciAddr': '73', 'serial': 'FCH17457FUC', 'id': '5'}

            command_string = '<configResolveClass cookie="%s" inHierarchical="false" classId="%s"/>' %\
                             (self.session_cookie, 'adaptorUnit')
            response_element = post_request(self.ipaddress, command_string)
            out_configs = response_element.find('outConfigs')
            for config in out_configs.getchildren():
                adaptorUnit_list.append(config.attrib)
            #self.inventory['adaptor'] = adaptorUnit_list

            # query adaptorExtEthIf classId to find all physical network interfaces
            command_string = '<configResolveClass cookie="%s" inHierarchical="false" classId="%s"/>' %\
                             (self.session_cookie, 'adaptorExtEthIf')
            response_element = post_request(self.ipaddress, command_string)
            out_configs = response_element.find('outConfigs')
            for config in out_configs.getchildren():
                adaptorExtEthIf_list.append(config.attrib)
            #self.inventory['ext_eth_if'] = adaptorExtEthIf_list

            # query adaptorHostEthIf classId to find all vNIC interfaces
            command_string = '<configResolveClass cookie="%s" inHierarchical="false" classId="%s"/>' %\
                             (self.session_cookie, 'adaptorHostEthIf')
            response_element = post_request(self.ipaddress, command_string)
            out_configs = response_element.find('outConfigs')
            for config in out_configs.getchildren():
                adaptorHostEthIf_list.append(config.attrib)
            #self.inventory['host_eth_if'] = adaptorHostEthIf_list

        except PostException as e:
            print 'pycimc.get_eth_settings: post_request returned error:', e
            return False

        # Build a nested JSON structure with adaptor, physical ports, and vnics
        out_list = []
        for adaptor in adaptorUnit_list:
            # create an empty list of ports for each adaptor
            if 'port' not in adaptor.keys():
                adaptor['port'] = []
            for port in adaptorExtEthIf_list:
                # create an empty list of vnics for each port
                if 'vnic' not in port.keys():
                    port['vnic'] = []
                # If this port is on the current adaptor, append its dict to the 'port' list
                if adaptor['dn'].split('/')[2] == port['dn'].split('/')[2]:
                    adaptor['port'].append(port)
                    for vnic in adaptorHostEthIf_list:
                        # If this vnic is on the current adaptor and is also on the current port,
                        #  append it to the port's vnic list
                        if (adaptor['dn'].split('/')[2] == vnic['dn'].split('/')[2]) and (vnic.get('uplinkPort') == port['portId']):
                            port['vnic'].append(vnic)

            out_list.append(adaptor)

        self.inventory['adaptor'] = out_list
        return True

    def get_pci_inventory(self):
        '''
        Query the pciEquipSlot class to get all PCI cards
        pciEquipSlot : {'dn': 'sys/rack-unit-1/equipped-slot-2', 'smbiosId': '2', 'controllerReported': '2', 'vendor': '0x1137', 'model': 'UCS VIC 1225 10Gbps 2 port CNA SFP+', 'id': '2'}
        pciEquipSlot : {'dn': 'sys/rack-unit-1/equipped-slot-4', 'smbiosId': '4', 'controllerReported': '4', 'vendor': '0x1000', 'model': 'LSI 9271-8i MegaRAID SAS HBA', 'id': '4'}
        pciEquipSlot : {'dn': 'sys/rack-unit-1/equipped-slot-5', 'smbiosId': '5', 'controllerReported': '5', 'vendor': '0x1137', 'model': 'UCS VIC 1225 10Gbps 2 port CNA SFP+', 'id': '5'}
        '''

        pciEquipSlot_list = []
        try:
            command_string = '<configResolveClass cookie="%s" inHierarchical="false" classId="pciEquipSlot"/>' % self.session_cookie
            response_element = post_request(self.ipaddress, command_string)
            out_configs = response_element.find('outConfigs')
            for config in out_configs.getchildren():
                pciEquipSlot_list.append(config.attrib)
            self.inventory['pci'] = pciEquipSlot_list
            return True
        except PostException as e:
            print 'pycimc.get_eth_settings: post_request returned error:', e
            return False

    def get_bios_settings(self):
        '''
        Query the firmwareRunning class to get all FW versions on the server
        Populate <instance>.bios_settings with the resulting dictionary
        '''

        bios_dict = {}
        command_string = '<configResolveClass cookie="%s" inHierarchical="true" classId="biosSettings"/>' % self.session_cookie
        url = "https://%s/nuova" % self.ipaddress
        try:
            response_element = post_request(self.ipaddress,command_string)
            all_bios_settings = response_element.find('*/biosSettings').getchildren()
            for i in all_bios_settings:
                bios_dict[i.attrib['rn']] = {}
                for key,value in i.items():
                    if key != 'rn':
                      bios_dict[i.attrib['rn']][key]=value
            self.inventory['bios'] = bios_dict
            return True
        except PostException as e:
            print 'pycimc.get_fw_versions:', e
            return False

    def set_bios_custom(self):
        '''
        Set the BIOS settings to Cisco's recommendations for virtualization
        '''
        command_string = configConfMo_prepend_string % self.session_cookie
        for item in config.CUSTOM_BIOS_SETTINGS:
            command_string += configConfMo_template.format(item=item)
        command_string += configConfMo_append_string

        try:
            response_element = post_request(self.ipaddress, command_string)
            return True
        except SyntaxError as e:
            print 'post_request returned error:', e
            return False

    def get_users(self):
        user_list = []
        command_string = '<configResolveClass cookie="%s" inHierarchical="false" classId="aaaUser"/>' % self.session_cookie
        try:
            response_element = post_request(self.ipaddress, command_string)
            for user in response_element.findall('*/aaaUser'):
                if user.attrib['name'] is not '':
                    user_list.append(user.attrib)
            self.inventory['users'] = user_list
            return True
        except PostException as e:
            print 'pycimc.get_fw_versions:', e
            return False

    def set_password(self, userid, password):
        '''<configConfMo cookie="<cookie>" inHierarchical="false" dn="sys/user-ext/user-3">
                <inConfig>
                    <aaaUser id="3" pwd="<new_password>" />
                </inConfig>
            </configConfMo>'''
        if len(self.inventory['users']) == 0:
            self.get_users()
        # Make sure we have the requested user
        try:
            (id, dn) = next((user['id'],user['dn']) for user in self.inventory['users'] if user['name'] == userid)
        except StopIteration:
            print 'Cannot find user', userid
            return False

        # ready to go. Change the user password
        command_string = '<configConfMo cookie="%s" inHierarchical="false" dn="%s">\
            <inConfig> <aaaUser id="%s" pwd="%s" /> </inConfig> </configConfMo>' % (self.session_cookie, dn, id, password)
        try:
            response_element = post_request(self.ipaddress, command_string)
            return True
        except PostException as e:
            print 'pycimc.set_password:', e
            return False

    def get_fw_versions(self):
        '''
        Query the firmwareRunning class to get all FW versions on the server
        Populate <instance>.inventory['fw'] with the resulting sorted list
        '''
        fw_dict = {}
        command_string = '<configResolveClass cookie="%s" inHierarchical="false" classId="firmwareRunning"/>' % self.session_cookie
        try:
            response_element = post_request(self.ipaddress,command_string)
            for i in response_element.iter('firmwareRunning'):
                # ignore elements with 'fw-boot-loader'. More detail than we care about
                # we just want 'fw-system' entries
                if 'fw-boot-loader' not in i.attrib['dn']:
                    fw_dict[i.attrib['dn']] = i.attrib['version']
            self.inventory['fw'] = fw_dict
            return True
        except PostException as e:
            print 'pycimc.get_fw_versions:', e
            return False
        except TimeoutException as e:
            print 'pycimc.get_fw_version:', e
            return False

def post_request(server, command_string, timeout=REQUEST_TIMEOUT):
    url = "https://%s/nuova" % server
    try:
        response = ET.fromstring(requests.post(url, data=command_string, verify=False, timeout=timeout).text)
        #print 'response.attrib:', response.attrib
        # Check if the response has an 'errorCode' key if something went wrong
        # if so, then print the error message and raise an exception
        if 'errorCode' in response.keys():
            # print 'command:', command_string
            # print 'response.attrib:', response.attrib
            raise ResponseException("'%s': '%s'" % (response.attrib['errorCode'], response.attrib['errorDescr']))
        else:
            return response
    except requests.exceptions.Timeout:
        raise TimeoutException('post_request(): Timeout error to %s.' % server)
    except requests.exceptions.SSLError:
        raise SSLError('post_request(): SSL connection error to %s.' % server)


if __name__ == "__main__":
    IPADDR = '172.29.85.36'
    USERNAME = 'admin'
    PASSWORD = 'password'


    if 0:
        if myserver.login():
            if len(myserver.inventory['users'].keys()) == 0:
                print '== user list empty - getting user list =='
                myserver.get_users()
                print myserver.inventory['users']
            print '== setting new password =='
            myserver.set_password('admin','cisco')
            myserver.logout()

    if 1:
        with UcsServer(IPADDR,USERNAME,PASSWORD) as myserver:
            print '== chassis info =='
            myserver.get_chassis_info()
            print '== CIMC info =='
            myserver.get_cimc_info()
            print '== Boot order =='
            myserver.get_boot_order()
            print '== Drive inventory =='
            myserver.get_drive_inventory()
            print '== FW versions =='
            myserver.get_fw_versions()
            print '== BIOS settings =='
            myserver.get_bios_settings()
            print '== PCI inventory =='
            myserver.get_pci_inventory()
            print '== Interface inventory =='
            myserver.get_interface_inventory()


    if 0:
        if myserver.login():
            for item,command in command_strings.items():
                start = time.time()
                full_command = command % myserver.session_cookie
                response = post_request(myserver.ipaddress, full_command)
                print item
                tmp = response.find('outConfigs').getchildren()
                for item in tmp:
                    print item.tag, item.attrib
                print (time.time() - start)
                print '\n'

            myserver.logout()