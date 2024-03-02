# railml-exporter

This library can generate [railML 3.1](https://www.railml.org) files from a [yaramo](https://github.com/simulate-digital-rail/yaramo) topology.

## Usage as library

To use the exporter as a library, install it via:
```shell
pip3 install git+https://github.com/simulate-digital-rail/railml-exporter
```

Afterwards you can import it to your application with:
```python
from railml_exporter.exporter import Exporter
# topology is a yaramo.models.Topology object
exporter = Exporter(topology)
xml_string = exporter.to_string()
exporter.to_file('path/to/file.xml')
```

Further examples can be found in the [demo repository](https://github.com/simulate-digital-rail/yaramo).
