import csv
import json
import logging
import os
import shutil
import sys
import threading
from abc import ABC
from collections import defaultdict
from pathlib import Path
from pkg_resources import resource_listdir, resource_stream

from .exceptions import *

MAX_BITMAP = '0' * 16
ISO_DIR = resource_listdir('resources', '')
SUPPORTED_VERSIONS = set()
ISO_FILES = {}

for file in ISO_DIR:
    file = Path(file)
    if file.suffix == '.json':
        if file.stem.startswith('ISO_'):
            ISO_FILES[file.stem[-1]] = resource_stream('resources', file.name).name
            SUPPORTED_VERSIONS.add(file.stem[-1])

DEFAULT_VERSION = '1'

if not ISO_FILES:
    raise Exception('No valid ISO file found!')


class Iso(ABC):

    def __init__(self) -> None:
        super().__init__()
        self.__iso_version = DEFAULT_VERSION
        self.restore_iso_version_file()
        self.removed_fields = IsoSet()
        self.modified_fields = IsoDict()
        self.added_fields = IsoDict()
        self.include_length = False

    @property
    def iso_version(self):
        return self.__iso_version

    def get_fields(self, data):
        self.validate_mti(data[0])
        record = defaultdict(lambda: '')
        bitmap_len = Iso.get_bitmap_len(data[4:20])
        bitmap = data[4:4 + bitmap_len]
        record['MTI'] = data[:4]
        record['BITMAP1'] = bitmap[:16]
        cur = 20
        pattern = Iso.get_pattern(bitmap)
        for i in range(len(pattern)):
            index = str(i + 1)
            if pattern[i] == '1':
                if self.iso[index]['pad']:
                    try:
                        ln = data[cur:cur + self.iso[index]['pad']]
                        length = int(ln)
                    except ValueError:
                        raise PadValueError(defaultdict(
                            lambda: '', {'field': index, 'column': cur + 1, 'value': ln}))
                    if length > self.iso[index]['len']:
                        raise LengthError(defaultdict(
                            lambda: '', {'field': index, 'column': cur + 1, 'value': length}))
                    cur += self.iso[index]['pad']
                    nxt = cur + length
                else:
                    nxt = cur + self.iso[index]['len']
                if index not in self.removed_fields:
                    if index in self.modified_fields:
                        val = self.modified_fields[index]
                    else:
                        val = data[cur:nxt]
                    record[index] = self.get_val(val, index)
                cur = nxt
            elif index in self.added_fields:
                record[index] = self.get_val(self.added_fields[index], index)

        record['BITMAP1'] = self.update_bitmap(record['BITMAP1'])
        if '1' in record:
            record['1'] = self.update_bitmap(record['1'])
        return record

    def validate_mti(self, mti1):
        if mti1 != self.__iso_version:
            logging.error(f'Wrong or unsupported iso version! Expected version\'{self.__iso_version}\' Got \'{mti1}\'')
            raise Exception(f'Wrong or unsupported iso version! Expected version\'{self.__iso_version}\' Got \'{mti1}\'')

    def update_bitmap(self, bitmap):
        if not (self.added_fields or self.removed_fields):
            return bitmap
        pattern = list(Iso.get_pattern(bitmap))
        for index in range(len(pattern)):
            i = str(index + 1)
            if i in self.added_fields:
                pattern[index] = '1'
            if i in self.removed_fields:
                pattern[index] = '0'
        return Iso.reconstruct_bitmap(''.join(pattern))

    def get_val(self, val, index):
        if self.include_length:
            if self.iso[index]['pad']:
                val = str(len(val)).zfill(self.iso[index]['pad']) + val
        return val

    def load_iso(self):
        try:
            with open(self.iso_file) as f:
                self.iso = json.load(f)
        except Exception as ex:
            logging.critical(f'Could not open Iso File {self.iso_file}.\t{ex}')
            raise Exception(f'Could not open Iso File {self.iso_file}.\n{ex}')

    def custom_iso_version_file(self, file, version):
        self.__iso_version = version
        self.iso_file = file
        self.load_iso()

    def restore_iso_version_file(self):
        self.change_iso_version_file()

    def change_iso_version_file(self, version=DEFAULT_VERSION):
        try:
            self.iso_file = Path(ISO_FILES[version])
            self.__iso_version = version
            self.load_iso()
        except KeyError:
            logging.critical(f'Unsupported Iso version {version}.')
            raise UnsupportedIsoVersion(defaultdict(
                lambda: '', {'version': version}))

    def download_iso_file(self, download_path=None, version=None):
        if version is None:
            version = self.__iso_version
        try:
            if download_path is None:
                download_path = os.getcwd()
            download_path = Path(download_path).absolute().resolve()
            shutil.copy(ISO_FILES[version], download_path)
        except KeyError:
            print(f'Unsupported Iso version {version}.')

    @staticmethod
    def get_bitmap_len(bitmap: str):
        return 16 if bitmap[0] < '8' else 32

    @staticmethod
    def get_pattern(bitmap):
        try:
            return bin(int(bitmap, 16))[2:].zfill(len(bitmap) * 4)
        except ValueError:
            raise InvalidBitmap(defaultdict(
                lambda: '', {'field': '1', 'column': '0'}))

    @staticmethod
    def reconstruct_bitmap(pattern):
        try:
            size = 16 if len(pattern) == 64 else 32
            return hex(int(pattern, 2))[2:].zfill(size)
        except ValueError:
            raise InvalidBitmap(defaultdict(
                lambda: '', {'field': '1', 'column': '0'}))

    @staticmethod
    def validate_field_num(*fields):
        validated = all((isinstance(field, int) and 0 < field < 128)
                        for field in fields)
        if not validated:
            logging.error(f'Invalid value found in input {fields}')
            raise FieldNumberError(
                f'Invalid field numbers encountered in input {fields}')

    def init_log(self, file='iso.log'):
        if not logging.getLogger().hasHandlers():
            logging.basicConfig(
                filename=file, format='%(asctime)s - %(levelname)s %(message)s', level=logging.NOTSET)


