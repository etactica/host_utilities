#!/usr/bin/env python3
"""
Read the data from a "large" characteristic.
"""
import argparse
import asyncio
import logging
import struct

import time
import sys, getopt

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(name)s %(levelname)s %(message)s')

from bleak import BleakScanner, BleakClient
from bleak.backends.scanner import BLEDevice, AdvertisementData

CHAR_TO_READ = "aab81001-842c-4277-8432-a3e884da463b"
target_device_name = ""

def get_parser():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-d", "--device", help="device name or address", default="aem-therm3")
    parser.add_argument("-c", "--characteristic", help="Characteristic uuid to read", default=CHAR_TO_READ)
    return parser


class App():
    def __init__(self, opts):
        self.opts = opts
        self.ktgt = None
        self.notif_complete = False
        self.len_total = 0
        self.len_received = 0

    def det_cb(self, dev: BLEDevice, adv: AdvertisementData):
        logging.info("det cb? %s %s", dev, adv)
        if dev.name == opts.device:
            print("Matched by name!")
            self.ktgt = dev
            return True
        if dev.address == opts.device:
            print("matched by address!")
            self.ktgt = dev
            return True
        print(f"Skipping non-matching device: {dev.name} with addr: {dev.address}")

    def disconn_cb(self, client):
        logging.warning("Unexpectedly disconnected from client: %s", client)

    def notif_cb(self, sender, data):
        logging.info("received notific from %s with %s", sender, data)
        if self.len_total == 0:
            # First packet...
            self.flags, self.len_total = struct.unpack("<BH", data)
            logging.info("ok, first packet, expecting %d bytes total", self.len_total)
        else:
            # just raw data now...
            #seqid, data_out = struct.unpack("<B%dH" % (len(data) - 1)/2, data)  # for 12 bit adc data...
            #seqid, data_out = struct.unpack("<B%dB" % (len(data) - 1), data)  # for 8 bit seq testing...
            data_out = data
            logging.debug("output data len: %d = %s", len(data_out), data_out)
            self.len_received += len(data_out)
            self.notif_complete = self.len_received >= self.len_total



    async def start(self):
        scanner = BleakScanner()
        scanner.set_scanning_filter(Transport="le")
        scanner.register_detection_callback(self.det_cb)
        await scanner.start()
        await asyncio.sleep(5)
        await scanner.stop()

        for d in scanner.discovered_devices:
            logging.info("Found: %s", d)

        if not self.ktgt:
            print("Failed to find a matching device, aborting")
            return
        print("but, _our_ device is: ", self.ktgt)

        async with BleakClient(self.ktgt, disconnected_callback=self.disconn_cb) as client:
            print(f"working with an mtu size of {client.mtu_size}")
            print("About to try mtu hack")
            if client.__class__.__name__ == "BleakClientBlueZDBus":
                #client._mtu_size = 244  # this results in "negotiated mtu" of 247 reported by silabs end
                client._mtu_size = 60  # nope, this simply did nothing at all! still 247, so that's our host doing it?
                #await client._acquire_mtu()  # I guess, unless you make this call? nah, that don't do shit....
            print("mtuhack complete")
            print(f"POST working with an mtu size of {client.mtu_size}")
            svcs = await client.get_services()
            [print(f"Service: {s}") for s in svcs]
            #header = await client.read_gatt_char(self.opts.characteristic)
            #(version,total_length,wop) = struct.unpack("<BH")
            #print("gat char read got", xx)
            await client.start_notify(self.opts.characteristic, self.notif_cb)
            while not self.notif_complete:
                await asyncio.sleep(0.5)
            await client.stop_notify(self.opts.characteristic)



def main(opts):
    app = App(opts)
    asyncio.run(app.start())


if __name__ == "__main__":
    p = get_parser()
    opts = p.parse_args()
    main(opts)
