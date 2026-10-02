s = "{\"name\": \"holy\", \"n\": 42, \"f\": 1.5, \"ok\": true, \"no\": false, \"nil\": null, \"list\": [1, \"x\", [3]], \"obj\": {\"a\": []}}"
v = json_parse(s)
print v["name"]
print v["n"]
print v["f"]
print v["ok"]
print v["nil"]
print v["list"][2][0]
print v["obj"]
print json_str(v)
print json_str([1, "a", true, null])
print json_parse("[1, 2]")
print json_str({})
print json_parse("\"\\u0e01\"")
