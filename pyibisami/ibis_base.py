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

import platform

from datetime     import datetime

from .ibis_parser import parse_ibis_file

class IBISModelBase():
    """
    HasTraits subclass for wrapping and interacting with an IBIS model.

    This class can be configured to present a customized GUI to the user
    for interacting with a particular IBIS model (i.e. - selecting components,
    pins, and models).

    The intended use model is as follows:

     1. Instantiate this class only once per IBIS model file.
        When instantiating, provide the unprocessed contents of the IBIS
        file, as a single string. This class will take care of getting
        that string parsed properly, and report any errors or warnings
        it encounters, in its ``ibis_parsing_errors`` property.

     2. When you want to let the user select a particular component/pin/model,
        call the newly created instance, as if it were a function, passing
        no arguments.
        The instance will then present a GUI to the user,
        allowing him to select a particular component/pin/model, which may then
        be retrieved, via the ``model`` property.
        The latest user selections will be remembered,
        as long as the instance remains in scope.

    Any errors or warnings encountered while parsing are available, in
    the ``ibis_parsing_errors`` property.

    The complete dictionary containing all parsed models may be retrieved,
    via the ``model_dict`` property.
    """

    _log = ""

    def get_models(self, mname):
        """Return the list of models associated with a particular name."""
        model_dict = self._model_dict
        if 'model_selectors' in model_dict and mname in model_dict['model_selectors']:
            return list(map(lambda pr: pr[0], model_dict['model_selectors'][mname]))
        else:
            return [mname]

    def get_pins(self):
        """Get the list of appropriate pins, given our type (i.e. - Tx or Rx)."""
        pins = self.comp_.pins
        def pin_ok(pname):
            (mname, _) = pins[pname]
            mods = self.get_models(mname)
            mod = self._models[mods[0]]
            mod_type = mod.mtype.lower()
            tx_ok = (mod_type == "output") or (mod_type == "i/o")
            if self._is_tx:
                return(tx_ok)
            else:
                return(not tx_ok)
        return(list(filter(pin_ok, list(pins))))

    def __init__(self, ibis_file_name, is_tx, debug=False):
        """
        Args:
            ibis_file_contents_str (str): The unprocessed contents of
                the IBIS file, as a single string.
            is_tx (bool): True if this is a Tx model.

        KeywordArgs:
            debug (bool): Output debugging info to console when true.
                Default = False
        """

        # Super-class initialization is ABSOLUTELY NECESSARY, in order
        # to get all the Traits/UI machinery setup correctly.
        super().__init__()

        self.debug = debug
        self.log("pyibisami.ibis_file.IBISModel initializing...")

        # Parse the IBIS file contents, storing any errors or warnings, and validate it.
        with open(ibis_file_name) as file:
            ibis_file_contents_str = file.read()
        err_str, model_dict = parse_ibis_file(ibis_file_contents_str, debug=debug)
        if 'components' not in model_dict or not model_dict['components']:
            raise ValueError("This IBIS model has no components! Parser messages:\n" + err_str)
        components = model_dict['components']
        if 'models' not in model_dict or not model_dict['models']:
            raise ValueError("This IBIS model has no models! Parser messages:\n" + err_str)
        models = model_dict['models']
        self._model_dict = model_dict
        self._models = models
        self._is_tx = is_tx
        self.log("IBIS parsing errors/warnings:\n" + err_str)

        self._ibis_parsing_errors = err_str
        self._os_type = platform.system()           # These 2 are used, to choose
        self._os_bits = platform.architecture()[0]  # the correct AMI executable.

        #self._comp_changed(list(components)[0])     # Wasn't being called automatically.
        #self._pin_changed(self.pins[0])             # Wasn't being called automatically.

        self.log("Done.")

    def __str__(self):
        return(f"IBIS Model '{self._model_dict['file_name']}'")

    def info(self):
        res = ""
        try:
            for k in ['ibis_ver', 'file_name', 'file_rev']:
                res += k + ':\t' + str(self._model_dict[k]) + '\n'
        except:
            print(self._model_dict)
            raise
        res += 'date' + ':\t\t' + str(self._model_dict['date']) + '\n'
        res += "\nComponents:"
        res += "\n=========="
        for c in list(self._model_dict['components']):
            res += "\n" + c + ":\n" + "---\n" + str(self._model_dict['components'][c]) + "\n"
        res += "\nModel Selectors:"
        res += "\n===============\n"
        for s in list(self._model_dict['model_selectors']):
            res += f"{s}\n"
        res += "\nModels:"
        res += "\n======"
        for m in list(self._model_dict['models']):
            res += "\n" + m + ":\n" + "---\n" + str(self._model_dict['models'][m])
        return res

    # Logger & Pop-up
    def log(self, msg):
        """Log a message to the console and, optionally, to terminal and/or pop-up dialog."""
        _msg = msg.strip()
        txt = "\n[{}]: {}\n".format(datetime.now(), _msg)
        self._log += txt
        if self.debug:
            print(txt)

    @property
    def ibis_parsing_errors(self):
        """Any errors or warnings encountered, while parsing the IBIS file contents."""
        return self._ibis_parsing_errors

    @property
    def log_txt(self):
        """The complete log since instantiation."""
        return self._log

    @property
    def model_dict(self):
        "Dictionary of all model keywords."
        return self._model_dict

    @property
    def dll_file(self):
        return self._dll_file

    @property
    def ami_file(self):
        return self._ami_file

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
