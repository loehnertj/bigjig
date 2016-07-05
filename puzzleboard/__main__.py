import logging
logging.basicConfig(
    level="INFO",
    filename="puzzleboard.log"
)
L = lambda: logging.getLogger(__name__)

from neatocom.json_codec import JsonCodec
from neatocom.stdio_transport import StdioTransport

from .puzzle_service import PuzzleService 


L().info('\n### New run of Puzzleboard ###')

L().info('initializing StdioTransport')
transport = StdioTransport()

L().info('initializing PuzzleService')
service = PuzzleService(
    codec=JsonCodec(),
    transport=transport,
    quit_handler=transport.stop
)

L().info('start running')
transport.run()