import pytest

from waypoint.runtime.ownership import Ownership


def test_automation_cannot_act_during_handoff_and_resume_tokens_are_single_use():
    ownership = Ownership()
    token = ownership.request()
    with pytest.raises(ValueError, match="ownership"):
        ownership.require_automation()
    ownership.take(token)
    with pytest.raises(ValueError, match="ownership"):
        ownership.require_automation()
    ownership.begin_resume(token)
    ownership.finish_resume(valid=False)
    assert ownership.state == "human"
    ownership.begin_resume(token)
    ownership.finish_resume(valid=True)
    ownership.require_automation()
    with pytest.raises(ValueError, match="stale"):
        ownership.begin_resume(token)
