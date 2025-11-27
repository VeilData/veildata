import pytest

from veildata.core import Module


class DummyModule(Module):
    def __init__(self):
        super().__init__()
        self.called_with = None

    def forward(self, x):
        self.called_with = x
        return f"processed-{x}"


def test_forward_and_call_equivalence():
    m = DummyModule()
    result_forward = m.forward("input")
    result_call = m("input")
    assert result_forward == result_call
    assert m.called_with == "input"


def test_train_and_eval_toggle():
    m = DummyModule()

    # Default mode is training
    assert m.training is True

    # Switch to eval
    m.eval()
    assert m.training is False

    # Switch back to train
    m.train()
    assert m.training is True


def test_forward_not_implemented():
    class Incomplete(Module):
        pass

    with pytest.raises(NotImplementedError):
        Incomplete().forward("x")
