# json_load: the file round-trip (write_text -> json_load -> json_save).
# The decode call used to receive the closed File instead of the content.
base = "/tmp/opencode/hs_json_test"
mkdir(base)
path = base + "/v.json"
v0 = {"n": 42, "f": 1.5, "s": "hi", "b": true, "z": null, "l": [1, 2, 3]}
write_text(path, json_str(v0))
v = json_load(path)
print v["n"]
print v["f"]
print v["s"]
print v["b"]
print v["z"]
print v["l"]
print json_str(v)
# a nested container survives the round trip
write_text(path, json_str({"o": {"p": [{"q": 1}]}}))
print json_load(path)["o"]["p"][0]["q"]