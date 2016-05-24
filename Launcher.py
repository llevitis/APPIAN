#!/usr/bin/env python

import os
import sys
import argparse
import commands
import shutil
import tempfile
import time

from optparse import OptionParser
from optparse import OptionGroup
import nipype.interfaces.minc as minc
import nipype.pipeline.engine as pe
import nipype.interfaces.io as nio
import nipype.interfaces.utility as util
from nipype.interfaces.utility import Rename

from Masking import masking as masking
import Registration.registration as reg
import Initialization.initialization as init

version = "1.0"



def printOptions(opts,args):
	uname = os.popen('uname -s -n -r').read()

	print "\n"
	print "* Pipeline started at "+time.strftime("%c")+"on "+uname
	print "* Command line is : \n "+str(sys.argv)+"\n"
	print "* The source directory is : "+opts.sourceDir
	print "* The target directory is : "+opts.targetDir+"\n"
	print "* The Civet directory is : "+opts.civetDir+"\n"
	print "* Data-set Subject ID(s) is/are : "+str(', '.join(args))+"\n"
	print opts.condiList
	print "* PET conditions : "+', '.join(opts.condiList)+"\n"
	print "* ROI labels : "+str(', '.join(opts.ROILabels))+"\n"




def test_get_inputs():
	return 

def runPipeline(opts,args):	
	if args:
		subjects_ids = args
	else:
		print "\n\n*******ERROR********: \n     The subject IDs are not listed in the command-line \n********************\n\n"
		sys.exit(1)

