'''
***************************************************************************//**
* @file ota_application_based.py
* @brief Perform an OTA to an EFR device using your computer
* @version 1.0
*******************************************************************************
* # License
* <b>Copyright 2020 Silicon Laboratories Inc. www.silabs.com</b>
*******************************************************************************
*
* SPDX-License-Identifier: Zlib
*
* The licensor of this software is Silicon Laboratories Inc.
*
* This software is provided \'as-is\', without any express or implied
* warranty. In no event will the authors be held liable for any damages
* arising from the use of this software.
*
* Permission is granted to anyone to use this software for any purpose,
* including commercial applications, and to alter it and redistribute it
* freely, subject to the following restrictions:
*
* 1. The origin of this software must not be misrepresented; you must not
*    claim that you wrote the original software. If you use this software
*    in a product, an acknowledgment in the product documentation would be
*    appreciated but is not required.
* 2. Altered source versions must be plainly marked as such, and must not be
*    misrepresented as being the original software.
* 3. This notice may not be removed or altered from any source distribution.
*
*******************************************************************************
* # Experimental Quality
* This code has not been formally tested and is provided as-is. It is not
* suitable for production environments. In addition, this code will not be
* maintained and there may be no bug maintenance planned for these resources.
* Silicon Labs may update projects from time to time.
******************************************************************************/
'''

'''
This example has been tested on Bluetooth projects that relies on
the Application (not the Apploader) to handle the OTA upgrade.

The BLEAK API documenation and example code can be found here:
        https://bleak.readthedocs.io/en/latest/
'''

import asyncio
import time
import sys, getopt

from bleak import BleakScanner, BleakClient
from bleak.backends.scanner import BLEDevice, AdvertisementData

# replace with real characteristic UUID
CHAR_OTA_CONTROL_UUID = "F7BF3564-FB6D-4E53-88A4-5E37E0326063"
CHAR_OTA_DATA_UUID = "984227F3-34FC-4045-A5D0-2C581F81A153"
SL_OTA_SVC_UUID = "1d14d6eefd63-4fa1-bfa4-8f47b42119f0"

target_device_name = ""
file_to_ota = ""

# Whether to use reliable writes or not...
MODE_RELIABLE = False

async def start():
    queue = asyncio.Queue()

    def callback(device: BLEDevice, adv: AdvertisementData) -> None:
        if device.name == target_device_name:
            # can use advertising data to filter here as well if desired
            print("Matched by name!")
            queue.put_nowait(device)
            return
        if device.address == target_device_name:
            print("Matched by addr!")
            queue.put_nowait(device)
            return
        print(f"Skipping non-matching device: {device.name} with address: {device.address}")

    async with BleakScanner(detection_callback=callback):
        # get the first matching device
        device = await queue.get()
        
        # Make sure queue does not have any remaining devices. Empty q if an item is present
        while queue.qsize() != 0:
            await queue.get() # Empty

    disconnected_event = asyncio.Event()
    def disconnected_callback(client):
        print(f"Got disconnected from {client} and pretending it didn't happen!")
        #disconnected_event.set()

    async with BleakClient(device, disconnected_callback=disconnected_callback) as client:
        print("Connection opened")

        # BlueZ doesn't have a proper way to get the MTU, so we have this hack.
        # If this doesn't work for you, you can set the client._mtu_size attribute
        # to override the value instead. Source: BLEAK
        print("About to try mtu hack")
        if client.__class__.__name__ == "BleakClientBlueZDBus":
            client._mtu_size = 244
        #     await client._acquire_mtu()
        print("mtuhack complete")

        svcs = await client.get_services()
        [print(f"Service: {s}") for s in svcs]
        ## FIXME - check it actually _has_ the ota service?!

        print("Initiating OTA")

        # AN1086. Write 0 to the Control characteristic to initiate OTA
        data = bytearray([0])
        await client.write_gatt_char(CHAR_OTA_CONTROL_UUID, data, True)
        await asyncio.sleep(1.0)    # delay to allow device to process (i.e. clear slot)

        # Open the file and write the contents one chunk at a time.
        # For greater throughput, the chunk size should be (MTU size - 3)
        f = open(file_to_ota, "rb")
        gbl_img = bytearray(f.read())
        fsize = len(gbl_img)
        t_start = time.time()
        chunk_size = client.mtu_size - 3    # 3 bytes for Write ATT operation
        print(f"Uploading {fsize} bytes in chunks of {chunk_size}")
        for chunk in (
            gbl_img[i : i + chunk_size] for i in range(0, len(gbl_img), chunk_size)
        ):
            if MODE_RELIABLE:
                await client.write_gatt_char(CHAR_OTA_DATA_UUID, chunk, True)
            else:
                await client.write_gatt_char(CHAR_OTA_DATA_UUID, chunk, False)
                await asyncio.sleep(.005)  # lol, spray and pray!
            print(".", end='', flush=True)
        print("")

        data = bytearray([3])
        answer = await client.write_gatt_char(CHAR_OTA_CONTROL_UUID, data)
        t_delta = time.time() - t_start
        await asyncio.sleep(1.0)

        print(f"Upload complete, wrote at {fsize / t_delta:0.2f} Bps or {fsize*8/t_delta:0.2f} bps")


def main(argv):
    global target_device_name, file_to_ota

    # Get the gbl file and device name
    try:
        opts, args = getopt.getopt(argv, "hd:f:", ["devname=","file="])
    except getopt.GetoptError:
        print("ota.py -d <device name> -f <file to ota>")
        print("AN1086 has information about performing OTAs on EFR devices")
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print("ota_application_based.py -d <device name> -f <file to ota>")
            print("AN1086 has information about performing OTAs on EFR devices")
            sys.exit()
        elif opt in ("-d", "--devname"):
            target_device_name = arg
            print(target_device_name)
        elif opt in ("-f", "--file"):
            file_to_ota = arg

    asyncio.run(start())


if __name__ == "__main__":
    main(sys.argv[1:])