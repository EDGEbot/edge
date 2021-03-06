##
# @file This file is part of EDGE.
#
# @author Alexander Breuer (anbreuer AT ucsd.edu)
#
# @section LICENSE
# Copyright (c) 2017, Regents of the University of California
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
# @section DESCRIPTION
# Generates sampled slip-rates for kinematic source benchmarks.
##
import logging
import argparse
import math
import netCDF4
import subprocess
import tempfile
import xml.etree.ElementTree

##
# Parses an XML-config containing a finite fault description.
#
# @param i_inFile XML-file which is parsed
##
def parseConfig( i_inFile ):
  l_tree = xml.etree.ElementTree.parse( i_inFile )
  l_root = l_tree.getroot()

  l_dict = { 'subfaults': [] }

  # get common options
  l_dict['cdl'] = l_root.find('path_to_cdl').text
  l_dict['out']  = l_root.find('path_to_out').text

  # iterate over subfaults
  for l_subfault in l_root.iter('subfault'):
    l_dict['subfaults'] = l_dict['subfaults'] + [{}]

    for l_par in ['on', 'dt', 'dur', 'mu', 'a', 'm0', 'T']:
      l_dict['subfaults'][-1][l_par] = float( l_subfault.find(l_par).text )

    l_dict['subfaults'][-1]['center'] = []
    l_center = l_subfault.find('center')
    for l_di in ['x', 'y', 'z']:
      l_dict['subfaults'][-1]['center'] = l_dict['subfaults'][-1]['center'] +\
                                          [ float( l_center.find(l_di).text ) ]

    l_dict['subfaults'][-1]['dirs'] = {'n': [], 's': [], 't': []}
    l_dirs = l_subfault.find('dirs')
    for l_dir in ['n', 's', 't']:
      for l_di in ['x', 'y', 'z']:
        l_str = l_dir+l_di
        l_dict['subfaults'][-1]['dirs'][l_dir] = l_dict['subfaults'][-1]['dirs'][l_dir] +\
                                                 [ float( l_dirs.find(l_str).text ) ]

  return l_dict

##
# Creates a netCDF-file based on the given cdl-source template.
#
# @param i_inFile cdl-template, with the two template paramters TEMPLATE_CENTERS and TEMPLATE_SUBFAULTS.
# @param i_outFile netCDF-output file which will be created.
# @param i_nSrcStr string replacing TEMPLATE_N_SRC;
# @param i_centerStr string replacing TEMPLATE_CENTERS.
# @param i_subStr string replacing TEMPLATE_SUBFAULTS.
##
def createNcFile( i_inFile, i_outFile, i_nSrcStr, i_centerStr, i_subStr ):
  # operate on a temporary file
  with tempfile.NamedTemporaryFile() as l_tmpFile:
    # open template
    with open(i_inFile) as l_tmpl:
      # copy contents and replace templates
      for l_line in l_tmpl:
        l_outStr = l_line

        l_outStr = l_outStr.replace( 'TEMPLATE_N_SRC',
                                     i_nSrcStr )

        l_outStr = l_outStr.replace( 'TEMPLATE_CENTERS',
                                     i_centerStr )
        l_outStr = l_outStr.replace( 'TEMPLATE_SUBFAULTS',
                                     i_subStr )
        l_tmpFile.write( l_outStr )

      # jump to beginning
      l_tmpFile.seek(0)

      # translate to netCDF
      l_proc = subprocess.check_call( ['ncgen -o '+i_outFile+' '+l_tmpFile.name], shell=True )

