"""
Node: rdomain(4) based node. This is somewhat more similar to Linux's network
namespace moreso than a jail since it creates a separate network address space
only.

Mininet 'hosts' are created by running shells within rdomains. Links are made of
pair(4)s patched together.

This is a collection of helpers that call the right commands to manipulate these
components.
"""
import signal
import re
from os import killpg

from subprocess import PIPE, Popen
from mininet.basenode import BaseNode
from mininet.log import debug, info, warn
from mininet.util import quietRun

from mininet.openbsd.util import moveIntf
from mininet.openbsd.intf import Intf

class Node( BaseNode ):
    """A virtual network node that manipulates and tracks rdomains. Because of
       the property of rdomains, an OpenBSD node will always come with at least
       one pair interface if inNamespace=True."""

    index=1     # rdomain ID, can only go to 255

    def __init__( self, name, inNamespace=True, **params ):
        BaseNode.__init__( self, name, inNamespace, **params )
        # No renaming, supply map of assigned interface names to real names
        self.portNames = {}

    def getShell( self, master, slave, mnopts=None ):
        """
        Starts a shell used by the node to run commands. If inNamespace=True,
        a pair interface is created, assigned to an rdomain, and a shell is
        exec'd in the rdomain.
        """
        #execcmd = [ 'mnexec' ]
        #opts = '-cd' if mnopts is None else mnopts

        if self.inNamespace:
            # create the pair tied to an rdomain
            self.pair, self.rdid = 'pair%d' % Intf.next(), Node.index
            Node.index += 1
            if Node.index == 256:
                error( 'Exceeded supported number of hosts (255)' )
                exit( 1 )
            rcmd = [ 'ifconfig', self.pair, 'create', 'description',
                     '"%s"' % self.name, 'rdomain', '%d' % self.rdid ]
            #execcmd = [ 'route', '-T%d' % self.rdid, 'exec' ] + execcmd
            Popen( rcmd, stdout=PIPE )
        else:
            self.pair = None
            self.rdid = None

        # bash -i: force interactive
        # -s: pass $* to shell, and make process easy to find in ps. The prompt
        # is set to sentinel chr( 127 )
        #cmd = execcmd + [ opts, 'env', 'PS1=' + chr( 127 ), '/bin/sh', '-is',
        #                  'mininet:' + self.name ]

        #return Popen( cmd, stdin=slave, stdout=slave, stderr=slave,
        #              close_fds=False )
        return None

    def mountPrivateDirs( self ):
        "mount private directories"
        # **Not applicable until further notice**
        pass
        # Avoid expanding a string into a list of chars
        #assert not isinstance( self.privateDirs, basestring )
        #for directory in self.privateDirs:
        #    if isinstance( directory, tuple ):
        #        # mount given private directory onto mountpoint
        #        mountPoint = directory[ 1 ] % self.__dict__
        #        privateDir = directory[ 0 ]
        #        diffDir = mountPoint + '_diff'
        #        quietRun( 'mkdir -p %s %s %s' %
        #                       ( privateDir, mountPoint, diffDir ) )
        #        quietRun( 'mount -t nullfs %s %s' % ( privateDir, mountPoint ) )
        #        quietRun( 'mount -t unionfs %s %s' % ( diffDir, mountPoint ) )
        #    else:
        #        # mount temporary filesystem on directory + name
        #        quietRun( 'mkdir -p %s' % directory + self.name )
        #        quietRun( 'mount -n -t tmpfs tmpfs %s' % directory + self.name )

    def unmountPrivateDirs( self ):
        "mount private directories -  overridden"
        # **Not applicable until further notice**
        pass
        #for directory in self.privateDirs:
        #    # all ops are from prison0
        #    if isinstance( directory, tuple ):
        #        quietRun( 'umount %s' % directory[ 1 ] % self.__dict__ )
        #        quietRun( 'umount %s' % directory[ 1 ] % self.__dict__ )
        #    else:
        #        quietRun( 'umount %s' % directory + self.name )

    def terminate( self ):
        """ Cleanup when node is killed.  """
        #self.unmountPrivateDirs()
        if self.rdid:
            Popen( [ 'ifconfig', self.pair, 'destroy' ] )
        if self.shell:
            if self.shell.poll() is None:
                killpg( self.shell.pid, signal.SIGHUP )
        self.cleanup()

    def popen( self, *args, **kwargs ):
        """Return a Popen() object in our namespace
           args: Popen() args, single list, or string
           kwargs: Popen() keyword args"""
        defaults = { 'stdout': PIPE, 'stderr': PIPE,
                     'mncmd':
                     [ 'route', '-T%d' % self.rdid, 'exec' ] if self.rdid else
                     [ 'mnexec', '-d' ] }
        defaults.update( kwargs )
        if len( args ) == 1:
            if isinstance( args[ 0 ], list ):
                # popen([cmd, arg1, arg2...])
                cmd = args[ 0 ]
            elif isinstance( args[ 0 ], basestring ):
                # popen("cmd arg1 arg2...")
                cmd = args[ 0 ].split()
            else:
                raise Exception( 'popen() requires a string or list' )
        elif len( args ) > 0:
            # popen( cmd, arg1, arg2... )
            cmd = list( args )
        # Attach to our namespace  using mnexec -a
        cmd = defaults.pop( 'mncmd' ) + cmd
        # Shell requires a string, not a list!
        if defaults.get( 'shell', False ):
            cmd = ' '.join( cmd )
        popen = self._popen( cmd, **defaults )
        return popen

    def sendInt( self, intr=chr( 3 ) ):
        "Interrupt running command."
        quietRun( "pkill -2 -f -- '%s'" % self.lastCmd )

    def setHostRoute( self, ip, intf ):
        """Add route to host.
           ip: IP address as dotted decimal
           intf: string, interface name
           intfs: interface map of names to Intf"""
        # add stronger checks for interface lookup
        cmd = 'route -T%s add -host %s %s'
        quietRun( cmd % ( self.rdid, ip, self.intfs( intf ).IP() ) )

    def setDefaultRoute( self, intf=None ):
        """Set the default route to go through intf.
           intf: Intf or {dev <intfname> via <gw-ip> ...}"""
        # Note setParam won't call us if intf is none
        if isinstance( intf, basestring ):
            argv = intf.split(' ')
            if 'via' not in argv[ 0 ]:
                warn( '%s: setDefaultRoute takes a port name but we got: %s\n' %
                      ( self.name, intf ) )
                return
            params = argv[ -1 ]
        else:
            params = intf.IP()
        quietRun( 'route -T%d change default %s' % ( self.rdid, params ) )


    def addIntf( self, intf, port=None, moveIntfFn=moveIntf ):
        self.portNames[ intf.name ] = intf.realname
        super( Node, self ).addIntf( intf, port, moveIntfFn )

    def cmd( self, *args, **kwargs ):
        """Send a command, wait for output, and return it. At this time this
           does not allow CLI commands from the host, e.g. 'h1 ping h2'.
           cmd: string"""
        from mininet.clean import sh
        verbose = kwargs.get( 'verbose', False )
        log, kwargs[ 'echo' ] = info, True if verbose else debug
        if self.rdid:
            cmd = 'route -T%d exec ' % self.rdid + " ".join( args )
            return sh( cmd )
        else:
            return sh( " ".join( args ) )
