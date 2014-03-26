__author__ = 'Rob Horner (robert@horners.org)'

import xml.etree.ElementTree as ET
from collections import namedtuple
from time import time

import requests
REQUEST_TIMEOUT = 60.0

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

##### Create XML template strings
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
    'boot-policy':'<configResolveChildren cookie="%s" inHierarchical="false" inDn="sys/rack-unit-1/boot-policy"/>',
    'drive-inventory':'<configResolveClass cookie="%s" inHierarchical="false" classId="storageLocalDisk"/>',
    'vic-settings':'<configResolveClass cookie="%s" inHierarchical="false" classId="adaptorHostEthIf"/>',

}
####

# timeit decorator
def timeit(method):
    def timed(*args, **kw):
        ts = time()
        result = method(*args, **kw)
        te = time()
        print '%r (%r, %r) %2.2f sec' % \
              (method.__name__, args, kw, te-ts)
        return result
    return timed

class LoginException(Exception):
    pass

MoSetting = namedtuple('MoSetting',['tag','rn','setting'])
custom_bios_settings = (
    MoSetting('biosVfDemandScrub',
              'Demand-Scrub-Param',
              'vpDemandScrub="disabled"'),
    MoSetting('biosVfIntelTurboBoostTech',
              'Intel-Turbo-Boost-Tech',
              'vpIntelTurboBoostTech="disabled"'),
    MoSetting('biosVfHardwarePrefetch',
              'Hardware-Prefetch',
              'vpHardwarePrefetch="disabled"'),
    MoSetting('biosVfAdjacentCacheLinePrefetch',
              'Adjacent-Cache-Line-Prefetch',
              'vpAdjacentCacheLinePrefetch="disabled"'),
    MoSetting('biosVfProcessorC1E',
              'Processor-C1E',
              'vpProcessorC1E="disabled"'),
    MoSetting('biosVfDCUPrefetch',
              'DCU-Prefetch',
              'vpStreamerPrefetch="disabled" vpIPPrefetch="disabled"'),
    MoSetting('biosVfCPUPowerManagement',
              'CPU-PowerManagement',
              'vpCPUPowerManagement="custom"'),
    MoSetting('biosVfCPUFrequencyFloor',
              'CPU-FreqFloor',
              'vpCPUFrequencyFloor="enabled"'),
    MoSetting('biosVfCPUEnergyPerformance',
              'CPU-EngPerfBias',
              'vpCPUEnergyPerformance="performance"'),
    MoSetting('biosVfIntelVTForDirectedIO',
              'Intel-VT-for-directed-IO',
              'vpIntelVTDATSSupport="enabled" vpIntelVTDCoherencySupport="enabled" vpIntelVTForDirectedIO="enabled"'),
    MoSetting('biosVfDRAMClockThrottling',
              'DRAM-Clock-Throttling',
              'vpDRAMClockThrottling="Performance"'),
    MoSetting('biosVfPatrolScrub',
              'Patrol-Scrub-Param',
              'vpPatrolScrub="disabled"'),
)

class ImcSession():
    def __init__(self, ipaddress, username, password):
        '''
        UCS CIMC session handle. Typically attached to a UcsServer instance.
        '''
        self.session_cookie = None
        self.session_id = None
        self.session_refresh_period = None
        self.ipaddress = ipaddress
        self.username = username
        self.password = password

    def login(self):
        pass

    def refresh(self):
        pass

    def logout(self):
        pass

    def __repr__(self):
        pass

    def __str__(self):
        pass