##
# Writes the given slip-rate samples of a single point source to var sliprates1 and the corresponding dimensions and metainfo.
#
# @param i_outFile netCDF-file where the slip-rate samples are written to.
# @param i_srs slip-rate samples which are written. list of lists [*][]: subfault, [][*]: sample
##
def writeSrs( i_outFile, i_srs ):
  # warn user about upcoming warning
  logging.info( 'warning \'unsupported Compound type, skipping...\' can be ignored, we are not touching this part of the netCDF-file' )

  # open netCDF file
  l_rootGroup = netCDF4.Dataset( i_outFile, "r+", format="NETCDF4" )

  # create offset dimension
  l_rootGroup.createDimension( 'sroffset',  len(i_srs)+1 )
  l_rootGroup.createDimension( 'direction', 3 )

  # create offset variable
  l_rootGroup.createVariable( varname='sroffsets',
                              datatype='u4',
                              dimensions=('sroffset', 'direction') )

  # deterimine total size
  l_nSrs = 0
  for l_sr in i_srs: l_nSrs = l_nSrs + len(l_sr)

  # create slip-rate dimensions
  l_rootGroup.createDimension( 'sample1', l_nSrs )
  l_rootGroup.createDimension( 'sample2', None       )
  l_rootGroup.createDimension( 'sample3', None       )

  # create slip-rate variables
  l_rootGroup.createVariable( varname='sliprates1',
                              datatype='f8',
                              dimensions=('sample1') )
  l_rootGroup.createVariable( varname='sliprates2',
                              datatype='f8',
                              dimensions=('sample2') )
  l_rootGroup.createVariable( varname='sliprates3',
                              datatype='f8',
                              dimensions=('sample3') )

  # set units
  l_rootGroup['sliprates1'].units = "m/s"
  l_rootGroup['sliprates2'].units = "m/s"
  l_rootGroup['sliprates3'].units = "m/s"

  # write slip-rates
  l_first = 0
  l_flush = 0;
  for l_su in i_srs:
    l_rootGroup['sliprates1'][l_first:l_first+len(l_su)] = l_su
    l_first = l_first + len(l_su)

    # flush periodically
    l_flush = l_flush + 1
    if l_flush % 10 == 0:
      l_rootGroup.sync

#  l_rootGroup['sliprates1'][:] = [l_en for l_sub in i_srs for l_en in l_sub]

  # write offsets
  l_rootGroup['sroffsets'][0, :] = [ 0, 0, 0 ]
  l_off = 0
  for l_so in xrange( 0, len(i_srs) ):
    l_off = l_off + len(i_srs[l_so])
    l_rootGroup['sroffsets'][l_so+1, :] = [ l_off, 0, 0 ]

  l_rootGroup.close()

##
# Generates slip-rate samples for the wave propagation benchmarks (see http://www.sismowine.org/model.html )
#
# @param i_t1 start time of the sampling.
# @param i_t2 end time of the sampling.
# @param i_dt time step of the sampling.
# @param i_T parameter T in the analytical slip-rate function.
# @param i_M0 scaling used for the moment-rate time history
# @return samples slip rates.
##
def wp( i_t1,
        i_t2,
        i_dt,
        i_T=0.1,
        i_M0=-1E18 ):
  l_sr = []

  # local time
  l_t = i_t1

  l_tI  = 1.0 / i_T
  l_tsI = l_tI * l_tI

  while( l_t < i_t2 ):
    l_sr.append( l_t * l_tsI * math.exp( -l_t * l_tI ) * i_M0 )
    l_t = l_t+i_dt
  return l_sr
             

