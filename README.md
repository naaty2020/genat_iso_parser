#### Genat Iso Parser

An iso message bulk editor and parsor.

##### Usage:
    
###### ISO STREAMING

**import the library**  
    `from genat_iso_parser.Iso import IsoDict, IsoFile, IsoStream`

**instantiate an instance of IsoStream**  
    `iso = IsoStream()`

**get current version**  
    `iso.iso_version`

**get supported versions**  
    `iso.supported_versions()`

**change any field value of your choice**  
    `iso.changed_fields = IsoDict({3: '001100'})`  
    `iso.changed_fields[2] = '9999999999999999999'`

**remove any number of fields of your choice**  
    `iso.removed_fields.add(7)`  
    `iso.removed_fields.update({3, 4})`

**add a field alomg with value**  
    `iso.added_fields.update({100: 'rywiujfbw8efhsdjkb'})`  
    `iso.added_fields[99] = 'isuhgghioadhfgioahdnf'`

**allow length of fields(if there is any) tobe printed to the output**  
    `iso.include_length = True`

**turn off fields length to be printed**  
    `iso.include_length = False`

**capture iso messages that come through stdin (default is 'json' the other one is 'iso') and output to stdout**  
    `iso.stream('iso')`

**stop streaming**  
    `iso.stop_stream()`


###### ISO FILE         

**instantiate an instance of IsoFile, default version is 93**  
    `iso = IsoFile("your file here")`

**get current version**  
    `iso.iso_version`

**get supported versions**  
    `iso.supported_versions()`

**change any field value of your choice**  
    `iso.changed_fields = IsoDict({3: '001100'})`  
    `iso.changed_fields[2] = '1999999999999999999'`

**remove any number of fields of your choice**  
    `iso.removed_fields.add(5)`  
    `iso.removed_fields.update({3, 4})`

**add a field alomg with value**  
    `iso.added_fields = {100: 'rewayhfgiojsed'}`  
    `iso.added_fields[99] = 'isuhgghifgiosdjfoiaknoadhfgioahdnf'`

**allow length of fields(if there is any) tobe printed to the output**  
    `iso.include_length = True`

**turn off fields length to be printed**  
    `iso.include_length = False`

**produce csv file from the iso**  
    `csv_file = iso.to_csv()`

**produce iso file from the iso (might be useful for inspection of the iso)**  
    `iso_file = iso.to_iso()`

**produce json file from the iso**  
    `json_file = iso.to_json()`


##### Iso format JSON file (ISO.json)

**Layout:**

>{  
>    "A": {  
>	"long": "B",  
>	"short": "C",  
>	"len": D,  
>	"pad": E  
>    },  
>    .  
>    .  
>    .  
>}

- A -> field number
- B -> field long name
- C -> field short name
- D -> field length
- E -> length/size of leading field length for variable field lengths (Ex: field2 PAN has a pad of 2)  

**Sample:**

>{  
>"1": {  
>    "long": "Secondary Bit Map",  
>    "short": "BITMAP2",  
>    "len": 16,  
>    "pad": 0  
>},  
>"2": {  
>    "long": "Primary Account Number",  
>    "short": "PAN",  
>    "len": 19,  
>    "pad": 2  
>},  
>.  
>.  
>.  
>}
