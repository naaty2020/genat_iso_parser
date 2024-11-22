from src.genat_iso_parser.Iso import IsoDict, IsoStream, IsoFile


if __name__ == '__main__':

    # instantiate an instance of IsoStream
    iso = IsoStream()

    # get current version
    iso.iso_version

    # get supported versions
    iso.supported_versions()

    # change any field value of your choice
    iso.changed_fields = IsoDict({3: '001100'})
    iso.changed_fields[2] = '9999999999999999999'

    # remove any number of fields of your choice
    iso.removed_fields.add(7)
    iso.removed_fields.update({3, 4})

    # add a field alomg with value
    iso.added_fields.update({100: 'rywiujfbw8efhsdjkb'})
    iso.added_fields[99] = 'isuhgghioadhfgioahdnf'

    # allow length of fields(if there is any) tobe printed to the output
    iso.include_length = True

    # turn off fields length to be printed
    iso.include_length = False

    # capture iso messages that come through stdin (default is 'json' the other one is 'iso') and output to stdout
    iso.stream()

    # stop streaming
    iso.stop_stream()

    # instantiate an instance of IsoFile, default version is 93
    iso = IsoFile(r"E:\projects\iso_parser_first\files\005_decline_reversal")

    # get current version
    iso.iso_version

    # get supported versions
    iso.supported_versions()

    # change any field value of your choice
    iso.changed_fields = IsoDict({3: '001100'})
    iso.changed_fields[2] = '1999999999999999999'

    # remove any number of fields of your choice
    iso.removed_fields.add(5)
    iso.removed_fields.update({3, 4})

    # add a field alomg with value
    iso.added_fields = {100: 'rewayhfgiojsed'}
    iso.added_fields[99] = 'isuhgghifgiosdjfoiaknoadhfgioahdnf'

    # allow length of fields(if there is any) tobe printed to the output
    iso.include_length = True

    # turn off fields length to be printed
    iso.include_length = False

    # produce csv file from the iso
    csv_file = iso.to_csv()

    # produce iso file from the iso (might be useful for inspection of the iso)
    iso_file = iso.to_iso()

    # produce json file from the iso
    json_file = iso.to_json()