class UcsServer():
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
        self.inventory = {}
        self.inventory['fw'] = {}
        self.inventory['bios'] = {}
        self.inventory['drives'] = {}
        self.inventory['boot_order'] = {}
        self.inventory['chassis'] = {}

    #@timeit
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
            response = post_request(self, command_string)
            if 'errorCode' in response.attrib:
                self.status_message = "Login Error: Server returned status code %s: %s" % (response.attrib['errorCode'], response.attrib['errorDescr'])
                raise Exception
            else:
                if 'outCookie' in response.attrib:
                    self.session_cookie = response.attrib['outCookie']
                if 'outRefreshPeriod' in response.attrib:
                    self.session_refresh_period = response.attrib['outRefreshPeriod']
                if 'outVersion' in response.attrib:
                    self.version = response.attrib['outVersion']
                return True
            return response
        except TimeoutException as e:
            print 'login to %s timed out' % self.ipaddress
            return False
        except PostException as e:
            print 'pycimc.login: post_request returned error:', e
            return False


    def logout(self):
        #print '== logging out of <%s> ==' % self.ipaddress
        #print 'logout session cookie:', self.session_cookie
        command_string = "<aaaLogout cookie='%s' inCookie='%s'></aaaLogout>" % (self.session_cookie, self.session_cookie)
        auth_response = post_request(self, command_string)

        if 'errorCode' in auth_response:
            self.status_message = "Logout Error: Server returned status code %s: %s" % (auth_response['errorCode'], auth_response['errorDescr'])
            raise Exception
        else:
            return True

    def reboot(self, force=False):
        '''
        Immediately reboot the server. Other power options from the XML Schema are "up", "down", "soft-shut-down",
        "cycle-immediate", "hard-reset-immediate", bmc-reset-immediate", "bmc-reset-default", "cmos-reset-immediate",
        and "diagnostic-interrupt"
        '''
        if force:
            print 'Rebooting server %s' % self.ipaddress
            command_string = '''<configConfMo cookie="%s" dn="sys/rack-unit-1" inHierarchical="false">\
            <inConfig>\
            <computeRackUnit dn="sys/rack-unit-1" adminPower="cycle-immediate"></computeRackUnit>
            </inConfig>\
            </configConfMo>''' % self.session_cookie
            response_element = post_request(self, command_string)
            return response_element
        else:
            print 'reboot() must be called with "force=True" to reboot the server'

    def refresh(self):
        '''
        XML Query:
            <aaaRefresh cookie="<real_cookie>" inCookie="<real_cookie>" inName='admin' inPassword='password'> </aaaRefresh>
        '''
        command_string = "<aaaRefresh cookie='%s' inCookie='%s' inName='%s' inPassword='%s'></aaaRefresh>" %\
                         (self.session_cookie, self.session_cookie, self.username, self.password)
        try:
            response_element = post_request(self, command_string)
            return True
        except SyntaxError as e:
            print 'refresh() post_request returned error:', e
            return False

    @timeit
    def get_all_info(self):
        try:
            command_string = '<configResolveChildren cookie="%s" inHierarchical="true" inDn="sys/rack-unit-1"/>' % self.session_cookie
            response_element = post_request(self, command_string)
            return response_element
        except PostException as e:
            print 'pycimc.get_chassis_info: post_request returned error:', e
            return False


    @timeit
    def get_chassis_info(self):
        chassis_dict = {}
        try:
            command_string = '<configResolveClass cookie="%s" inHierarchical="false" classId="computeRackUnit"/>' % self.session_cookie
            response_element = post_request(self, command_string)
            for key,value in response_element.find('.//computeRackUnit').items():
                chassis_dict[key] = value
            self.inventory['chassis'] = chassis_dict
            self.serial_no = self.inventory['chassis']['serial']
            self.model = self.inventory['chassis']['model']
            self.total_memory = self.inventory['chassis']['totalMemory']
            self.name = self.inventory['chassis']['name']
            return True
        except PostException as e:
            print 'pycimc.get_chassis_info: post_request returned error:', e
            return False

    @timeit
    def get_boot_order(self):
        try:
            command_string = '<configResolveChildren cookie="%s" inHierarchical="false" inDn="sys/rack-unit-1/boot-policy"/>' % self.session_cookie
            response_element = post_request(self, command_string)
            out_configs = response_element.find('outConfigs')
            for config in out_configs.getchildren():
                print config.tag,':',config.attrib
        except PostException as e:
            print 'pycimc.get_chassis_info: post_request returned error:', e
            return False

    @timeit
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
                response_element = post_request(self, command)
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

    @timeit
    def get_eth_settings(self):
        '''
        Query the adaptorHostEthIf class to get all VIC settings on the server
        [TODO] Populate <instance>.vic_settings with the resulting dictionary
        adaptorHostEthIf : {'dn': 'sys/rack-unit-1/adaptor-2/host-eth-eth0', 'ifType': 'virtual', 'name': 'eth0', 'iscsiBoot': 'disabled', 'pxeBoot': 'enabled', 'mtu': '1500', 'mac': 'A8:0C:0D:DC:7B:8F', 'channelNumber': 'N/A', 'classOfService': '0', 'portProfile': 'N/A', 'usnicCount': '0', 'uplinkPort': '0'}
        adaptorHostEthIf : {'dn': 'sys/rack-unit-1/adaptor-2/host-eth-eth1', 'ifType': 'virtual', 'name': 'eth1', 'iscsiBoot': 'disabled', 'pxeBoot': 'enabled', 'mtu': '1500', 'mac': 'A8:0C:0D:DC:7B:90', 'channelNumber': 'N/A', 'classOfService': '0', 'portProfile': 'N/A', 'usnicCount': '0', 'uplinkPort': '1'}
        adaptorHostEthIf : {'dn': 'sys/rack-unit-1/adaptor-5/host-eth-eth0', 'ifType': 'virtual', 'name': 'eth0', 'iscsiBoot': 'disabled', 'pxeBoot': 'enabled', 'mtu': '1500', 'mac': 'A8:0C:0D:DC:21:35', 'channelNumber': 'N/A', 'classOfService': '0', 'portProfile': 'N/A', 'usnicCount': '0', 'uplinkPort': '0'}
        adaptorHostEthIf : {'dn': 'sys/rack-unit-1/adaptor-5/host-eth-eth1', 'ifType': 'virtual', 'name': 'eth1', 'iscsiBoot': 'disabled', 'pxeBoot': 'enabled', 'mtu': '1500', 'mac': 'A8:0C:0D:DC:21:36', 'channelNumber': 'N/A', 'classOfService': '0', 'portProfile': 'N/A', 'usnicCount': '0', 'uplinkPort': '1'}
        '''

        adaptorHostEthIf_list = []
        try:
            command_string = '<configResolveClass cookie="%s" inHierarchical="false" classId="adaptorHostEthIf"/>' % self.session_cookie
            response_element = post_request(self, command_string)
            out_configs = response_element.find('outConfigs')
            for config in out_configs.getchildren():
                adaptorHostEthIf_list.append(config.attrib)
            self.adaptor_host_eth_list = adaptorHostEthIf_list
        except PostException as e:
            print 'pycimc.get_eth_settings: post_request returned error:', e
            return False

        '''
        Query the pciEquipSlot class to get all PCI cards
        pciEquipSlot : {'dn': 'sys/rack-unit-1/equipped-slot-2', 'smbiosId': '2', 'controllerReported': '2', 'vendor': '0x1137', 'model': 'UCS VIC 1225 10Gbps 2 port CNA SFP+', 'id': '2'}
        pciEquipSlot : {'dn': 'sys/rack-unit-1/equipped-slot-4', 'smbiosId': '4', 'controllerReported': '4', 'vendor': '0x1000', 'model': 'LSI 9271-8i MegaRAID SAS HBA', 'id': '4'}
        pciEquipSlot : {'dn': 'sys/rack-unit-1/equipped-slot-5', 'smbiosId': '5', 'controllerReported': '5', 'vendor': '0x1137', 'model': 'UCS VIC 1225 10Gbps 2 port CNA SFP+', 'id': '5'}
        '''

        pciEquipSlot_list = []
        try:
            command_string = '<configResolveClass cookie="%s" inHierarchical="false" classId="pciEquipSlot"/>' % self.session_cookie
            response_element = post_request(self, command_string)
            out_configs = response_element.find('outConfigs')
            for config in out_configs.getchildren():
                pciEquipSlot_list.append(config.attrib)
            self.pci_slot_list = pciEquipSlot_list
        except PostException as e:
            print 'pycimc.get_eth_settings: post_request returned error:', e
            return False


    @timeit
    def get_bios_settings(self):
        '''
        Query the firmwareRunning class to get all FW versions on the server
        Populate <instance>.bios_settings with the resulting dictionary
        '''

        bios_dict = {}
        command_string = '<configResolveClass cookie="%s" inHierarchical="true" classId="biosSettings"/>' % self.session_cookie
        url = "https://%s/nuova" % self.ipaddress
        try:
            response_element = post_request(self,command_string)
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
        for item in custom_bios_settings:
            command_string += configConfMo_template.format(item=item)
        command_string += configConfMo_append_string

        try:
            response_element = post_request(self, command_string)
            return True
        except SyntaxError as e:
            print 'post_request returned error:', e
            return False

    @timeit
    def get_fw_versions(self):
        '''
        Query the firmwareRunning class to get all FW versions on the server
        Populate <instance>.fw_running with the resulting dictionary
        '''
        fw_dict = {}
        command_string = '<configResolveClass cookie="%s" inHierarchical="false" classId="firmwareRunning"/>' % self.session_cookie
        try:
            response_element = post_request(self,command_string)
            for i in response_element.iter('firmwareRunning'):
                fw_dict[i.attrib['dn']] = i.attrib['version']
            self.inventory['fw'] = fw_dict
            return True
        except PostException as e:
            print 'pycimc.get_fw_versions:', e
            return False
        except TimeoutException as e:
            print 'pycimc.get_fw_version:', e
            return False

