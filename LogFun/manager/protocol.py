import struct

# Protocol Constants (Must match Agent)
PROTO_VERSION = 1
TYPE_HANDSHAKE = 1
TYPE_LOG_DATA = 2
TYPE_HEARTBEAT = 3
TYPE_CONFIG_PUSH = 4

# Header: Version(1B) + Type(1B) + Length(4B)
PACKET_HEAD = struct.Struct('!BBI')


def unpack_packet(sock):
    """
    Helper to read a complete packet from a socket.
    Returns: (type, body_bytes) or (None, None) on error/close.
    """
    try:
        # 1. Read Header
        header_data = sock.recv(PACKET_HEAD.size)
        if not header_data:
            return None, None

        ver, p_type, length = PACKET_HEAD.unpack(header_data)

        # 2. Read Body
        body_data = b""
        while len(body_data) < length:
            chunk = sock.recv(length - len(body_data))
            if not chunk:
                return None, None
            body_data += chunk

        return p_type, body_data
    except Exception:
        return None, None


def pack_packet(p_type, body_bytes):
    """
    Helper to create a packet byte stream.
    """
    length = len(body_bytes)
    header = PACKET_HEAD.pack(PROTO_VERSION, p_type, length)
    return header + body_bytes
