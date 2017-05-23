"""
Mininet Cleanup
author: Bob Lantz (rlantz@cs.stanford.edu)

Unfortunately, Mininet and OpenFlow (and the Linux kernel)
don't always clean up properly after themselves. Until they do
(or until cleanup functionality is integrated into the Python
code), this script may be used to get rid of unwanted garbage.
It may also get rid of 'false positives', but hopefully
nothing irreplaceable!
"""
from os import uname
from subprocess import ( Popen, PIPE, check_output as co,
                         CalledProcessError )
import time

from mininet.log import info
from mininet.term import cleanUpScreens

def sh( cmd ):
    "Print a command and send it to the shell"
    info( cmd + '\n' )
    return Popen( [ '/bin/sh', '-c', cmd ], stdout=PIPE ).communicate()[ 0 ]

def _coPids( pattern ):
    try:
        return co( [ 'pgrep', '-f', pattern ] )
    except CalledProcessError:
        return ''

def _popenPids( pattern ):
    try:
        p1 = Popen( [ 'ps' ], stdout=PIPE )
        pids = co( [ 'awk', '/%s/{print $1}' % pattern ], stdin=p1.stdout )
        p1.stdout.close()
        return pids
    except CalledProcessError:
        return ''

def killprocs( pidsFunc, pattern ):
    "Reliably terminate processes matching a pattern (including args)"
    sh( 'pkill -9 -f %s' % pattern )
    # Make sure they are gone
    while True:
        pids = pidsFunc( pattern )
        if pids:
            sh( 'pkill -9 -f %s' % pattern )
            time.sleep( .5 )
        else:
            break

def killnodes( pidsFunc, pattern='[m]ininet' ):
    "kill processes representing nodes"
    killprocs( pidsFunc, pattern )
    nodes = sh( 'jls name' ).split('\n')
    for node in nodes:
        if 'mininet:' in node:
            sh( 'jail -r %s 2>/dev/null' % node )

def _iplinkClean( listCmd=None ):
    """ link cleanup using 'ip link' """
    links = sh( "ip link show | "
                "egrep -o '([-_.[:alnum:]]+-eth[[:digit:]]+)'"
                ).splitlines()
    # Delete blocks of links
    n = 1000  # chunk size
    for i in range( 0, len( links ), n ):
        cmd = ';'.join( 'ip link del %s' % link
                         for link in links[ i : i + n ] )
        sh( '( %s ) 2> /dev/null' % cmd )

    if 'tap9' in sh( 'ip link show' ):
        info( "*** Removing tap9 - assuming it's from cluster edition\n" )
        sh( 'ip link del tap9' )

def _ifcfgClean( listCmd ):
    """ link cleanup with 'ifconfig'"""
    links = sh( listCmd ).splitlines()
    # Delete blocks of links
    n = 1000  # chunk size
    for i in range( 0, len( links ), n ):
        cmd = ';'.join( 'ifconfig %s destroy' % link
                         for link in links[ i : i + n ] )
        sh( '( %s ) 2> /dev/null' % cmd )

    if 'tap9' in sh( 'ifconfig' ):
        info( "*** Removing tap9 - assuming it's from cluster edition\n" )
        sh( 'ifconfig tap9 destroy' )

def _ifcfgCleanLo( listCmd ):
    """ link cleanup with 'ifconfig' that assumes formattable listCmd
        that takes an interface unit name (see args for OpenBSD)"""
    _ifcfgClean( listCmd % 'pair' )
    los = sh( listCmd % 'lo' )
    n = 256  # chunk size - can only have 256 max, per rdomain(4)
    for i in range( 1, len( los ), n ):
        cmd = ';'.join( 'ifconfig %s destroy' % lo
                         for lo in los[ i : i + n ] )
        sh( '( %s ) 2> /dev/null' % cmd )


platform = uname()[ 0 ]
if platform == 'FreeBSD':
    cleanLinks = _ifcfgClean
    args       = "ifconfig -l | egrep -o '([-_.[:alnum:]]+-eth[[:digit:]]+)'"
    pidsFunc   = _popenPids
    cleanNodes = killnodes
elif platform == 'Linux':
    cleanLinks, args = _iplinkClean, None
    pidsFunc   = _coPids
    cleanNodes = killprocs
else: # OpenBSD
    cleanLinks = _ifcfgCleanLo
    args = "ifconfig %s | sed -n 's|\(^[a-z]\{1,\}[0-9]\{1,\}\):.*|\\1| p'"
    pidsFunc   = _coPids
    cleanNodes = killprocs


class Cleanup( object ):
    "Wrapper for cleanup()"

    callbacks = []

    @classmethod
    def cleanup( cls):
        """Clean up junk which might be left over from old runs;
           do fast stuff before slow dp and link removal!"""

        info( "*** Removing excess controllers/ofprotocols/ofdatapaths/"
              "pings/noxes\n" )
        zombies = ( 'controller ofprotocol ofdatapath ping nox_core'
                    'lt-nox_core ovs-openflowd ovs-controller'
                    'ovs-testcontroller udpbwtest mnexec ivs ryu-manager' )
        # Note: real zombie processes can't actually be killed, since they
        # are already (un)dead. Then again,
        # you can't connect to them either, so they're mostly harmless.
        # Send SIGTERM first to give processes a chance to shutdown cleanly.
        sh( 'killall ' + zombies + ' 2> /dev/null' )
        time.sleep( 1 )
        sh( 'killall -9 ' + zombies + ' 2> /dev/null' )

        # And kill off sudo mnexec
        sh( 'pkill -9 -f "sudo mnexec"')

        info( "*** Removing junk from /tmp\n" )
        sh( 'rm -f /tmp/vconn* /tmp/vlogs* /tmp/*.out /tmp/*.log' )

        info( "*** Removing old X11 tunnels\n" )
        cleanUpScreens()

        info( "*** Removing excess kernel datapaths\n" )
        dps = sh( "ps ax | egrep -o 'dp[0-9]+' | sed 's/dp/nl:/'"
                  ).splitlines()
        for dp in dps:
            if dp:
                sh( 'dpctl deldp ' + dp )

        info( "***  Removing OVS datapaths\n" )
        dps = sh("ovs-vsctl --timeout=1 list-br").strip().splitlines()
        if dps:
            sh( "ovs-vsctl " + " -- ".join( "--if-exists del-br " + dp
                                            for dp in dps if dp ) )
        # And in case the above didn't work...
        dps = sh( "ovs-vsctl --timeout=1 list-br" ).strip().splitlines()
        for dp in dps:
            sh( 'ovs-vsctl del-br ' + dp )

        info( "*** Removing all links of the pattern foo-ethX\n" )
        cleanLinks( args )

        info( "*** Killing stale mininet node processes\n" )
        cleanNodes( pidsFunc, '[m]ininet:' )

        info( "*** Shutting down stale tunnels\n" )
        killprocs( pidsFunc, '[T]unnel=Ethernet' )
        killprocs( pidsFunc, '.ssh\/mn' )
        sh( 'rm -f ~/.ssh/mn/*' )

        # Call any additional cleanup code if necessary
        for callback in cls.callbacks:
            callback()

        info( "*** Cleanup complete.\n" )

    @classmethod
    def addCleanupCallback( cls, callback ):
        "Add cleanup callback"
        if callback not in cls.callbacks:
            cls.callbacks.append( callback )


cleanup = Cleanup.cleanup
addCleanupCallback = Cleanup.addCleanupCallback
