import pathlib

import yaml


# https://github.com/yaml/pyyaml/issues/103
class NoAliasDumper(yaml.SafeDumper):
    def ignore_aliases(self, data):
        return True


def main():
    here = pathlib.Path(__file__).parent
    input_file = here.joinpath("ci.yml")
    output_file = here.joinpath("workflows", "ci.yml")

    loaded = yaml.load(input_file.read_text(encoding="UTF-8"), Loader=yaml.SafeLoader)
    loaded.pop("anchors")
    output_file.write_text(yaml.dump(loaded, Dumper=NoAliasDumper), encoding="UTF-8")


main()

# s = """
# anchors:
#     wifi_parm: &wifi_params
#         ssid: 1
#         key: 2
# test1:
#   name: connectivity
#   <<: *wifi_params
# test2:
#   name: connectivity_5ghz
#   <<: *wifi_params
# """
#
# print(s)
# data = yaml.load(s, Loader=yaml.SafeLoader)
# print(data)
# data.pop("anchors")
# print(yaml.dump(data, Dumper=yaml.SafeDumper))