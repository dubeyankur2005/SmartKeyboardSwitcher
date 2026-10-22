import pytest
from shared.protocol import LineBuffer, decode_line, encode


def test_round_trip_and_fragmented_or_coalesced_frames():
    buf=LineBuffer(); first=encode({"type":"key","action":"down","key":"A"}); second=encode({"type":"key","action":"up","key":"A"})
    assert buf.feed(first[:5])==[]
    assert buf.feed(first[5:]+second)==[{"type":"key","action":"down","key":"A"},{"type":"key","action":"up","key":"A"}]


@pytest.mark.parametrize("raw",[b"{bad}\n",b'{"type":"key","action":"sideways","key":"A"}\n',b'{"type":"key","action":"down","key":"NOPE"}\n',b'{"type":"inject","key":"A"}\n'])
def test_reject_malformed_messages(raw):
    with pytest.raises(ValueError): decode_line(raw.strip())


def test_oversized_partial_frame_rejected():
    with pytest.raises(ValueError): LineBuffer().feed(b"x"*4097)
