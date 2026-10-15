base = env("HS_WWW")
print http_get(base + "/hello.txt")
port = int(env("HS_WWW_PORT"))
s = tcp_connect("127.0.0.1", port)
tcp_send(s, "GET /hello.txt HTTP/1.0\r\nHost: x\r\n\r\n")
print tcp_recv(s, 15)
tcp_close(s)
print "done"
