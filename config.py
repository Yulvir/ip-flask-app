import os

conn_string = "mongodb://localhost:27017/"
if os.getenv("MONGO_IP"):
    print(os.getenv("MONGO_IP"))
    conn_string = "mongodb://{}:27017/".format(os.getenv("MONGO_IP"))
