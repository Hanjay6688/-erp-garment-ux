"""Attempt the full dump restore even when observing the used DB fails."""
import traceback


def always(observe,restore,verify):
    observed=None;failure=None
    try:observed=observe()
    except Exception as error:failure=(error,traceback.format_exc())
    restored=restore()
    verified=verify(restored)
    return observed,restored,verified,failure
