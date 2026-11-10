"""Bind an admitted Mandor installation to its separately verified adapter."""

from .verify_catalogue_transition import ROUTINES, verify_transition


def payload(state):
    return {key: value for key, value in state.items() if key != "sha256"}


def check_original(mandor, original):
    if (original.get("contract") != mandor.CONTRACT
            or original.get("sha256") != mandor.digest(payload(original))):
        raise ValueError("MANDOR_ADAPTER_ORIGINAL_STATE_CHANGED")


def bind(mandor, cur, original, raw_before, footprint, installer_receipt):
    """Call only after the original verifier passed and the pinned adapter was installed."""
    check_original(mandor, original)
    catalogue = mandor.capture(cur)
    verify_transition(original["after"], catalogue, raw_before,
                      mandor.native_identity(cur, ROUTINES), footprint, installer_receipt)
    adapted = dict(payload(original), after=catalogue)
    adapted["sha256"] = mandor.digest(adapted)
    mandor.verify(cur, adapted)
    return adapted


def verify(mandor, cur, original, adapted, raw_before, footprint, installer_receipt):
    check_original(mandor, original)
    # Only the after-catalogue and its digest may differ. This preserves the
    # original inverse inputs, authority and source records byte for byte.
    restored_fields = dict(payload(adapted), after=original["after"])
    if restored_fields != payload(original):
        raise ValueError("MANDOR_ADAPTER_ORIGINAL_BINDING_CHANGED")
    verify_transition(original["after"], adapted["after"], raw_before,
                      mandor.native_identity(cur, ROUTINES), footprint, installer_receipt)
    return mandor.verify(cur, adapted)