#	subjects_ids=["%03d" % subjects_ids[subjects_ids.index(subj)] for subj in subjects_ids]
	conditions_ids=list(range(len(opts.condiList)))
	conditions_ids=opts.condiList
	print(conditions_ids)

	###Infosource###
	infosource = pe.Node(interface=util.IdentityInterface(fields=['study_prefix', 'subject_id', 'condition_id']), name="infosource")
	infosource.inputs.study_prefix = opts.prefix
	infosource.iterables = [ ('subject_id', subjects_ids), ('condition_id', conditions_ids) ]


	##Datasources###
	datasourceRaw = pe.Node( interface=nio.DataGrabber(infields=['study_prefix', 'subject_id', 'condition_id'], 
													   outfields=['pet'], sort_filelist=False), name="datasourceRaw")
	datasourceRaw.inputs.base_directory = opts.sourceDir
	datasourceRaw.inputs.template = '*'
	datasourceRaw.inputs.field_template = dict(pet='pet/%s/%s_%s_%s_real_orig.mnc')
	datasourceRaw.inputs.template_args = dict(pet=[['study_prefix', 'study_prefix', 'subject_id', 'condition_id']])	


	datasourceCivet = pe.Node( interface=nio.DataGrabber(infields=['study_prefix', 'subject_id'], 
														 outfields=['nativeT1', 'nativeT1nuc', 
														 			'talT1', 'xfmT1tal','xfmT1talnl',
														 			'brainmasktal', 'headmasktal', 'clsmask', 'animalmask'], 
														 sort_filelist=False), name="datasourceCivet")
	datasourceCivet.inputs.base_directory = opts.civetDir
	datasourceCivet.inputs.template = '*'
	datasourceCivet.inputs.field_template = dict(nativeT1='%s/%s/native/%s_%s_t1.mnc', 
												 nativeT1nuc='%s/%s/native/%s_%s_t1_nuc.mnc', 
												 talT1='%s/%s/final/%s_%s_t1_tal.mnc',
												 xfmT1tal='%s/%s/transforms/linear/%s_%s_t1_tal.xfm',
												 xfmT1talnl='%s/%s/transforms/nonlinear/%s_%s_nlfit_It.xfm',
												 brainmasktal='%s/%s/mask/%s_%s_brain_mask.mnc',
												 headmasktal='%s/%s/mask/%s_%s_skull_mask.mnc',
												 clsmask='%s/%s/classify/%s_%s_pve_classify.mnc',
												 animalmask='%s/%s/segment/%s_%s_stx_labels_masked.mnc'
												)
	datasourceCivet.inputs.template_args = dict(nativeT1=[['study_prefix', 'subject_id', 'study_prefix', 'subject_id']], 
										   		nativeT1nuc=[['study_prefix', 'subject_id', 'study_prefix', 'subject_id']], 
										   		talT1=[['study_prefix', 'subject_id', 'study_prefix', 'subject_id']], 
										   		xfmT1tal=[['study_prefix', 'subject_id', 'study_prefix', 'subject_id']], 
										   		xfmT1talnl=[['study_prefix', 'subject_id', 'study_prefix', 'subject_id']], 
										   		brainmasktal=[['study_prefix', 'subject_id', 'study_prefix', 'subject_id']], 										   		
										   		headmasktal=[['study_prefix', 'subject_id', 'study_prefix', 'subject_id']], 										   		
										   		clsmask=[['study_prefix', 'subject_id', 'study_prefix', 'subject_id']], 										   		
										   		animalmask=[['study_prefix', 'subject_id', 'study_prefix', 'subject_id']] 										   		
										   		)	


	##Datasink###
	datasink=pe.Node(interface=nio.DataSink(), name="output")
	datasink.inputs.base_directory= opts.targetDir + '/' +opts.prefix
	datasink.inputs.substitutions = [('_condition_id_', ''), ('subject_id_', '')]

	##Nodes###
	node_name="t1Masking"
	t1Masking = pe.Node(interface=masking.T1maskingRunning(), name=node_name)
	t1Masking.inputs.modelDir = opts.modelDir
	t1Masking.inputs.clobber = True
	t1Masking.inputs.verbose = opts.verbose
	t1Masking.inputs.run = opts.prun
	rT1MaskingHead=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(subject_id)s_%(condition_id)s_"+node_name+"_head.mnc"), name="r"+node_name+"Head")
	rT1MaskingBrain=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(subject_id)s_%(condition_id)s_"+node_name+"_brain.mnc"), name="r"+node_name+"Brain")

	node_name="refMasking"
	refMasking = pe.Node(interface=masking.RefmaskingRunning(), name=node_name)
	refMasking.inputs.segLabels = opts.RefAtlasValue
	refMasking.inputs.MaskingType = opts.RefMaskType
	refMasking.inputs.modelDir = opts.RefTemplate
	refMasking.inputs.close = opts.RefClose
	refMasking.inputs.refGM = True if opts.RefMatter == 'gm' else False
	refMasking.inputs.refWM = True if opts.RefMatter == 'wm' else False
	refMasking.inputs.clobber = True
	refMasking.inputs.verbose = opts.verbose
	refMasking.inputs.run = opts.prun
	rRefMaskingTal=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(subject_id)s_%(condition_id)s_"+node_name+"Tal.mnc"), name="r"+node_name+"Tal")
	rRefMaskingT1=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(subject_id)s_%(condition_id)s_"+node_name+"T1.mnc"), name="r"+node_name+"T1")


	node_name="petCenter"
	petCenter= pe.Node(interface=init.VolCenteringRunning(), name=node_name)
	petCenter.inputs.verbose = opts.verbose
	petCenter.inputs.run = opts.prun	
	rPetCenter=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(subject_id)s_%(condition_id)s_"+node_name+".mnc"), name="r"+node_name)

	node_name="petExcludeFr"
	petExFr = pe.Node(interface=init.PETexcludeFrRunning(), name=node_name)
	petExFr.inputs.verbose = opts.verbose	
	petExFr.inputs.run = opts.prun
	rPetExFr=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(subject_id)s_%(condition_id)s_"+node_name+".mnc"), name="r"+node_name)

	node_name="petVolume"
	petVolume = pe.Node(interface=minc.AverageCommand(), name=node_name)
	petVolume.inputs.avgdim = 'time'
	petVolume.inputs.width_weighted = True
	petVolume.inputs.clobber = True
	petVolume.inputs.verbose = opts.verbose	
	rPetVolume=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(subject_id)s_%(condition_id)s_"+node_name+".mnc"), name="r"+node_name)

	node_name="petSettings"
	petSettings = pe.Node(interface=init.MincHdrInfoRunning(), name=node_name)
	petSettings.inputs.verbose = opts.verbose
	petSettings.inputs.clobber = True
	petSettings.inputs.run = opts.prun
	rPetSettings=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(subject_id)s_%(condition_id)s_"+node_name+".mnc"), name="r"+node_name)

	node_name="petMasking"
	petMasking = pe.Node(interface=masking.PETheadMaskingRunning(), name=node_name)
	petMasking.inputs.verbose = opts.verbose
	petMasking.inputs.run = opts.prun
	rPetMasking=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(subject_id)s_%(condition_id)s_"+node_name+".mnc"), name="r"+node_name)

	node_name="pet2mri"
	pet2mri = pe.Node(interface=reg.PETtoT1LinRegRunning(), name=node_name)
	pet2mri.inputs.clobber = True
	pet2mri.inputs.verbose = opts.verbose
	pet2mri.inputs.run = opts.prun
	rPet2MriImg=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(subject_id)s_%(condition_id)s_"+node_name+".mnc"), name="r"+node_name+"Img")
	rPet2MriXfm=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(subject_id)s_%(condition_id)s_"+node_name+".xfm"), name="r"+node_name+"Xfm")


	node_name="petRefMask"
	petRefMask = pe.Node(interface=minc.ResampleCommand(), name=node_name)
	petRefMask.inputs.interpolation = 'nearest_neighbour'
	petRefMask.inputs.invert = 'invert_transformation'
	petRefMask.inputs.clobber = True
	rPetRefMask=pe.Node(interface=Rename(format_string="%(study_prefix)s_%(subject_id)s_%(condition_id)s_"+node_name+".mnc"), name="r"+node_name)



	workflow = pe.Workflow(name='preproc')
	workflow.base_dir = opts.targetDir

	workflow.connect([(infosource, datasourceRaw, [('subject_id', 'subject_id')]),
                      (infosource, datasourceRaw, [('condition_id', 'condition_id')]),
                      (infosource, datasourceRaw, [('study_prefix', 'study_prefix')]),
                      (infosource, datasourceCivet, [('subject_id', 'subject_id')]),
                      (infosource, datasourceCivet, [('study_prefix', 'study_prefix')])
                	 ])
	workflow.connect([(datasourceCivet, t1Masking, [('nativeT1nuc', 'nativeT1')]), 
					  (datasourceCivet, t1Masking, [('xfmT1tal', 'LinT1TalXfm')]), 
					  (datasourceCivet, t1Masking, [('brainmasktal', 'brainmaskTal')])])

	workflow.connect([(t1Masking, rT1MaskingBrain, [('T1brainmask', 'in_file')])])
	workflow.connect([(t1Masking, rT1MaskingHead, [('T1headmask', 'in_file')])])

	workflow.connect([(infosource, rT1MaskingBrain, [('study_prefix', 'study_prefix')]),
					  (infosource, rT1MaskingBrain, [('subject_id', 'subject_id')]),
					  (infosource, rT1MaskingBrain, [('condition_id','condition_id')])])
	workflow.connect([(infosource, rT1MaskingHead, [('study_prefix', 'study_prefix')]),
	 				  (infosource, rT1MaskingHead, [('subject_id', 'subject_id')]),
	 				  (infosource, rT1MaskingHead, [('condition_id','condition_id')])])

	workflow.connect(rT1MaskingBrain, 'out_file', datasink, t1Masking.name+"Head")
	workflow.connect(rT1MaskingHead, 'out_file', datasink, t1Masking.name+"Brain")


	workflow.connect([(datasourceCivet, refMasking, [('nativeT1nuc','nativeT1',)]),
                      (datasourceCivet, refMasking, [('talT1','T1Tal', )]),
                      (datasourceCivet, refMasking, [('xfmT1tal','LinT1TalXfm')]),
                      (datasourceCivet, refMasking, [('brainmasktal','brainmaskTal' )]),
                      (datasourceCivet, refMasking, [('clsmask','clsmaskTal')]),
                      (datasourceCivet, refMasking, [('animalmask','segMaskTal' )])
                    ])
  
    #Connect RefmaskTal from refMasking to rename node
	workflow.connect([(refMasking, rRefMaskingTal, [('RefmaskTal', 'in_file')])])
	workflow.connect([(infosource, rRefMaskingTal, [('study_prefix', 'study_prefix')]),
                      (infosource, rRefMaskingTal, [('subject_id', 'subject_id')]),
                      (infosource, rRefMaskingTal, [('condition_id', 'condition_id')])
                    ])

    #Connect RefmaskT1 from refMasking to rename node
	workflow.connect([(refMasking, rRefMaskingT1, [('RefmaskT1', 'in_file')])])
	workflow.connect([(infosource, rRefMaskingT1, [('study_prefix', 'study_prefix')]),
                      (infosource, rRefMaskingT1, [('subject_id', 'subject_id')]),
                      (infosource, rRefMaskingT1, [('condition_id', 'condition_id')])
                    ])

	workflow.connect(rRefMaskingT1, 'out_file', datasink, refMasking.name+"T1")
	workflow.connect(rRefMaskingTal, 'out_file', datasink, refMasking.name+"Tal")


    #Connect PET to PET volume
	workflow.connect([(datasourceRaw, petCenter, [('pet', 'in_file')])])

	#Connect pet from petVolume to its rename node
	workflow.connect([(petCenter, rPetCenter, [('out_file', 'in_file')])])
	workflow.connect([(infosource, rPetCenter, [('study_prefix', 'study_prefix')]),
                      (infosource, rPetCenter, [('subject_id', 'subject_id')]),
                      (infosource, rPetCenter, [('condition_id', 'condition_id')])
                    ])

	workflow.connect(rPetCenter, 'out_file', datasink, petCenter.name)



	workflow.connect([(petCenter, petExFr, [('out_file', 'in_file')])])
	
	workflow.connect([(petExFr, rPetExFr, [('out_file', 'in_file')])])
	workflow.connect([(infosource, rPetExFr, [('study_prefix', 'study_prefix')]),
                      (infosource, rPetExFr, [('subject_id', 'subject_id')]),
                      (infosource, rPetExFr, [('condition_id', 'condition_id')])
                    ])

	workflow.connect(rPetExFr, 'out_file', datasink, petExFr.name)



	workflow.connect([(petExFr, petVolume, [('out_file', 'in_file')])])

	#Connect pet from petVolume to its rename node
	workflow.connect([(petVolume, rPetVolume, [('out_file', 'in_file')])])
	workflow.connect([(infosource, rPetVolume, [('study_prefix', 'study_prefix')]),
                      (infosource, rPetVolume, [('subject_id', 'subject_id')]),
                      (infosource, rPetVolume, [('condition_id', 'condition_id')])
                    ])

	workflow.connect(rPetVolume, 'out_file', datasink, petVolume.name)


    #
	workflow.connect([(datasourceRaw, petSettings, [('pet', 'in_file')])])
	workflow.connect([(petVolume, petMasking, [('out_file', 'in_file')]),
	                  (petSettings, petMasking, [('out_file','in_json')])
                    ])
	#
	workflow.connect([(petMasking, rPetMasking, [('out_file', 'in_file')])])
	workflow.connect([(infosource, rPetMasking, [('study_prefix', 'study_prefix')]),
                      (infosource, rPetMasking, [('subject_id', 'subject_id')]),
                      (infosource, rPetMasking, [('condition_id', 'condition_id')])
                    ])

	workflow.connect(rPetMasking, 'out_file', datasink, petMasking.name)





    #
	workflow.connect([(petVolume, pet2mri, [('out_file', 'in_source_file' )]),
                      (petMasking, pet2mri, [('out_file', 'in_source_mask')]), 
                      (t1Masking, pet2mri, [('T1headmask',  'in_target_mask')]),
                      (datasourceCivet, pet2mri, [('nativeT1nuc', 'in_target_file')])
                      ]) 
    #
	workflow.connect([(pet2mri, rPet2MriImg, [('out_file_img', 'in_file')])])
	workflow.connect([(infosource, rPet2MriImg, [('study_prefix', 'study_prefix')]),
                      (infosource, rPet2MriImg, [('subject_id', 'subject_id')]),
                      (infosource, rPet2MriImg, [('condition_id', 'condition_id')])
                    ])

	workflow.connect([(pet2mri, rPet2MriXfm, [('out_file_xfm', 'in_file')])])
	workflow.connect([(infosource, rPet2MriXfm, [('study_prefix', 'study_prefix')]),
                      (infosource, rPet2MriXfm, [('subject_id', 'subject_id')]),
                      (infosource, rPet2MriXfm, [('condition_id', 'condition_id')])
                    ])

	workflow.connect(rPet2MriXfm, 'out_file', datasink, pet2mri.name+"Xfm")
	workflow.connect(rPet2MriImg, 'out_file', datasink, pet2mri.name+"Img")





    #
	workflow.connect([(refMasking, petRefMask, [('RefmaskT1', 'in_file' )]),
                      (petVolume, petRefMask, [('out_file', 'model_file')]), 
                      (pet2mri, petRefMask, [('out_file_xfm', 'transformation')])
                      ]) 

	workflow.connect([(petRefMask, rPetRefMask, [('out_file', 'in_file')])])
	workflow.connect([(infosource, rPetRefMask, [('study_prefix', 'study_prefix')]),
                      (infosource, rPetRefMask, [('subject_id', 'subject_id')]),
                      (infosource, rPetRefMask, [('condition_id', 'condition_id')])
                    ])

	workflow.connect(rPetRefMask, 'out_file', datasink, petRefMask.name)
	


	printOptions(opts,subjects_ids)

	#run the work flow
	workflow.run()

	# #vizualization graph of the workflow
	# workflow.write_graph(opts.targetDir+os.sep+"workflow_graph.dot", graph2use = 'exec')




