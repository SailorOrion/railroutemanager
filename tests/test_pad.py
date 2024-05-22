import pytest
from pad import Pad, PadSize

def test_pad_create():
    pad = Pad(100, 100, 'Test pad', PadSize(1, 1, 3, 3), color = False)

    pad.resize(50, 50, 3, 5)

    assert pad.height() == 50
    assert pad.width()  == 30
