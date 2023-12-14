import argparse
import os
import sys
import time
import cbor2

import zmq
from loguru import logger

sendMsgCount = 0
receiveMsgCount = 0

try:
    from rich import pretty, print
    pretty.install()
except ImportError or ModuleNotFoundError:
    pass


def main(argc: int, argv: list[str]):

    # ZeroMQ client connect
    argv_parser = argparse.ArgumentParser(prog=os.path.basename(__file__).removesuffix(".py"),
                                         description="ZeroMQ client demo")
    argv_parser.add_argument("-p", "--port", type=int, default=12333, help="Port number")

    args = argv_parser.parse_args(argv[1:])

    print(f"Connecting to server on port {args.port}...")
    
    context = zmq.Context()

    subscriber = context.socket(zmq.SUB)
    
    subscriber.connect(f"tcp://localhost:{args.port}")
    subscriber.setsockopt(zmq.SUBSCRIBE, b"light_level")
    print("Connected!")

    print("Listening...")
    n_messages_received: int = 0
    try:
        while True:
            topic = subscriber.recv_string()
            # Then receive the message
            message = subscriber.recv()
            
            # Deserialize the message using cbor2
            data = cbor2.loads(message)
            
            logger.info(f"Received message #{n_messages_received}: {data}")
            n_messages_received += 1
            time.sleep(1)

    except KeyboardInterrupt:
        print("Interrupted!")
    finally:
        subscriber.close()

        context.term()

   

if __name__ == "__main__":
    sys.exit(main(len(sys.argv), sys.argv))
