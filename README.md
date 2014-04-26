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

It can also create new virtual drives (via pexpect) and set BIOS values.

The examples directory has a few samples of how to use the library. 'threaded_get_inventory' uses multithreading to query lots of servers simultaneously.

To install, do the typical 'python setup.py install'

cimc
====

As an example of how to use the library, I've created a 'cimc' CLI app that will return a json data structure of the requested inventory. It's located in the examples directory.

```
rohorner$ ./cimc 192.168.200.100 -u admin -p password --get-pci-inventory
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
