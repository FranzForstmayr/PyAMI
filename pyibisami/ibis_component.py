"""
A class for encapsulating IBIS model files.

Original Author: David Banas <capn.freako@gmail.com>

Original Date:   November 1, 2019

For information regarding the IBIS modeling standard, visit:
https://ibis.org/

*Note:* The ``IBISModel`` class, defined here, needs to be kept separate from the
other IBIS-related classes, defined in the ``ibis_model`` module, in order to
avoid circular imports.

Copyright (c) 2019 by David Banas; All rights reserved World wide.
"""
class ComponentBase():
    """Encapsulation of a particular component from an IBIS model file.
    """

    def __init__(self, subDict):
        """
        Args:
            subDict (dict): Dictionary of [Component] sub-keywords/params.
        """

        # Stash the sub-keywords/parameters.
        self._subDict = subDict

        # Fetch available keyword/parameter definitions.
        def maybe(name):
            return subDict[name] if name in subDict else None
        self._mfr   = maybe('manufacturer')
        self._pkg   = maybe('package')
        self._pins  = maybe('pin')
        self._diffs = maybe('diff_pin')

        # Check for the required keywords.
        if not self._mfr:
            raise LookupError("Missing [Manufacturer]!")
        if not self._pkg:
            print(self._mfr)
            raise LookupError("Missing [Package]!")
        if not self._pins:
            raise LookupError("Missing [Pin]!")

    def __str__(self):
        res  = "Manufacturer:\t" + self._mfr       + '\n'
        res += "Package:     \t" + str(self._pkg)  + '\n'
        res += "Pins:\n"
        for pname in self._pins:
            res += "    " + pname + ":\t" + str(self._pins[pname]) + '\n'
        return res

    @property
    def pin(self):
        """The pin selected most recently by the user.

        Returns the first pin in the list, if the user hasn't made a selection yet.
        """
        return self._pin_

    @property
    def pins(self):
        "The list of component pins."
        return self._pins

class ModelBase():
    """Encapsulation of a particular I/O model from an IBIS model file.
    """

    def __init__(self, subDict):
        """
        Args:
            subDict (dict): Dictionary of sub-keywords/params.
        """

        # Stash the sub-keywords/parameters.
        self._subDict = subDict

        # Fetch available keyword/parameter definitions.
        def maybe(name):
            return subDict[name] if name in subDict else None
        self._mtype  = maybe('model_type')
        self._ccomp  = maybe('c_comp')
        self._cref   = maybe('cref')
        self._vref   = maybe('vref')
        self._vmeas  = maybe('vmeas')
        self._rref   = maybe('rref')
        self._trange = maybe('temperature_range')
        self._vrange = maybe('voltage_range')
        self._ramp   = maybe('ramp')

        # Check for the required keywords.
        if not self._mtype:
            raise LookupError("Missing Model_type!")
        if not self._vrange:
            raise LookupError("Missing [Voltage Range]!")
        
        # Infer impedance and rise/fall time for output models.
        mtype = self._mtype.lower()
        if mtype == 'output' or mtype == 'i/o':
            if 'pulldown' not in subDict or 'pullup' not in subDict:
                raise LookupError("Missing I-V curves!")

            if not self._ramp:
                raise LookupError("Missing [Ramp]!")
            ramp = subDict['ramp']
            self._slew = (ramp['rising'][0] + ramp['falling'][0])/2e9  # (V/ns)

        # Separate AMI executables by OS.
        def is64(x):
            ((_, b), _) = x
            return int(b) == 64

        def isWin(x):
            ((os, _), _) = x
            return os.lower() == 'windows'

        def showExec(x):
            ((os, b), fs) = x
            return os + str(b) + ': ' + str(fs)

        def partition(p, xs):
            ts, fs = [], []
            for x in xs:
                ts.append(x) if p(x) else fs.append(x)
            return ts, fs

        def getFiles(x):
            if x:
                ((_, _), fs) = x[0]
                return fs
            else:
                return []

        def splitExecs(fs):
            wins, lins = partition(isWin, fs)
            return (getFiles(wins), getFiles(lins))

        self._exec32Wins, self._exec32Lins = [], []
        self._exec64Wins, self._exec64Lins = [], []
        if 'algorithmic_model' in subDict:
            execs = subDict['algorithmic_model']
            exec64s, exec32s = partition(is64, execs)
            self._exec32Wins, self._exec32Lins = splitExecs(exec32s)
            self._exec64Wins, self._exec64Lins = splitExecs(exec64s)

    def __str__(self):
        res = "Model Type:\t" + self._mtype + '\n'
        res += "C_comp:    \t" + str(self._ccomp) + '\n'
        res += "Cref:      \t" + str(self._cref)  + '\n'
        res += "Vref:      \t" + str(self._vref)  + '\n'
        res += "Vmeas:     \t" + str(self._vmeas) + '\n'
        res += "Rref:      \t" + str(self._rref)  + '\n'
        res += "Temperature Range:\t" + str(self._trange) + '\n'
        res += "Voltage Range:    \t" + str(self._vrange) + '\n'
        if 'algorithmic_model' in self._subDict:
            res += "Algorithmic Model:\n" \
                   + "\t32-bit:\n"
            if self._exec32Lins:
                res += "\t\tLinux: "   + str(self._exec32Lins) + '\n'
            if self._exec32Wins:
                res += "\t\tWindows: " + str(self._exec32Wins) + '\n'
            res += "\t64-bit:\n"
            if self._exec64Lins:
                res += "\t\tLinux: "   + str(self._exec64Lins) + '\n'
            if self._exec64Wins:
                res += "\t\tWindows: " + str(self._exec64Wins) + '\n'
        return res

    @property
    def zout(self):
        "The driver impedance."
        return self._zout

    @property
    def slew(self):
        "The driver slew rate."
        return self._slew
        
    @property
    def ccomp(self):
        "The parasitic capacitance."
        return self._ccomp
        
    @property
    def mtype(self):
        """Model type."""
        return self._mtype