class IsoStream(Iso):
    def __init__(self) -> None:
        super().__init__()
        self.event = None
        self.streaming = None

    def stream(self, format='json'):
        def stream_internal():
            while not self.event.is_set():
                data = next(sys.stdin)
                if data.isspace() or data == '':
                    continue
                try:
                    print(self.choose_format(data, format))
                except Exception as ex:
                    logging.error(ex)

        if self.event and self.event.is_set():
            logging.error(
                'Another stream is in progress. Either stop it or start it on a new IsoStream instance.')
            return

        self.event = threading.Event()
        self.streaming = threading.Thread(target=stream_internal)
        self.streaming.start()

    def choose_format(self, data, format):
        if format == 'json':
            return json.dumps(self.get_fields(data))
        elif format == 'iso':
            return ''.join(self.get_fields(data).values())
        else:
            logging.error(f'Unknown format type {format}')
            return ''

    def stop_stream(self):
        self.event.set()
        self.streaming.join()


class IsoFile(Iso):

    def __init__(self, file) -> None:
        super().__init__()
        self.file = Path(file).resolve()
        self.failed_file = self.file.with_stem(self.file.stem + '_failed')
        self.max_bitmap = MAX_BITMAP

    def parse(self):
        with open(self.file) as f:
            for i, line in enumerate(f, 1):
                try:
                    yield self.get_fields(line)
                except (LengthError, InvalidBitmap, PadValueError) as ex:
                    logging.error(
                        f'{ex} on line {i} field {ex.errors["field"]} column {ex.errors["column"]}')
                except Exception as ex:
                    logging.error(ex)

    def to_csv(self):
        records = self.parse()
        header = self.make_header()
        pattern = Iso.get_pattern(self.max_bitmap)
        pattern_range = range(len(pattern))
        file = self.file.with_suffix('.csv')
        with open(file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for record in records:
                line = [record['MTI'], record['BITMAP1']]
                line.extend([record[str(i + 1)]
                            for i in pattern_range if pattern[i] == '1'])
                writer.writerow(line)
        return file

    def to_json(self):
        records = self.parse()
        file = self.file.with_suffix('.json')
        with open(file, 'w') as f:
            f.write('[' + json.dumps(next(records)))
            for json_encoded in records:
                f.write(',' + json.dumps(json_encoded))
            f.write(']')
        return file

    def to_iso(self):
        records = self.parse()
        file = self.file.with_suffix('.iso')
        with open(file, 'w') as f:
            for record in records:
                f.write(''.join(record.values()) + '\n')
        return file

    def make_header(self):
        self.choose_bitmap()
        pattern = Iso.get_pattern(self.max_bitmap)
        hdr = ['MTI', 'BITMAP1']
        for index in range(len(pattern)):
            if pattern[index] == '1':
                hdr.append(f'DE{index + 1}')
        return hdr

    def choose_bitmap(self):
        with open(self.file) as f:
            for line in f:
                n = 4
                n += Iso.get_bitmap_len(line[4:20])
                try:
                    if int(line[4:n], 16) > int(self.max_bitmap, 16):
                        self.max_bitmap = line[4:n]
                except ValueError:
                    pass
        self.max_bitmap = self.update_bitmap(self.max_bitmap)


class IsoSet(set):
    def __init__(self, *args):
        Iso.validate_field_num(*args)
        super().__init__(*args)

    def __or__(self, __s):
        Iso.validate_field_num(*__s)
        return super().__or__(__s)

    def add(self, value):
        Iso.validate_field_num(value)
        super().add(str(value))

    def update(self, *s) -> None:
        Iso.validate_field_num(*s)
        return super().update(*s)

    def union(self, *s):
        Iso.validate_field_num(*s)
        return super().union(*s)

class IsoDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        Iso.validate_field_num(*self.keys())

    def __setitem__(self, key, value):
        Iso.validate_field_num(key)
        key = str(key)
        value = str(value)
        super().__setitem__(key, value)