def post_request(server, command_string):
    url = "https://%s/nuova" % server.ipaddress
    try:
        response = ET.fromstring(requests.post(url, data=command_string, verify=False, timeout=REQUEST_TIMEOUT).text)
        #print 'response.attrib:', response.attrib
        # Check if the response has an 'errorCode' key if something went wrong
        # if so, then print the error message and raise an exception
        if 'errorCode' in response.keys():
            print 'command:', command_string
            print 'response.attrib:', response.attrib
            raise SyntaxError("'%s': '%s'" % (response.attrib['errorCode'], response.attrib['errorDescr']))
        else:
            return response
    except requests.exceptions.Timeout:
        raise TimeoutException('pycimc.post_request() to %s timed out' % server.ipaddress)
    except Exception as e:
        raise PostException('pycimc.post_request() raised Exception:', e)

class PostException(Exception):
    pass

class TimeoutException(Exception):
    pass


if __name__ == "__main__":
    IPADDR = '69.134.77.28'
    USERNAME = 'admin'
    PASSWORD = 'password'

    myserver = UcsServer(IPADDR,USERNAME,PASSWORD)

    myserver.login()
    result = myserver.get_all_info()

    #myserver.get_chassis_info()
    #myserver.get_drive_inventory()
    #myserver.get_fw_versions()
    #myserver.get_eth_settings()

    myserver.logout()
