# Copyright (c) 2012, Braiden Kindt.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
# 
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER AND CONTRIBUTORS
# ''AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY
# WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
Implementation of the Garmin Device Interface Specifications.
http://www8.garmin.com/support/commProtocol.html
Classes named like Annn, Dnnn coorelate with the documented
types in specification. Currently this class only implementes
the necessary protocols and datatypes  to dynamically discover
device capaibilties and save runs. The spec was last updated
in 2006, so some datatypes include undocumented/unkown fields.
"""
from binascii import hexlify

import logging
import os
import struct
import time
import collections

import antd.ant as ant

_log = logging.getLogger("antd.garmin_fr")

class Device(object):
    """
    Class represents a garmin gps device.
    Methods of this class will delegate to
    the specific protocols impelemnted by this
    device. They may raise DeviceNotSupportedError
    if the device does not implement a specific
    operation.
    """
    
    def __init__(self, stream):
        self.stream = stream


    def get_filename(self, f):
        file_date_time = f.date.strftime("%Y-%m-%d_%H-%M-%S")
        return str.format("{0}-{1:02x}-{2}.fit", file_date_time,
            f.file_type, f.identifier)

    def download_all(self, archived=False, path=None):
        index = self.stream.download_index()

        if not os.path.exists(path):
            os.makedirs(path)

        for file in index.files:
            if file.read:
                if not (archived or not file.archive):
                    print "Skipping", file.date
                    continue
                file_path = os.path.join(path, self.get_filename(file))
                print "Downloading", file.date
                data = self.stream.download(file.index)
                f = open(file_path, 'wb')
                f.write(data)
                f.close()
