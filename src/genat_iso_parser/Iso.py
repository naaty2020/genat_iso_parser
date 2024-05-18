import csv
import json
import logging
import sys
import threading
from abc import ABC, abstractmethod
from collections import defaultdict
from itertools import repeat
from pathlib import Path

from exceptions import *

MAX_BITMAP = '0' * 16
SUPPORTED_VERSIONS = '93', '87'
ISO_FILES = dict(zip(SUPPORTED_VERSIONS, repeat('../ISO.json')))


class Iso(ABC):

    @abstractmethod
    def get_fields(self, data):
        pass

    @abstractmethod
    def load_iso(self):
        pass

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
    def init_log(file: str):
        if logging.getLogger().hasHandlers():
            return
        logging.basicConfig(
            filename=file, format='%(asctime)s - %(levelname)s %(message)s', level=logging.NOTSET)


class IsoStream(Iso):
    def __init__(self, version='93') -> None:
        Iso.init_log('iso_stream.log')
        self.version = version
        try:
            self.iso_file = Path(ISO_FILES[self.version])
        except KeyError:
            logging.critical(f'Unsupported Iso version {self.version}.')
            raise UnsupportedIsoVersion(defaultdict(
                lambda: '', {'version': self.version}))
        try:
            self.load_iso()
        except Exception as ex:
            logging.critical(f'Could not read Iso File {self.iso_file}.\t{ex}')
            raise Exception(f'Could not read Iso File {self.iso_file}.\n{ex}')
        self.to_be_removed = set()
        self.to_be_modified = {}
        self.event = None
        self.streaming = None
        self.include_length = False

    def get_fields(self, data):
        record = defaultdict(lambda: '')
        bitmap_len = Iso.get_bitmap_len(data[4:20])
        bitmap = data[4:4 + bitmap_len]
        record['MTI'] = data[:4]
        record['BITMAP1'] = bitmap[:16]
        cursor = 20
        pattern = Iso.get_pattern(bitmap)
        for index in range(len(pattern)):
            if pattern[index] == '1':
                index = str(index + 1)
                if self.iso[index]['pad']:
                    try:
                        length = int(
                            data[cursor:cursor + self.iso[index]['pad']])
                    except ValueError:
                        raise PadValueError(defaultdict(
                            lambda: '', {'field': index, 'column': cursor + 1}))
                    if length > self.iso[index]['len']:
                        raise LengthError(defaultdict(
                            lambda: '', {'field': index, 'column': cursor + 1}))
                    cursor += self.iso[index]['pad']
                    nxt = cursor + length
                else:
                    nxt = cursor + self.iso[index]['len']
                if index not in self.to_be_removed:
                    if index in self.to_be_modified:
                        val = self.to_be_modified[index]
                    else:
                        val = data[cursor:nxt]
                    record[index] = self.get_val(val, index)
                cursor = nxt
        return record

    def get_val(self, val, index):
        if self.include_length:
            if self.iso[index]['pad']:
                val = str(len(val)).zfill(self.iso[index]['pad']) + val
        return val

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
                'Another stream is in progress. Either stop it or start this thread on a new IsoStream instance.')
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

    def remove_fields(self, *fields):
        if self.validate_field_num(*fields):
            self.to_be_removed.update({str(i) for i in fields})

    def remove_field(self, field):
        if self.validate_field_num(field):
            self.to_be_removed.add(str(field))

    def change_field(self, field, value):
        field = str(field)
        value = str(value)
        try:
            self.validate_field(field, value)
            self.to_be_modified[field] = value
        except (PadValueError, LengthError) as ex:
            logging.error(f'{ex} on field {ex.errors["field"]}')

    def validate_field_num(self, *fields):
        validated = all((isinstance(field, int) and 0 < field < 128)
                        for field in fields)
        if validated:
            return True
        else:
            logging.error(f'Invalid value found in input {fields}')

    def validate_field(self, field, value):
        if self.iso[field]['pad']:
            try:
                length = int(value[:self.iso[field]['pad']])
            except ValueError:
                raise PadValueError(defaultdict(lambda: '', {'field': field}))
            if length > self.iso[field]['len'] or len(value[self.iso[field]['pad']:]) != length:
                raise LengthError(defaultdict(lambda: '', {'field': field}))

    def stop_stream(self):
        self.event.set()
        self.streaming.join()

    def load_iso(self):
        with open(self.iso_file) as f:
            self.iso = json.load(f)

    def turn_on_length(self):
        self.include_length = True

    def turn_off_length(self):
        self.include_length = False


