from __future__ import absolute_import
# SMOP compiler -- Simple Matlab/Octave to Python compiler
# Copyright 2011-2013 Victor Leikehman

import smop.version
import sys,six.moves.cPickle,glob,os
import getopt,re
from smop import lexer,parse,resolve,backend,options,graphviz
import smop.node as node
import networkx as nx
from smop.runtime import *
from smop.core import *
from six.moves import input
#from version import __version__
__version__ = smop.version.__version__

def usage():
    print "SMOP compiler version " + __version__
    print """Usage: smop [options] file-list
    Options:
    -V --version
    -X --exclude=FILES      Ignore files listed in comma-separated list FILES.
                            Can be used several times.
    -S --syntax-errors=FILES Ignore syntax errors in comma-separated list of FILES.
                            Can be used several times.
    -S.                     Always gnore syntax errors
    -d --dot=REGEX          For functions whose names match REGEX, save debugging
                            information in "dot" format (see www.graphviz.org).
                            You need an installation of graphviz to use --dot
                            option.  Use "dot" utility to create a pdf file.
                            For example:
                                $ python main.py fastsolver.m -d "solver|cbest"
                                $ dot -Tpdf -o resolve_solver.pdf resolve_solver.dot
    -h --help
    -o --output=FILENAME    By default create file named a.py
    -o- --output=-          Use standard output
    -s --strict             Stop on the first error
    -v --verbose
"""

def main():
    """
    !a="def f(): \\n\\treturn 123"
    !exec a
    !print f
    !print f()
    !reload(backend)
    =>> function t=foo(a) \\
    ... t=123
    !exec foo(3)
    """
    try:
        opts, args = getopt.gnu_getopt(sys.argv[1:],
                                       "d:ho:vVsr:S:X:",
                                       [
                                        "dot=",
                                        "exclude=",
                                        "help",
                                        "syntax-errors=",
                                        "output=",
                                        "runtime=",
                                        "strict",
                                        "verbose",
                                        "version",
                                       ])
    except getopt.GetoptError as err:
        # print help information and exit:
        print str(err) # will print something like "option -a not recognized"
        usage()
        sys.exit(2)

    exclude_list = []
    output = None
    strict = 0
    dot = None
    runtime = []

    for o, a in opts:
        if o in ("-r", "--runtime"):
            runtime += [a]
        elif o in ("-s", "--strict"):
            strict = 1
        elif o in ("-S", "--syntax-errors"):
            options.syntax_errors += a.split(",")
        elif o in ("-d", "--dot"):
            dot = re.compile(a)
        elif o in ("-X", "--exclude"):
            exclude_list += [ "%s.m" % b for b in a.split(",")]
        elif o in ("-v", "--verbose"):
            options.verbose += 1
        elif o in ("-V", "--version"):
            print "SMOP compiler version " + __version__
            sys.exit()
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-o", "--output"):
            output = a
        else:
            assert False, "unhandled option"

    """
    if not args:
        usage()
        sys.exit()
    """
    if not args:
        symtab = {}
        print "? for help"
        while 1:
            try:
                buf = input("octave: ")
                if not buf:
                    continue
                while buf[-1] == "\\":
                    buf = buf[:-1] + "\n" + input("... ")
                if buf[0] == '?':
                    print main.__doc__
                    continue
                if buf[0] == "!":
                    try:
                        exec(buf[1:])
                    except Exception as ex:
                        print ex
                    continue
                t = parse.parse(buf if buf[-1]=='\n' else buf+'\n')
                if not t:
                    continue
                print "t=", repr(t)
                print 60*"-"
                resolve.resolve(t,symtab)
                print "t=", repr(t)
                print 60*"-"
                print "symtab:",symtab
                s = backend.backend(t)
                print "python:",s.strip()
                try:
                    print eval(s)
                except SyntaxError:
                    exec(s)
            except EOFError:
                return
            except Exception as ex:
                print ex

    if not output:
        output = "a.py"
    fp = open(output,"w") if output != "-" else sys.stdout
    print >> fp, "# Autogenerated with SMOP version " + __version__
    print >> fp, "# " + " ".join(sys.argv)
    print >> fp, "from __future__ import division"
    for a in runtime:
        print >> fp, "from %s import *" % a

    for pattern in args:
        for filename in glob.glob(os.path.expanduser(pattern)):
            if not filename.endswith(".m"):
                print "\tIngored file: '%s'" % filename
                continue
            if os.path.basename(filename) in exclude_list:
                print "\tExcluded file: '%s'" % filename
                continue
            if options.verbose:
                print filename
            buf = open(filename).read().replace("\r\n","\n")
            func_list = parse.parse(buf if buf[-1]=='\n' else buf+'\n',filename)
            if not func_list and strict:
                sys.exit(-1)

            for func_obj in func_list:
                try:
                    func_name = func_obj.head.ident.name
                    if options.verbose:
                        print "\t",func_name
                except AttributeError:
                    if options.verbose:
                        print "\tJunk ignored"
                    if strict:
                        sys.exit(-1)
                    continue
                fp0 = open("parse_"+func_name+".dot","w") if dot and dot.match(func_name) else None
                if fp0:
                    graphviz.graphviz(func_obj,fp0)
                if options.do_resolve:
                    G = resolve.resolve(func_obj)

            for func_obj in func_list:
                s = backend.backend(func_obj)
                print >> fp, s

if __name__ == "__main__":
    main()
