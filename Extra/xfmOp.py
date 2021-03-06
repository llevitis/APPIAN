import os
import numpy as np
from os.path import splitext, basename
from nipype.interfaces.base import CommandLine, CommandLineInputSpec
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,isdefined)
from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix)


class ConcatInput(CommandLineInputSpec):
    in_file = File(position=0, argstr="%s", exists=True, mandatory=True, desc="main input xfm file")
    in_file_2 = File(position=1, argstr="%s", exists=True, mandatory=True, desc="input xfm files to concat")
    out_file = File(position=2, argstr="%s", desc="output concatenated xfm file")

    clobber = traits.Bool(argstr="-clobber", usedefault=True, default_value=True, desc="Overwrite output file")
    verbose = traits.Bool(argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class ConcatOutput(TraitedSpec):
    out_file = File(exists=True, desc="transformation matrix")

class ConcatCommand(CommandLine):
    _cmd = "xfmconcat"
    _suffix = "_concat"
    input_spec = ConcatInput
    output_spec = ConcatOutput


    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_filename(self.inputs.in_file, self.inputs.in_file_2, self._suffix)

        return super(ConcatCommand, self)._parse_inputs(skip=skip)

    def _list_outputs(self):
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_filename(self.inputs.in_file, self.inputs.in_file_2, self._suffix)
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs


    def _gen_filename(self, name, name2, suffix):
        split_name = splitext(name)
        split_name2 = splitext(name2)
        fn = os.getcwd() + os.sep + basename(split_name[0])+"_"+basename(split_name2[0]) + split_name[1]
        print fn
        return fn






class InvertInput(CommandLineInputSpec):
    in_file = File(position=0, argstr="%s", exists=True, mandatory=True, desc="main input xfm file")
    out_file = File(position=2, argstr="%s", desc="output inverted xfm file")

    clobber = traits.Bool(argstr="-clobber", usedefault=True, default_value=True, desc="Overwrite output file")
    verbose = traits.Bool(argstr="-verbose", usedefault=True, default_value=True, desc="Write messages indicating progress")

class InvertOutput(TraitedSpec):
    out_file = File(desc="transformation matrix")

class InvertCommand(CommandLine):
    _cmd = "xfminvert"
    _suffix = "_inv"
    input_spec = InvertInput
    output_spec = InvertOutput

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []
        if not isdefined(self.inputs.out_file):
            self.inputs.out_file = self._gen_fname(self.inputs.in_file, suffix=self._suffix, ext='.xfm')

        return super(InvertCommand, self)._parse_inputs(skip=skip)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file
        return outputs


    def _gen_filename(self, name):
        if name == "out_file":
            return self._list_outputs()["out_file"]
        return None
