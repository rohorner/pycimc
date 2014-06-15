pycimc
======

A python interface to Cisco's UCS CIMC

pycimc is a simple library to access Cisco's UCS XML API to 
In its current state it can grab inventory for
- physical and virtual drives
- BIOS settings
- FW versions
- PCI/VIC/vNIC associations
- users
- boot order
- general chassis info

Version 2.x of UCS firmware allows for creating and modifying virtual drives through the XML interface. See "create_raid_drives.py" in the examples directory.

The examples directory has a few samples of how to use the library. 'multi_get_inventory' uses multithreading to query lots of servers simultaneously. You'll almost certainly want to do this in a large data center environment, as the XMLAPI in the CIMC is fairly slow and processor-constrained, taking about 6-8 seconds for a typical query.

###Installation
To install, do the typical 'python setup.py install'

###cimc

As an example of how to use the library, I've created a 'cimc' CLI app that will return a json data structure of the requested inventory. It's located in the examples directory. Run 'cimc --help' to see all of the subsystem info that can be pulled from the server.

```
rohorner$ ./cimc -i 192.168.200.100 pci
[
  {
    "dn": "sys/rack-unit-1/equipped-slot-L", 
    "smbiosId": "L", 
    "version": "0x80000AA4-1.446.1", 
    "vendor": "0x8086", 
    "controllerReported": "L", 
    "model": "Intel(R) I350 1 Gbps Network Controller", 
    "id": "L"
  }, 
  {
    "dn": "sys/rack-unit-1/equipped-slot-1", 
    "smbiosId": "1", 
    "version": "2.2(1.210)", 
    "vendor": "0x1137", 
    "controllerReported": "1", 
    "model": "UCS VIC 1225 10Gbps 2 port CNA SFP+", 
    "id": "1"
  }, 
  {
    "dn": "sys/rack-unit-1/equipped-slot-2", 
    "smbiosId": "2", 
    "version": "N/A", 
    "vendor": "0x1000", 
    "controllerReported": "2", 
    "model": "LSI 9266-8i MegaRAID SAS HBA", 
    "id": "2"
  }
]
```
