"""
IBIS-AMI parameter parsing and configuration utilities.

Original author: David Banas <capn.freako@gmail.com>

Original date:   December 17, 2016

Copyright (c) 2019 David Banas; all rights reserved World wide.
"""
import re

from parsec import ParseError, generate, many, many1, regex, string, parsecmap
from traits.api import Bool, Enum, HasTraits, Range, Trait, List
from traitsui.api import Group, Item, View
from traitsui.menu import ModalButtons

from .ami_parameter import AMIParamError, AMIParameter
from .ami_base import AMIParamBase
from .ami_base import parse_ami_param_defs as parser_ami

#####
# AMI parameter configurator.
#####


class AMIParamConfigurator(AMIParamBase, HasTraits):
    """
    Customizable IBIS-AMI model parameter configurator.

    This class can be configured to present a customized GUI to the user
    for configuring a particular IBIS-AMI model.

    The intended use model is as follows:

     1. Instantiate this class only once per IBIS-AMI model invocation.
        When instantiating, provide the unprocessed contents of the AMI
        file, as a single string. This class will take care of getting
        that string parsed properly, and report any errors or warnings
        it encounters, in its ``ami_parsing_errors`` property.

     2. When you want to let the user change the AMI parameter
        configuration, call the ``open_gui`` member function.
        (Or, just call the instance as if it were executable.)
        The instance will then present a GUI to the user,
        allowing him to modify the values of any *In* or *InOut* parameters.
        The resultant AMI parameter dictionary, suitable for passing
        into the ``ami_params`` parameter of the ``AMIModelInitializer``
        constructor, can be accessed, via the instance's
        ``input_ami_params`` property. The latest user selections will be
        remembered, as long as the instance remains in scope.

    The entire AMI parameter definition dictionary, which should *not* be
    passed to the ``AMIModelInitializer`` constructor, is available in the
    instance's ``ami_param_defs`` property.

    Any errors or warnings encountered while parsing are available, in
    the ``ami_parsing_errors`` property.

    """

    def __init__(self, ami_file_contents_str):
        """
        Args:
            ami_file_contents_str (str): The unprocessed contents of
                the AMI file, as a single string.
        """

        # Super-class initialization is ABSOLUTELY NECESSARY, in order
        # to get all the Traits/UI machinery setup correctly.
        AMIParamBase.__init__(self, ami_file_contents_str)
        HasTraits.__init__(self)

        gui_items, new_traits = make_gui_items(
            "Model Specific In/InOut Parameters", self._param_dict["Model_Specific"], first_call=True
        )
        trait_names = []
        for trait in new_traits:
            self.add_trait(trait[0], trait[1])
            trait_names.append(trait[0])
        self._content = gui_items
        self._param_trait_names = trait_names
        self._content = gui_items

    def __call__(self):
        self.open_gui()
        
    def open_gui(self):
        """Present a customized GUI to the user, for parameter customization."""
        self.edit_traits()

    def default_traits_view(self):
        view = View(
            resizable=False,
            buttons=ModalButtons,
            title="PyBERT AMI Parameter Configurator",
            id="pybert.pybert_ami.param_config",
        )
        view.set_content(self._content)
        return view

def make_gui_items(pname, param, first_call=False):
    """Builds list of GUI items from AMI parameter dictionary."""

    gui_items = []
    new_traits = []
    if isinstance(param, AMIParameter):
        pusage = param.pusage
        if pusage in ("In", "InOut"):
            if param.ptype == "Boolean":
                new_traits.append((pname, Bool(param.pvalue)))
                gui_items.append(Item(pname, tooltip=param.pdescription))
            else:
                pformat = param.pformat
                if pformat == "Range":
                    new_traits.append((pname, Range(param.pmin, param.pmax, param.pvalue)))
                    gui_items.append(Item(pname, tooltip=param.pdescription))
                elif pformat == "List":
                    list_tips = param.plist_tip
                    default = param.pdefault
                    if list_tips:
                        tmp_dict = {}
                        tmp_dict.update(list(zip(list_tips, param.pvalue)))
                        val = list(tmp_dict.keys())[0]
                        if default:
                            for tip in tmp_dict:
                                if tmp_dict[tip] == default:
                                    val = tip
                                    break
                        new_traits.append((pname, Trait(val, tmp_dict)))
                    else:
                        val = param.pvalue[0]
                        if default:
                            val = default
                        new_traits.append((pname, Enum([val] + param.pvalue)))
                    gui_items.append(Item(pname, tooltip=param.pdescription))
                else:  # Value
                    new_traits.append((pname, param.pvalue))
                    gui_items.append(Item(pname, style="readonly", tooltip=param.pdescription))
    else:  # subparameter branch
        subparam_names = list(param.keys())
        subparam_names.sort()
        sub_items = []
        group_desc = ""

        # Build GUI items for this branch.
        for subparam_name in subparam_names:
            if subparam_name == "description":
                group_desc = param[subparam_name]
            else:
                tmp_items, tmp_traits = make_gui_items(subparam_name, param[subparam_name])
                sub_items.extend(tmp_items)
                new_traits.extend(tmp_traits)

        # Put all top-level ungrouped parameters in a single VGroup.
        top_lvl_params = []
        sub_params = []
        for item in sub_items:
            if isinstance(item, Item):
                top_lvl_params.append(item)
            else:
                sub_params.append(item)
        sub_items = [Group(top_lvl_params)] + sub_params

        # Make the top-level group an HGroup; all others VGroups (default).
        if first_call:
            gui_items.append(
                Group([Item(label=group_desc)] + sub_items, label=pname, show_border=True, orientation="horizontal")
            )
        else:
            gui_items.append(Group([Item(label=group_desc)] + sub_items, label=pname, show_border=True))

    return gui_items, new_traits

def parse_ami_param_defs(param_str):
    return parser_ami(param_str)