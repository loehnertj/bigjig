import sys
import logging
L = lambda: logging.getLogger(__name__)

from neatocom.codecs import TerseCodec
from neatocom.transports import StdioTransport, MuxTransport, TcpServerTransport
from neatocom.announcer_api import make_udp_announcer

from .puzzle_service import PuzzleService

if '--console' in sys.argv:
    logging.basicConfig(level='INFO')
else:
    logging.basicConfig(
        level="INFO",
        filename="puzzleboard.log"
    )

L().info('\n### New run of Puzzleboard ###')

L().info('initializing Transport')
transport = MuxTransport()
transport += StdioTransport()
# FIXME hardcoded port
server = TcpServerTransport(
    port=8888,
    announcer=make_udp_announcer(8889, description='type:puzzleboard version:0.1 servername:Unknown_Server')
)
transport += server

L().info('initializing PuzzleService')
try:
    service = PuzzleService(
        codec=TerseCodec(),
        transport=transport,
        announcer=server.announcer,
        close_handler=server.close,
        quit_handler=transport.stop
    )

    L().info('start running')
    transport.run()
    
except Exception as e:
    L().critical('Fatal Exception occured', exc_info=True)
    raise
L().info('exiting')
