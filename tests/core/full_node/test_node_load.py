import asyncio
import time

import pytest

from src.protocols import full_node_protocol
from src.server.outbound_message import Message, NodeType
from src.types.peer_info import PeerInfo
from src.util.ints import uint16
from tests.core.full_node.test_full_node import connect_and_get_peer
from tests.setup_nodes import setup_two_nodes, test_constants, bt, self_hostname
from tests.time_out_assert import time_out_assert
from tests.core.full_node.test_full_sync import node_height_at_least


@pytest.fixture(scope="function")
def event_loop():
    loop = asyncio.get_event_loop()
    yield loop


class TestNodeLoad:
    @pytest.fixture(scope="function")
    async def two_nodes(self):
        async for _ in setup_two_nodes(test_constants):
            yield _

    @pytest.mark.asyncio
    async def test_blocks_load(self, two_nodes):
        num_blocks = 50
        full_node_1, full_node_2, server_1, server_2 = two_nodes
        blocks = bt.get_consecutive_blocks(num_blocks)
        peer = await connect_and_get_peer(server_1, server_2)
        await full_node_1.respond_sub_block(full_node_protocol.RespondSubBlock(blocks[0]), peer)

        await server_2.start_client(PeerInfo(self_hostname, uint16(server_1._port)), None)

        async def num_connections():
            return len(server_2.get_connections())

        await time_out_assert(10, num_connections, 1)

        start_unf = time.time()
        for i in range(1, num_blocks):
            await time_out_assert(5, node_height_at_least, True, full_node_2, i - 2)
            msg = Message("respond_sub_block", full_node_protocol.RespondSubBlock(blocks[i]))
            await server_1.send_to_all([msg], NodeType.FULL_NODE)
        print(f"Time taken to process {num_blocks} is {time.time() - start_unf}")
        assert time.time() - start_unf < 100
