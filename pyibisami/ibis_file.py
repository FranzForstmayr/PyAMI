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
from traits.api   import HasTraits, Trait, String, Float, List, Property, cached_property, Dict, Any, Enum
from traitsui.api import Item, View, ModalButtons, Group, spring, VGroup, HGroup
from chaco.api    import ArrayPlotData, Plot
from enable.component_editor import ComponentEditor
from traitsui.message import message

from .ibis_parser import parse_ibis_file
from .ibis_model  import Model
from .ibis_base import IBISModelBase

class IBISModel(IBISModelBase, HasTraits):
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

    pin_     = Property(Any,  depends_on=["pin"])
    pin_rlcs = Property(Dict, depends_on=["pin"])
    model    = Property(Any,  depends_on=["mod"])
    pins   = List  # Always holds the list of valid pin selections, given a component selection.
    models = List  # Always holds the list of valid model selections, given a pin selection.

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
        super().__init__(ibis_file_name=ibis_file_name, is_tx=is_tx, debug=debug)

        model_dict = self._model_dict
        components = model_dict['components']

        # Add Traits for various attributes found in the IBIS file.
        self.add_trait('comp', Trait(list(components)[0], components))  # Doesn't need a custom mapper, because
        self.pins = self.get_pins()                                     # the thing above it (file) can't change.
        self.add_trait('pin', Enum(self.pins[0], values="pins"))
        (mname, rlc_dict) = self.pin_
        self.models = self.get_models(mname)
        self.add_trait('mod',       Enum(self.models[0], values="models"))
        self.add_trait('ibis_ver',  Float(model_dict['ibis_ver']))
        self.add_trait('file_name', String(model_dict['file_name']))
        self.add_trait('file_rev',  String(model_dict['file_rev']))
        if 'date' in model_dict:
            self.add_trait('date',      String(model_dict['date']))
        else:
            self.add_trait('date',      String("(n/a)"))

        self._comp_changed(list(components)[0])     # Wasn't being called automatically.
        self._pin_changed(self.pins[0])             # Wasn't being called automatically.

        self.log("Done.")

    def __call__(self):
        """Present a customized GUI to the user, for model selection, etc."""
        self.edit_traits(kind='livemodal')

    # Logger & Pop-up
    def log(self, msg, alert=False):
        super().log(msg)
        if alert:
            message(msg.strip(), "PyAMI Alert")

    def default_traits_view(self):
        view = View(
            VGroup(
                HGroup(
                    Item('file_name', label='File name', style='readonly'),
                    spring,
                    Item('file_rev', label='rev', style='readonly'),
                ),
                HGroup(
                    Item('ibis_ver', label='IBIS ver', style='readonly'),
                    spring,
                    Item('date', label='Date', style='readonly'),
                ),
                HGroup(
                    Item('comp', label='Component'),
                    Item('pin',  label='Pin'),
                    Item('mod',  label='Model'),
                ),
            ),
            resizable=False,
            buttons=ModalButtons,
            title="PyBERT IBIS Model Selector",
            id="pybert.pybert_ami.model_selector",
        )
        return view

    @cached_property
    def _get_pin_(self):
        return self.comp_.pins[self.pin]

    @cached_property
    def _get_pin_rlcs(self):
        (_, pin_rlcs) = self.pin_
        return pin_rlcs

    @cached_property
    def _get_model(self):
        return self._models[self.mod]

    def _comp_changed(self, new_value):
        self.pins = self.get_pins()
        self.pin = self.pins[0]

    def _pin_changed(self, new_value):
        model_dict = self._model_dict
        # (mname, rlc_dict) = self.pin_  # Doesn't work. Because ``pin_`` is a cached property and hasn't yet been marked "dirty"?
        (mname, rlc_dict) = self.comp_.pins[new_value]
        self.models = self.get_models(mname)
        self.mod = self.models[0]

    def _mod_changed(self, new_value):
        model = self._models[new_value]
        os_type = self._os_type
        os_bits = self._os_bits
        fnames = []
        dll_file = ""
        ami_file = ""
        if os_type.lower() == 'windows':
            if os_bits == '64bit':
                fnames = model._exec64Wins
            else:
                fnames = model._exec32Wins
        else:
            if os_bits == '64bit':
                fnames = model._exec64Lins
            else:
                fnames = model._exec32Lins
        if fnames:
            dll_file = fnames[0]
            ami_file = fnames[1]
            self.log(
                "There was an [Algorithmic Model] keyword in this model.\n \
If you wish to use the AMI model associated with this IBIS model,\n \
please, go the 'Equalization' tab and enable it now.",
                alert=True)
        elif 'algorithmic_model' in model._subDict:
            self.log(f"There was an [Algorithmic Model] keyword for this model,\n \
but no executable for your platform: {os_type}-{os_bits};\n \
PyBERT native equalization modeling being used instead.",
                alert=True)
        else:
            self.log("There was no [Algorithmic Model] keyword for this model;\n \
PyBERT native equalization modeling being used instead.",
                alert=True)
        self._dll_file = dll_file
        self._ami_file = ami_file
