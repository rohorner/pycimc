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

THIS IS A WORK IN PROCESS. IT ALMOST CERTAINLY WON'T WORK WITHOUT SOME CODE TWEAKS

To install, do the typical 'python setup.py install'
