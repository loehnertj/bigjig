import logging
logging.basicConfig(
    level="INFO",
    filename="puzzleboard.log"
)
L = lambda: logging.getLogger(__name__)

from neatocom.terse_codec import TerseCodec
from neatocom.transports import StdioTransport, MuxTransport, TcpServerTransport

from .puzzle_service import PuzzleService


L().info('\n### New run of Puzzleboard ###')

L().info('initializing Transport')
transport = MuxTransport()
transport += StdioTransport()
# FIXME hardcoded port
server = TcpServerTransport(port=8888)
transport += server

L().info('initializing PuzzleService')
service = PuzzleService(
    codec=TerseCodec(),
    transport=transport,
    close_handler=server.close,
    quit_handler=transport.stop
)

L().info('start running')
transport.run()
L().info('exiting')