def get_opt_list(option,opt,value,parser):
	setattr(parser.values,option.dest,value.split(','))


# def printStages(opts,args):



# def printScan(opts,args):



if __name__ == "__main__":

	usage = "usage: "

	file_dir = os.path.dirname(os.path.realpath(__file__))
	atlas_dir = file_dir + "/Atlas/MNI152/"


	parser = OptionParser(usage=usage,version=version)

	group= OptionGroup(parser,"File options (mandatory)")
	group.add_option("-s","--sourcedir",dest="sourceDir",help="Native pet and mri directory")
	group.add_option("-t","--targetdir",dest="targetDir",help="Directory where output data will be saved in")
	group.add_option("-p","--prefix",dest="prefix",help="Study name")
	group.add_option("-c","--civetdir",dest="civetDir",help="Civet directory")
	parser.add_option_group(group)		

	group= OptionGroup(parser,"Scan options","***if not, only baseline condition***")
	group.add_option("","--condition",dest="condiList",help="comma-separated list of conditions or scans",type='string',action='callback',callback=get_opt_list,default='baseline')
	parser.add_option_group(group)		

	group= OptionGroup(parser,"Registration options")
	group.add_option("","--modelDir",dest="modelDir",help="Models directory",default=atlas_dir)
	parser.add_option_group(group)		

	group= OptionGroup(parser,"PET acquisition options")
	parser.add_option_group(group)
		
	group= OptionGroup(parser,"Masking options","Reference region")
	group.add_option("","--ref-atlas",dest="RefMaskType",help="Use an atlas to make the Reference mask",action='store_const',const='atlas',default='atlas')
	group.add_option("","--ref-nonlinear",dest="RefMaskType",help="Non linear registration based segmentatoin",action='store_const',const='nonlinear',default='atlas')
	group.add_option("","--ref-no-transform",dest="RefMaskType",help="Don't run any non-linear registration",action='store_const',const='no-transform',default='atlas')
	group.add_option("","--ref-atlas_labels",dest="RefAtlasValue",help="Label value(s) from ANIMAL segmentation. By default, the values correspond to the cerebellum",type='string',action='callback',callback=get_opt_list,default=['67','76'])
	group.add_option("","--ref-template",dest="RefTemplate",help="Template to segment the reference region.",default= atlas_dir + 'mni_icbm152_t1_tal_nlin_sym_09a.mnc')
	group.add_option("","--ref-gm",dest="RefMatter",help="Gray matter of reference region (if -ref-animal is used)",action='store_const',const='gm',default='gm')
	group.add_option("","--ref-wm",dest="RefMatter",help="White matter of reference region (if -ref-animal is used)",action='store_const',const='wm',default='gm')
	group.add_option("","--ref-close",dest="RefClose",help="Close - erosion(dialtion(X))",action='store_true',default=False)
	group.add_option("","--ref-mask",dest="RefOnTemplate",help="Reference mask on the template",default=None)	
	parser.add_option_group(group)

	group= OptionGroup(parser,"Masking options","Region Of Interest")
	group.add_option("","--roi-animal",dest="roiValueAnimal",help="Label value(s) from ANIMAL segmentation.",type='string',action='callback',callback=get_opt_list)
	group.add_option("","--roi-linreg",dest="roiRegister",help="Non-linear registration based segmentation",action='store_true',default=False)
	group.add_option("","--roi-no-linreg",dest="roiRegister",help="Don't run any non-linear registration",action='store_false',default=False)
	group.add_option("","--roi-template",dest="templateROI",help="Template to segment the ROI.",default=atlas_dir+'mni_icbm152_t1_tal_nlin_sym_09a.mnc')
	group.add_option("","--roi-template-suffix",dest="templateROIsuffix",help="Suffix for the ROI template.",default='icbm152')
	group.add_option("","--roi-mask",dest="ROIOnTemplate",help="ROI mask on the template",default=atlas_dir + 'mni_icbm152_t1_tal_nlin_sym_09a_atlas/atlas_level0.5_BG.mnc')	
	group.add_option("","--roi-suffix",dest="ROIsuffix",help="ROI suffix",default='striatal_6lbl')	
	group.add_option("","--roi-labels",dest="ROILabels",help="ROI labels",type='string',action='callback',callback=get_opt_list,default=['4','5','6','9','10','11'])
	group.add_option("","--roi-erosion",dest="roiErosion",help="Erode the ROI mask",action='store_true',default=False)
	parser.add_option_group(group)

	group= OptionGroup(parser,"Tracer Kinetic analysis options")
	parser.add_option_group(group)

	group= OptionGroup(parser,"Command control")
	group.add_option("-v","--verbose",dest="verbose",help="Write messages indicating progress.",action='store_true',default=False)
	parser.add_option_group(group)

	group= OptionGroup(parser,"Pipeline control")
	group.add_option("","--run",dest="prun",help="Run the pipeline.",action='store_true',default=False)
	group.add_option("","--fake",dest="prun",help="do a dry run, (echo cmds only).",action='store_false',default=False)
	group.add_option("","--print-scan",dest="pscan",help="Print the pipeline parameters for the scan.",action='store_true',default=False)
	group.add_option("","--print-stages",dest="pstages",help="Print the pipeline stages.",action='store_true',default=False)
	parser.add_option_group(group)

	(opts, args) = parser.parse_args()

	opts.extension='mnc'

	if not opts.sourceDir or not opts.targetDir or not opts.civetDir or not opts.prefix:
		print "\n\n*******ERROR******** \n     You must specify -sourcedir, -targetdir, -civetdir  and -prefix \n********************\n"
		parser.print_help()
		sys.exit(1)
	
	
	opts.targetDir = os.path.normpath(opts.targetDir)
	opts.sourceDir = os.path.normpath(opts.sourceDir)
	opts.civetDir = os.path.normpath(opts.civetDir)


#	if opts.prun:
#		runPipeline(opts,args)
#	elif opts.pscan:
#		printScan(opts,args)
#	elif opts.pstages:
#		printStages(opts,args)
#	else:
#		print "\n\n*******ERROR********: \n    The options -run, -print-scan or print-stages need to be chosen \n********************\n\n"
#		parser.print_help()
#		sys.exit(1)

	if opts.pscan:
		printScan(opts,args)
	elif opts.pstages:
		printStages(opts,args)
	else:
		runPipeline(opts,args)