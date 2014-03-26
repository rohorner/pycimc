__author__ = 'Rob Horner (robert@horners.org)'

import pexpect
import sys
from time import sleep

COMMAND_PROMPT = '[$#] '
MORE_PROMPT = '--More--'


def login(host, user, password):
    child = pexpect.spawn('ssh -l %s %s'%(user, host))
    fout = file('mylog.txt','w')
    child.logfile_send = fout
    child.logfile_read = sys.stdout

    i = child.expect([pexpect.TIMEOUT, '[Pp]assword: '])
    if i == 0: # Timeout
        print('ERROR!')
        print('SSH could not login. Here is what SSH said:')
        print(child.before, child.after)
        sys.exit (1)
    child.sendline(password)
    # Now we are either at the command prompt or
    # the login process is asking for our terminal type.
    i = child.expect (['Permission denied', COMMAND_PROMPT])
    if i == 0:
        print('Permission denied on host:', host)
        sys.exit (1)
    elif i == 1:
        return child

def logout(child):
    child.sendline('top')
    child.expect_exact('# ')
    child.sendline('exit')

def remove_virtualdrives(child, vd_list, slot):
    child.sendline('top')
    child.sendline('scope chassis')
    child.expect_exact('/chassis # ')
    child.sendline('scope storageadapter '+slot)
    child.expect_exact('/chassis/storageadapter # ')
    child.sendline('clear-foreign-config')
    child.expect_exact("Enter 'yes' to confirm -> ")
    child.sendline('yes')
    #child.sendline('show virtual-drive')
    #child.expect_exact('/chassis/storageadapter # ')

    for vd in vd_list:
        child.expect_exact('/chassis/storageadapter # ')
        child.sendline('scope virtual-drive %s' % vd)
        child.expect_exact('/chassis/storageadapter/virtual-drive #')
        child.sendline('delete-virtual-drive')
        child.expect_exact("Enter 'yes' to confirm -> ")
        child.sendline('yes')
        child.expect_exact('/chassis/storageadapter/virtual-drive # ')
        child.sendline('top')
        child.expect_exact('# ')
        child.sendline('scope chassis')
        child.expect_exact('/chassis # ')
        child.sendline('scope storageadapter SLOT-4')


def create_virtualdrives(child, pd, slot):
    child.sendline('top')
    child.expect_exact('# ')
    child.sendline('scope chassis')
    child.expect_exact('/chassis # ')
    child.sendline('scope storageadapter '+slot)
    child.expect_exact('/chassis/storageadapter # ')
    #child.sendline('show virtual-drive')
    #child.expect_exact('/chassis/storageadapter # ')

    child.sendline('create-virtual-drive')
    child.expect_exact('--> ')
    child.sendline(pd['raid_level'])
    child.expect_exact('Enter comma-separated PDs from above list--> ')
    child.sendline(pd['id'])
    child.expect_exact('(15 characters maximum)--> ')
    child.sendline(pd['name'])
    child.expect_exact("Example format: '400 GB' --> ")
    child.sendline(pd['size'])
    child.expect_exact('OK? (y or n)--> ')
    child.sendline('y')
    child.expect_exact('OK? (y or n)--> ')
    child.sendline('y')

def logout(child):
    child.expect('# ')
    child.sendline('exit')


def modify_drives(ipaddr, username, password, vd_list, pd_list, slot):
    child = login(ipaddr, username, password)
    #print child.__dict__
    child.sendline('top')
    child.sendline('scope chassis')
    child.expect('/chassis # ')
    child.sendline('scope storageadapter '+slot)
    child.expect('/chassis/storageadapter # ')
    child.sendline('show virtual-drive')
    child.expect(COMMAND_PROMPT)
    # remove all existing VDs
    if len(vd_list) > 0:
        remove_virtualdrives(vd_list)
    # Create new RAID VDs from existing physical drives
    if len(pd_list) > 0:
        create_virtualdrives(pd_list)
    child.send('top' )
    child.expect('# ')
    child.sendline('exit')


if __name__ == '__main__':
    child = login(IPADDR, USERNAME, PASSWORD)
    #print child.__dict__
    child.sendline('top')
    child.sendline('scope chassis')
    child.expect('/chassis # ')
    child.sendline('scope storageadapter SLOT-MEZZ')
    child.expect('/chassis/storageadapter # ')
    child.sendline('show virtual-drive')
    child.expect(COMMAND_PROMPT)
    # remove all existing VDs
    if len(vd_list) > 0:
        remove_virtualdrives(vd_list)
    # Create new RAID VDs from existing physical drives
    if len(pd_list) > 0:
        create_virtualdrives(pd_list)
    child.send('top' )
    child.expect('# ')
    child.sendline('exit')
