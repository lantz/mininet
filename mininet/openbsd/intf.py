"""
A interface object that relies on ifconfig(8) to manipulate network
interfaces and devices.
"""
from mininet.baseintf import BaseIntf

class Intf( BaseIntf ):
    """Interface objects that use 'ifconfig' to configure the underlying
    interface that it represents"""

    index=0    # pair(4) index

    def __init__( self, name, node=None, port=None, link=None,
                  mac=None, **params ):
        self.realname = params[ 'orgName' ]
        BaseIntf.__init__( self, name, node=node, port=port, link=link,
                           mac=mac, **params )

    def ifconfig( self, *args ):
        "Configure ourselves using ifconfig"
        o, err, ext = self.node.pexec( 'ifconfig', self.realname, *args )
        if not err:
            return o
        return err


    def setMAC( self, macstr ):
        self.mac = macstr
        return self.ifconfig( 'lladdr', macstr )

    def rename( self, newname ):
        """
        Rename interface. We retain the real name of the interface as
        self.realname since interfaces can't be renamed.
        """
        if self.name in self.node.portNames:
            del self.node.portNames[ self.name ]
        self.node.portNames[ newname ] = self.realname
        self.name = newname
        return newname

    def delete( self ):
        "Delete interface"
        if self.name in self.node.portNames:
            del self.node.portNames[ self.name ]
        self.node.delIntf( self )
        self.link = None

    def status( self ):
        "Return intf status as a string"
        links, _err, _result = self.node.pexec( 'ifconfig pair' )
        if self.realname + ':' in links:
            return "OK"
        else:
            return "MISSING"

    def realName( self ):
        """
        Pretend that the interface name has changed, but retain
        the real name so we can actually configure the interface
        """
        return self.realname

    @classmethod
    def next( cls ):
	idx = Intf.index
	Intf.index += 1
        return idx 