# set up logger
logging.basicConfig( level=logging.DEBUG,
                     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s' )

# command line arguments
l_parser = argparse.ArgumentParser( description='Generates a NRF file from a finite fault config and a CDL-template. Writes sampled slip-rates for kinematic source benchmarks.',
                                    formatter_class=argparse.RawTextHelpFormatter, )

l_parser.add_argument( '--xml',
                       dest     = 'xml',
                       required = True,
                       type     = str,
                       help     =
'\
XML-configuration for the kinematic source description.\n\
The expected syntax is as follows:\n\
  <?xml version="1.0"?>\n\
  <!-- finite fault description consisting out of one or more subfaults -->\n\
  <finite_fault>\n\
    <!-- subfault struct, arbitrary number of subfaults are allowed -->\n\
    <subfault>\n\
      <!-- onset time -->\n\
      <on>0.0</on>\n\
      <!-- time step of the slip-rate sampling -->\n\
      <dt>0.001</dt>\n\
      <!-- duration for which the subfault is active -->\n\
      <dur>4.0</dur>\n\
      <!-- Lame parameter mu. If set to 0, the background velocity model is used -->\n\
      <mu>1.0</mu>\n\
      <!-- area of the subfault -->\n\
      <a>1.0</a>\n\
\n\
      <!-- scaling, used for the computation of the moment-rate time history,\n\
           typically called \'M0\' -->\n\
      <m0>-1E18</m0>\n\
      <!-- smoothing time T, used for the generation of the moment-rate time series -->\n\
      <T>0.1</T>\n\
\n\
      <!-- center of the subfault (x, y, z coordinates) -->\n\
      <center>\n\
        <x>   0</x>\n\
        <y>   0</y>\n\
        <z>2000</z>\n\
      </center>\n\
\n\
      <dirs>\n\
        <!-- direction of fault-normal (x, y, z) -->\n\
        <nx>0</nx>\n\
        <ny>1</ny>\n\
        <nz>0</nz>\n\
\n\
        <!-- direction of first tangent (x, y, z) -->\n\
        <sx>1</sx>\n\
        <sy>0</sy>\n\
        <sz>0</sz>\n\
\n\
        <!-- direction of second tangent (x, y, z) -->\n\
        <tx>0</tx>\n\
        <ty>0</ty>\n\
        <tz>1</tz>\n\
      </dirs>\n\
    </subfault>\n\
\n\
    <!-- path to cdl-file, which is used to generate the basic netCDF-header\n\
         and which sliprates1-array is populated -->\n\
    <path_to_cdl>kinematic_bench.cdl</path_to_cdl>\n\
    <!-- path to output file (netCDF) to which the slip-rates the output is written -->\n\
    <path_to_out>example_src.nc</path_to_out>\n\
  </finite_fault>\n\
')

l_args = vars(l_parser.parse_args())

l_cfg = parseConfig( l_args['xml'] )
assert( len( l_cfg['subfaults']) > 0 )

# assemble center str
l_ctrStr = ''
l_first = True;
for l_sf in l_cfg['subfaults']:
  if not l_first: l_ctrStr = l_ctrStr + ', '
  else: l_first = False

  l_ctrStr = l_ctrStr + '{'
  l_ctrStr = l_ctrStr + str( l_sf['center'][0] ) + ', ' +\
                        str( l_sf['center'][1] ) + ', ' +\
                        str( l_sf['center'][2] )
  l_ctrStr = l_ctrStr + '}'

# assemble subfault string
l_subStr = ''
l_first = True;
for l_sf in l_cfg['subfaults']:
  if not l_first: l_subStr = l_subStr + ', '
  else: l_first = False

  l_subStr = l_subStr + '{'
  l_subStr = l_subStr +   str( l_sf['on'] ) + ', ' +\
                          str( l_sf['dt'] ) + ', ' +\
                          str( l_sf['mu'] ) + ', ' +\
                          str( l_sf[ 'a'] ) + ', ' +\
                          '{' +\
                            str( l_sf['dirs'][ 's'][0] ) + ', ' +\
                            str( l_sf['dirs'][ 's'][1] ) + ', ' +\
                            str( l_sf['dirs'][ 's'][2] )        +\
                          '}' + ', ' +\
                          '{' +\
                            str( l_sf['dirs'][ 't'][0] ) + ', ' +\
                            str( l_sf['dirs'][ 't'][1] ) + ', ' +\
                            str( l_sf['dirs'][ 't'][2] )        +\
                          '}' + ', ' +\
                          '{' +\
                            str( l_sf['dirs'][ 'n'][0] ) + ', ' +\
                            str( l_sf['dirs'][ 'n'][1] ) + ', ' +\
                            str( l_sf['dirs'][ 'n'][2] )        +\
                          '}' +\
                        '}'

createNcFile( l_cfg['cdl'],
              l_cfg['out'],
              str( len(l_cfg['subfaults']) ),
              l_ctrStr,
              l_subStr )

#createNcFile( l_arguments['cdl_file'], l_arguments['out_file'], l_centerStr, l_subStr )
logging.info( "created netCDF-file "+l_cfg['out'] );

# slip rate samples
l_srs = []

# create slip rates
l_nSrs = 0
for l_sf in l_cfg['subfaults']:
  l_t1 = 0.0
  l_t2 = l_sf['dur']
  l_dt = l_sf['dt']
  l_t  = l_sf['T']
  l_sr = wp( 0.0,
             l_sf['dur'],
             l_sf['dt'],
             l_sf['T'],
             l_sf['m0'] )
  l_srs  = l_srs + [l_sr]
  l_nSrs = l_nSrs + len( l_sr )

logging.info( "generated a total of "+str(l_nSrs)+" slip-rate samples for " + str(len(l_cfg['subfaults'])) + ' subfaults' )
writeSrs( l_cfg['out'], l_srs )

logging.info( "finished, enjoy your benchmark source" )
