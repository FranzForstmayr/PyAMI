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
        self.components = model_dict['components']
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

        (mname, rlc_dict) = self.pin
        self.models = self.get_models(mname)

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