class IsoFile(Iso):

    def __init__(self, file, version='93') -> None:
        Iso.init_log('iso_file.log')
        self.version = version
        try:
            self.iso_file = Path(ISO_FILES[self.version])
        except KeyError:
            logging.critical(f'Unsupported Iso version {self.version}.')
            raise UnsupportedIsoVersion(defaultdict(
                lambda: '', {'version': self.version}))
        try:
            self.load_iso()
        except Exception as ex:
            logging.critical(f'Could not open Iso File {self.iso_file}.\t{ex}')
            raise Exception(f'Could not open Iso File {self.iso_file}.\n{ex}')
        self.file = Path(file).resolve()
        self.failed_file = self.file.with_stem(self.file.stem + '_failed')
        self.max_bitmap = MAX_BITMAP
        self.to_be_removed = set()
        self.to_be_modified = {}
        self.include_length = False

    def parse(self):
        with open(self.file) as f:
            for i, line in enumerate(f, 1):
                try:
                    yield self.get_fields(line)
                except (LengthError, InvalidBitmap, PadValueError) as ex:
                    logging.error(
                        f'{ex} on line {i} field {ex.errors["field"]} column {ex.errors["column"]}')

    def get_fields(self, data):
        record = defaultdict(lambda: '')
        bitmap_len = Iso.get_bitmap_len(data[4:20])
        bitmap = data[4:4 + bitmap_len]
        record['MTI'] = data[:4]
        record['BITMAP1'] = bitmap[:16]
        cursor = 20
        pattern = Iso.get_pattern(bitmap)
        for index in range(len(pattern)):
            if pattern[index] == '1':
                index = str(index + 1)
                if self.iso[index]['pad']:
                    try:
                        length = int(
                            data[cursor:cursor + self.iso[index]['pad']])
                    except ValueError:
                        raise PadValueError(defaultdict(
                            lambda: '', {'field': index, 'column': cursor + 1}))
                    if length > self.iso[index]['len']:
                        raise LengthError(defaultdict(
                            lambda: '', {'field': index, 'column': cursor + 1}))
                    cursor += self.iso[index]['pad']
                    nxt = cursor + length
                else:
                    nxt = cursor + self.iso[index]['len']
                if index not in self.to_be_removed:
                    if index in self.to_be_modified:
                        val = self.to_be_modified[index]
                    else:
                        val = data[cursor:nxt]
                    record[index] = self.get_val(val, index)
                cursor = nxt
        return record

    def get_val(self, val, index):
        if self.include_length:
            if self.iso[index]['pad']:
                val = str(len(val)).zfill(self.iso[index]['pad']) + val
        return val

    def remove_fields(self, *fields):
        self.to_be_removed.update({str(i) for i in fields})

    def remove_field(self, field):
        self.to_be_removed.add(str(field))

    def change_field(self, field, value):
        field = str(field)
        value = str(value)
        try:
            self.validate_field(field, value)
            self.to_be_modified[field] = value
        except (PadValueError, LengthError) as ex:
            logging.error(f'{ex} on field {ex.errors["field"]}')

    def validate_field(self, field, value):
        if self.iso[field]['pad']:
            try:
                length = int(value[:self.iso[field]['pad']])
            except ValueError:
                raise PadValueError(defaultdict(lambda: '', {'field': field}))
            if length > self.iso[field]['len'] or len(value[self.iso[field]['pad']:]) != length:
                raise LengthError(defaultdict(lambda: '', {'field': field}))

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
        json_encodeds = self.stream_json()
        file = self.file.with_suffix('.json')
        with open(file, 'w') as f:
            f.write('[' + next(json_encodeds))
            for json_encoded in json_encodeds:
                f.write(',' + json_encoded)
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
        self.choose_bitmap(self.file)
        pattern = Iso.get_pattern(self.max_bitmap)
        hdr = ['MTI', 'BITMAP1']
        for index in range(len(pattern)):
            if pattern[index] == '1':
                hdr.append(f'DE{index + 1}')
        return hdr

    def choose_bitmap(self, file):
        with open(file) as f:
            for line in f:
                n = 4
                n += Iso.get_bitmap_len(line[4:20])
                try:
                    if int(line[4:n], 16) > int(self.max_bitmap, 16):
                        self.max_bitmap = line[4:n]
                except ValueError:
                    pass

    def load_iso(self):
        with open(self.iso_file) as f:
            self.iso = json.load(f)

    def turn_on_length(self):
        self.include_length = True

    def turn_off_length(self):
        self.include_length = False
