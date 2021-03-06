import os
import numpy as np

from nipype.interfaces.base import CommandLine, CommandLineInputSpec
from nipype.interfaces.base import (TraitedSpec, File, traits, InputMultiPath,isdefined)
from nipype.utils.filemanip import (load_json, save_json, split_filename, fname_presuffix)



 
class SmoothInput(CommandLineInputSpec):
    in_file = File(position=-2, argstr="%s", mandatory=True, desc="image to blur")
    out_file = File(position=-1, argstr="%s", desc="smoothed image")
    
    fwhm = traits.Float(position=3, argstr="-fwhm %d", mandatory=True, desc="fwhm value")  
    no_apodize = traits.Bool(position=0, argstr="-no_apodize", usedefault=True, default_value=True, desc="Do not apodize the data before blurring")

    clobber = traits.Bool(argstr="-clobber", position=1, usedefault=True, default_value=True, desc="Overwrite output file")
    verbose = traits.Bool(argstr="-verbose", position=2, usedefault=True, default_value=True, desc="Write messages indicating progress")

class SmoothOutput(TraitedSpec):
    out_file = File(exists=True, desc="smoothed image")

#class SmoothCommand(CommandLine, Info):
class SmoothCommand(CommandLine):
    _cmd = "mincblur"
    _suffix = "_blur"
    input_spec = SmoothInput
    output_spec = SmoothOutput

    def _parse_inputs(self, skip=None):
        if skip is None:
            skip = []

        if not isdefined(self.inputs.out_file):
            path, ext = os.path.splitext(self.inputs.in_file)
            fname=os.path.basename(path)
            self.inputs.out_file=os.getcwd()+os.sep+fname+'_fwhm' + str(self.inputs.fwhm)

        return super(SmoothCommand, self)._parse_inputs(skip=skip)


    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = self.inputs.out_file+self._suffix+'.mnc'
        # outputs["out_file"] = self.inputs.out_file+self._suffix+Info.ftypes['MINC']
        return outputs


    def _gen_filename(self, name):
        if name == "out_file":
            return self._list_outputs()["out_file"]
        return None
