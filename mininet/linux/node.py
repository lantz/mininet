"""
A node implementing platform-specifics for various Linux distros.

Mininet 'hosts' are shells running within network and filesystem namespaces.
Links are veth device pairs (see ip link(8)). 

This is a collection of helpers that call the right commands to manipulate these
components.
"""
from subprocess import PIPE, Popen
from mininet.util import quietRun

class Node( BaseNode ):
    """A virtual network node that manipulates and tracks namespaces."""

    def __init__( self, name, inNamespace=True, **params ):
        BaseNode.__init__( self, name, inNamespace, **params )

    def getShell( self, master, slave, mnopts=None ):
        """
        Starts a shell used by the node to run commands. If inNamespace=True,
        then a shell is started in a network namespace. Otherwise it just starts
        a shell.
        """
        # mnexec: (c)lose descriptors, (d)etach from tty,
        # (p)rint pid, and run in (n)amespace
        opts = '-cd' if mnopts is None else mnopts
        if self.inNamespace:
            opts += 'n'
        # bash -i: force interactive
        # -s: pass $* to shell, and make process easy to find in ps
        # prompt is set to sentinel chr( 127 )
        cmd = [ 'mnexec', opts, 'env', 'PS1=' + chr( 127 ),
                'bash', '--norc', '-is', 'mininet:' + self.name ]

        return Popen( cmd, stdin=slave, stdout=slave, stderr=slave,
                      close_fds=False )

    def mountPrivateDirs( self ):
        "mount private directories"
        # Avoid expanding a string into a list of chars
        assert not isinstance( self.privateDirs, basestring )
        for directory in self.privateDirs:
            if isinstance( directory, tuple ):
                # mount given private directory
                privateDir = directory[ 1 ] % self.__dict__
                mountPoint = directory[ 0 ]
                self.cmd( 'mkdir -p %s' % privateDir )
                self.cmd( 'mkdir -p %s' % mountPoint )
                self.cmd( 'mount --bind %s %s' %
                               ( privateDir, mountPoint ) )
            else:
                # mount temporary filesystem on directory
                self.cmd( 'mkdir -p %s' % directory )
                self.cmd( 'mount -n -t tmpfs tmpfs %s' % directory )

    def unmountPrivateDirs( self ):
        "mount private directories -  overridden"
        for directory in self.privateDirs:
            if isinstance( directory, tuple ):
                self.cmd( 'umount ', directory[ 0 ] )
            else:
                self.cmd( 'umount ', directory )

    def terminate( self ):
        """ Cleanup when node is killed.  """
        self.unmountPrivateDirs()
        if self.shell:
            if self.shell.poll() is None:
                os.killpg( self.shell.pid, signal.SIGHUP )
        self.cleanup()

    def popen( self, *args, **kwargs ):
        """Return a Popen() object in our namespace
           args: Popen() args, single list, or string
           kwargs: Popen() keyword args"""
        defaults = { 'stdout': PIPE, 'stderr': PIPE,
                     'mncmd': [ 'mnexec', '-da', str( self.pid ) ] }
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
        debug( 'sendInt: writing chr(%d)\n' % ord( intr ) )
        self.write( intr )

    def setHostRoute( self, ip, intf ):
        """Add route to host.
           ip: IP address as dotted decimal
           intf: string, interface name
           intfs: interface map of names to Intf"""
        # add stronger checks for interface lookup
        self.cmd( 'route add -host %s dev %s' % ( ip, intf ) )
     
    def setDefaultRoute( self, intf=None ):
        """Set the default route to go through intf.
           intf: Intf or {dev <intfname> via <gw-ip> ...}"""
        # Note setParam won't call us if intf is none
        if isinstance( intf, basestring ) and ' ' in intf:
            params = intf
        else:
            params = 'dev %s' % intf
        # Do this in one line in case we're messing with the root namespace
        self.cmd( 'route del default; route add default %s' % params )


class Intf( BaseIntf ):
    """Interface objects that use 'ip' and 'ifconfig' to configure the
    underlying interface that it represents"""

    def setMAC( self, macstr ):
        self.mac = macstr
        return ( self.ifconfig( 'down' ) +
                 self.ifconfig( 'hw', 'ether', macstr ) +
                 self.ifconfig( 'up' ) )

    def rename( self, newname ):
        "Rename interface"
        self.ifconfig( 'down' )
        result = self.cmd( 'ip link set', self.name, 'name', newname )
        self.name = newname
        self.ifconfig( 'up' )

    def delete( self ):
        "Delete interface"
        self.cmd( 'ip link del ' + self.name )
        # We used to do this, but it slows us down:
        # if self.node.inNamespace:
        # Link may have been dumped into root NS
        # quietRun( 'ip link del ' + self.name )
        self.node.delIntf( self )
        self.link = None

        return result

    def status( self ):
        "Return intf status as a string"
        links, _err, _result = self.node.pexec( 'ip link show' )
        if self.name in links:
            return "OK"
        else:
            return "MISSING"
