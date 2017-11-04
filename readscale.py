#!/usr/bin/env python
# This program can be distributed under the terms of the GNU GPL.
# See the file COPYING.

try:
    import usb
except ImportError:
    pass
try:
    import hid
except ImportError:
    pass

import sys


class USBScaleBase(object):
    VENDOR_ID = 0x1446
    PRODUCT_ID = 0x6a73
    DATA_MODE_GRAMS = 2
    DATA_MODE_OUNCES = 11

    def __init__(self):
        self.data = [0, 0, 0, 0, 0, 0]
        self.raw_weight = None

    def update(self):
        """
        Just update the internal instance values
        :return:
        """
        self.read()

    def read(self):
        raise NotImplementedError

    @property
    def corrected_raw_weight(self):
        """
        The corrected weight in ounces
        :return:
        """
        weight = 0
        if self.data[2] == self.DATA_MODE_OUNCES:
            ounces = self.raw_weight * 0.1
            weight = ounces
        elif self.data[2] == self.DATA_MODE_GRAMS:
            grams = self.raw_weight
            weight = grams * .035274
        return weight

    @property
    def pounds(self):
        """
        The pounds portion of the scale reading
        :return:
        """
        return self.corrected_raw_weight // 16

    @property
    def ounces(self):
        """
        The ounces portion of the scale reading
        :return:
        """
        return self.corrected_raw_weight % 16


class USBScaleWin(USBScaleBase):
    def __init__(self):
        super(USBScaleWin, self).__init__()
        # find the USB device
        self.device = usb.core.find(idVendor=self.VENDOR_ID,
                                    idProduct=self.PRODUCT_ID)

        # if the device isn't found, bail
        if not self.device:
            raise ValueError('Cannot find device')
        # use the first/default configuration
        self.device.set_configuration()
        # first endpoint
        self.endpoint = self.device[0][(0, 0)][0]
        self.raw_weight = self.read()

    def read(self):
        """
        Read the scale data and return the raw, uncorrected values
        :return:
        """
        # Empty out the buffer and take the last result for more accurate results
        data = None
        while True:
            try:
                data = self.device.read(self.endpoint.bEndpointAddress,
                                        self.endpoint.wMaxPacketSize,
                                        timeout=100)
            except usb.core.USBError as e:
                if 'time' in e.strerror:
                    break
                raise e
        if not data:
            return

        self.raw_weight = data[4] + data[5] * 256
        self.data = data
        return self.raw_weight

    def __del__(self):
        """Be sure to release the scale"""
        usb.util.dispose_resources(self.device)


class USBScaleMac(USBScaleBase):
    def __init__(self):
        super(USBScaleMac, self).__init__()
        self.device = hid.device()
        try:
            self.device.open(self.VENDOR_ID, self.PRODUCT_ID)
        except IOError:
            sys.stdout.write("\rDevice appears to be busy, please check that "
                             "it is not in use by another process")
            sys.stdout.flush()
        self.device.set_nonblocking(1)
        self.raw_weight = self.read()

    def read(self):
        """
        Read the scale, update internal variables, and return the raw weight
        :return: raw weight
        """
        # empty out the buffer, once empty, return accurate results
        empty = False
        while True:
            data = self.device.read(64)
            if not data:
                empty = True
            if data and empty:
                break
        self.raw_weight = data[4] + data[5] * 256
        self.data = data
        return self.raw_weight

    def __del__(self):
        """
        Close the device when cleaning up...
        :return:
        """
        self.device.close()


def system_type():
    if sys.platform == 'darwin':
        return 'Mac'
    elif sys.platform == 'win32':
        return 'Win'
    else:
        raise NotImplementedError('The current system type is not supported')


def set_scale():
    scale = globals()['USBScale' + system_type()]()
    return scale

if __name__ == '__main__':
    print("Content-type: text/javascript\r\n\r\n")

    scale = set_scale()
    pounds, ounces = scale.pounds, scale.ounces

    # in a word, jsonp
    print('here_is_the_weight({pounds:'+str(pounds)+',ounces:'+str(round(ounces, 2))+'})')
