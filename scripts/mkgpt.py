#!/usr/bin/env python3
"""Write a raw GPT disk image, no loop devices or root needed.

    python3 scripts/mkgpt.py OUTPUT.img SIZE_MIB [--bios-boot]

Layout (512-byte sectors): protective MBR, primary header and entries,
one EFI System Partition starting at LBA 2048, backup entries and header.
With --bios-boot a 1 MiB BIOS boot partition (GRUB core.img home) comes
first and the ESP follows it. The ESP fills the rest, rounded down to
whole MiB; its FAT filesystem is written later with mtools at the byte
offset this script prints. Deterministic GUIDs: same inputs, same image.
"""
import hashlib
import struct
import sys
import zlib

SECTOR = 512
ENTRIES = 128
ENTRY_SIZE = 128
ESP_TYPE = bytes.fromhex('28732ac11ff8d211ba4b00a0c93ec93b')
BIOS_TYPE = bytes.fromhex('4848612164496e6f744e656564454649')  # 21686148-6449-6E6F-744E-656564454649


def guid(seed):
    return hashlib.sha256(seed).digest()[:16]


def header(my_lba, alt_lba, first_usable, last_usable, disk_guid, entries_lba, entries_crc):
    out = struct.pack('<8sIIII', b'EFI PART', 0x10000, 92, 0, 0)
    out += struct.pack('<QQQQ', my_lba, alt_lba, first_usable, last_usable)
    out += disk_guid
    out += struct.pack('<QII', entries_lba, ENTRIES, ENTRY_SIZE)
    out += struct.pack('<I', entries_crc)
    crc = zlib.crc32(out) & 0xFFFFFFFF
    return out[:16] + struct.pack('<I', crc) + out[20:] + bytes(512 - 92)


def entry(type_guid, unique, first, last, name):
    raw = type_guid + unique + struct.pack('<QQQ', first, last, 0)
    raw += name.encode('utf-16-le').ljust(72, b'\0')
    assert len(raw) == ENTRY_SIZE
    return raw


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) != 2:
        raise SystemExit('usage: mkgpt.py OUTPUT.img SIZE_MIB [--bios-boot]')
    output, mib = args[0], int(args[1])
    bios_boot = '--bios-boot' in sys.argv[2:]
    total = mib * 1024 * 1024 // SECTOR
    if total < 4096 + 2048 + 67:
        raise SystemExit('image too small for GPT plus a 1 MiB-aligned ESP')
    parts = []
    at = 2048
    if bios_boot:
        parts.append(entry(BIOS_TYPE, guid(b'hs-bios-boot' + bytes(8)), at, at + 2047, 'bios'))
        at += 2048
    esp_first = at
    esp_count = (total - 34 - esp_first + 1) & ~2047
    if esp_count < 2048:
        raise SystemExit('image too small: no room for the ESP')
    parts.append(entry(ESP_TYPE, guid(b'hs-esp' + struct.pack('<Q', esp_count)),
                       esp_first, esp_first + esp_count - 1, 'ESP'))
    table = b''.join(parts).ljust(ENTRIES * ENTRY_SIZE, b'\0')
    entries_crc = zlib.crc32(table) & 0xFFFFFFFF
    disk_guid = guid(b'hs-usb-disk' + struct.pack('<Q', total) + (b'b' if bios_boot else b''))
    last_usable = total - 34
    mbr = bytearray(512)
    struct.pack_into('<B3sB3sII', mbr, 446, 0, b'\0\0\0', 0xEE, b'\xff\xff\xff', 1,
                     min(total - 1, 0xFFFFFFFF))
    mbr[510:512] = b'\x55\xaa'
    image = bytearray(total * SECTOR)
    image[0:512] = mbr
    image[512:1024] = header(1, total - 1, 34, last_usable, disk_guid, 2, entries_crc)
    image[1024:1024 + len(table)] = table
    backup_entries_lba = total - 1 - len(table) // SECTOR
    image[(total - 1) * SECTOR:total * SECTOR] = header(
        total - 1, 1, 34, last_usable, disk_guid, backup_entries_lba, entries_crc)
    image[backup_entries_lba * SECTOR:(total - 1) * SECTOR] = table
    with open(output, 'xb') as out:
        out.write(image)
    print(esp_first * SECTOR)


if __name__ == '__main__':
    main()
