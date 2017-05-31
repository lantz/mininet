Mininet: Rapid Prototyping for Software Defined Networks
========================================================

Fork of Mininet 2.3.0d1

*This is a heavily refactored version of Mininet that also supports
FreeBSD and OpenBSD, and is aimed to make it easier to add support for
non-Linux systems. As such, the native install instructions are
slightly different. This is also a heavy work-in-progress so things
may be broken or unsupported.*


### What is Mininet?

Mininet emulates a complete network of hosts, links, and switches
on a single machine.  To create a sample two-host, one-switch network,
just run:

  `sudo mn`

Mininet is useful for interactive development, testing, and demos,
especially those using OpenFlow and SDN.  OpenFlow-based network
controllers prototyped in Mininet can usually be transferred to
hardware with minimal changes for full line-rate execution.


### Features

*Different platform ports support varying subsets of the base (Linux)
version described below. Refer to the documentation/notes for each
platform for the specifics.*

Mininet includes:

* A command-line launcher (`mn`) to instantiate networks.

* A handy Python API for creating networks of varying sizes and
  topologies.

* Examples (in the `examples/` directory) to help you get started.

* Full API documentation via Python `help()` docstrings, as well as
  the ability to generate PDF/HTML documentation with `make doc`.

* Parametrized topologies (`Topo` subclasses) using the Mininet
  object.  For example, a tree network may be created with the
  command:

  `mn --topo tree,depth=2,fanout=3`

* A command-line interface (`CLI` class) which provides useful
  diagnostic commands (like `iperf` and `ping`), as well as the
  ability to run a command to a node. For example,

  `mininet> h11 ifconfig -a`

  tells host h11 to run the command `ifconfig -a`

* A "cleanup" command to get rid of junk (interfaces, processes, files
  in /tmp, etc.) which might be left around by Mininet or Linux. Try
  this if things stop working!

  `mn -c`

   (Note: this is a fairly blunt command that may remove non-Mininet
    related things)


### Installation

If you are using a Linux, see `INSTALL` for installation instructions
and details. If you are using FreeBSD, see `INSTALL.FreeBSD`. On
OpenBSD, `./configure` followed by `./util/install.sh -a` should be
all that is required.


### De-Installation

The FreeBSD and OpenBSD ports come with an 'uninstall' feature that
removes the Mininet core libraries and related files (but not the
additional packages that were installed): 

`./util/install.sh -u`


### Documentation

In addition to the API documentation (`make doc`), much useful
information, including a Mininet walkthrough and an introduction
to the Python API, is available on the
[Mininet Web Site](http://mininet.org).
There is also a wiki which you are encouraged to read and to
contribute to, particularly the Frequently Asked Questions (FAQ.)

Details about FreeBSD support are available on the 
[FreeBSD wiki Mininet page](https://wiki.freebsd.org/Mininet).

Details about OpenBSD support are found in `INSTALL.OpenBSD`.


### Support

This fork of Mininet is an experiment that isn't supported by the
Mininet community; However, Mininet-related questions pertaining to
the features of the original Mininet can be directed to
`mininet-discuss`:

<https://mailman.stanford.edu/mailman/listinfo/mininet-discuss>

